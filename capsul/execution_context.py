# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import chain
from uuid import uuid4
import importlib

from populse_db import Database
from soma.controller import Controller, OpenKeyDictController
from soma.api import DictWithProxy
from soma.undefined import undefined

from .application import Capsul, executable
from .dataset import Dataset
from .pipeline.pipeline import Process, Pipeline
from capsul.process.process import NipypeProcess
from .pipeline.process_iteration import ProcessIteration
from capsul.config.configuration import get_config_class, ModuleConfiguration


class ExecutionContext(Controller):
    python_modules: list[str]
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None):
        mod_classes = []
        if config:
            python_modules = config.get('python_modules', ())
            for m in python_modules:
                mod = importlib.import_module(m)
        super().__init__()
        self.dataset = OpenKeyDictController[Dataset]()
        if config is not None:
            for k in list(config.keys()):
                cls = get_config_class(k, exception=False)
                if cls:
                    new_k = cls.name
                    if k != new_k:
                        config[new_k] = config[k]
                        del config[k]
                        k = new_k
                elif '.' in k:
                    new_k = k.rsplit('.', 1)[-1]
                    config[new_k] = config[k]
                    del config[k]
                    k = new_k
                if cls:
                    self.add_field(k, cls,
                                doc=cls.__doc__,
                                default_factory=cls)
                    mod_classes.append(cls)
            self.import_dict(config)
        self.executable = executable

        for cls in mod_classes:
            if hasattr(cls, 'init_execution_context'):
                cls.init_execution_context(self)


class ExecutionDatabase:
    def __init__(self, path):
        self.db = Database(path)
        self.collection = None
    
    def __enter__(self):
        session = self.session = self.db.__enter__()
        if not session.has_collection('status'):
            session.add_collection('status')
            status = session['status']
            status.add_field('status', str)
            status.add_field('execution_context', dict)
            status.add_field('start_time', datetime)
            status.add_field('end_time', datetime)
            # status.add_field('debug_messages', list[str])
            status.add_field('error', str)
            status.add_field('error_detail', str)
            status.add_field('executable', dict)
            status[''] = {}

            session.add_collection('jobs', 'uuid')
            jobs = session['jobs']
            jobs.add_field('command', list[str])
            jobs.add_field('wait_for', list[str])
            jobs.add_field('process', dict)
            jobs.add_field('parameters_location', list[str])

            session.add_collection('workflow', 'uuid')
            workflow = session['workflow']
            workflow.add_field('temporaries', dict)
            workflow.add_field('parameters', dict[str, list])
        return self
    
    def __exit__(self, *args):
        self.db.__exit__(*args)
        self.session = None
        
    @property
    def status(self):
        row = self.session['status'].document('', fields=['status'], as_list=True)
        if row is not None:
            return row[0]

    @status.setter
    def status(self, status):
        self.session['status'].update_document('', {'status': status})

    @property
    def execution_context(self):
        row = self.session['status'].document('', fields=['execution_context'], as_list=True)
        if row is not None:
            return ExecutionContext(config=row[0])

    @execution_context.setter
    def execution_context(self, execution_context):
        json_context = execution_context.json()
        for k in list(json_context):
            # replace module classes with long name, if they are not in the
            # standard location (capsul.config)
            m = getattr(execution_context, k)
            if isinstance(m, ModuleConfiguration) \
                    and m.__class__.__module__.split('.') \
                        != ['capsul', 'config', m.name]:
                cls_name = f'{m.__class__.__module__}.{m.__class__.__name__}'
                json_context[cls_name] = json_context[k]
                del json_context[k]

        self.session['status'].update_document('', {'execution_context': json_context})
    
    @property
    def executable(self):
        row = self.session['status'].document('', fields=['executable'], as_list=True)
        if row is not None:
            return Capsul.executable(row[0])

    @executable.setter
    def executable(self, executable):
        self.session['status'].update_document('', {'executable': executable.json()})
    
    @property
    def start_time(self):
        row = self.session['status'].document('', fields=['start_time'], as_list=True)
        if row is not None:
            return row[0]

    @start_time.setter
    def start_time(self, value):
        self.session['status'].update_document('', {'start_time': value})

    def save_workflow(self, workflow):
        for job_uuid, job in workflow.jobs.items():
            self.session['jobs'][job_uuid] = job
        self.session['workflow'][''] = {}
        self.workflow_parameters = workflow.parameters

    @property
    def workflow_parameters(self):
        row = self.session['workflow'].document('', fields=['parameters'], as_list=True)
        if row is not None:
            return DictWithProxy.from_json(row[0])
        return None
    
    @workflow_parameters.setter
    def workflow_parameters(self, parameters):
        self.session['workflow'].update_document('', {'parameters': parameters.json()})

    def jobs(self):
        return self.session['jobs'].documents()


class CapsulWorkflow(Controller):
    parameters: DictWithProxy
    jobs: dict
    
    def __init__(self, executable):
        super().__init__()
        self.find_temporary_to_generate(executable)
        self.parameters = DictWithProxy(all_proxies=True)
        self.jobs = {}
        jobs_per_process = {}
        process_chronology = {}
        processes_proxies = {}
        job_parameters = self._create_jobs(
            executable=executable,
            jobs_per_process=jobs_per_process,
            processes_proxies=processes_proxies,
            process_chronology=process_chronology,
            process=executable,
            parent_executables=[],
            parameters_location=[],
            disabled=False)
        self.parameters.content.update(job_parameters.content)

        # Set jobs chronology based on processes chronology
        for after_process, before_processes in process_chronology.items():
            for after_job in jobs_per_process.get(after_process, ()):
                for before_process in before_processes:
                    for before_job in jobs_per_process.get(before_process, ()):
                        aj = self.jobs[after_job]
                        aj['wait_for'].add(before_job)
                        bj = self.jobs[before_job]
                        if bj['command'] is None:
                            bj['waited_by'].add(after_job)

        # Resolve disabled jobs
        disabled_jobs = [(uuid, job) for uuid, job in self.jobs.items() if job['command'] is None]
        for disabled_job in disabled_jobs:
            wait_for = set()
            stack = disabled_job[1]['wait_for']
            while stack:
                job = stack.pop()
                if self.jobs[job]['command'] is None:
                    stack.update(self.jobs[job]['wait_for'])
                else:
                    wait_for.add(job)
            waited_by = set()
            stack = list(disabled_job[1]['waited_by'])
            while stack:
                job = stack.pop(0)
                if self.jobs[job]['command'] is None:
                    stack.extend(self.jobs[job]['waited_by'])
                else:
                    waited_by.add(job)
            for job in disabled_job[1]['waited_by']:
                self.jobs[job]['wait_for'].remove(disabled_job[0])
            del self.jobs[disabled_job[0]]
    
        # Transform wait_for sets to lists for json storage
        for job in self.jobs.values():
            job['wait_for'] = list(job['wait_for'])
    
    def _create_jobs(self,
                     executable,
                     jobs_per_process,
                     processes_proxies,
                     process_chronology,
                     process,
                     parent_executables,
                     parameters_location,
                     disabled):
        parameters = self.parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        nodes = []
        nodes_dict = parameters.content.setdefault('nodes', {})
        if isinstance(process, Pipeline):
            disabled_nodes = process.disabled_pipeline_steps_nodes()
            for node_name, node in process.nodes.items():
                if (node is process 
                    or not node.activated
                    or not isinstance(node, Process)
                    or node in disabled_nodes):
                    continue
                nodes_dict[node_name] = {}
                job_parameters = self._create_jobs(
                    executable=executable,
                    jobs_per_process=jobs_per_process,
                    processes_proxies=processes_proxies,
                    process_chronology=process_chronology,
                    process=node,
                    parent_executables=parent_executables + [process],
                    parameters_location=parameters_location + ['nodes',
                                                               node_name],
                    disabled=disabled or node in disabled_nodes)
                # nodes_dict[node_name].content.update(job_parameters.content)
                nodes.append(node)
            for field in process.user_fields():
                for dest_node, plug_name in executable.get_linked_items(process, 
                                                                        field.name,
                                                                        in_sub_pipelines=False):
                    if dest_node in disabled_nodes:
                        continue
                    #print('field name:', field.name, ', plug:', plug_name, ', dest_node:', dest_node.name, dest_node.name in nodes_dict, type(dest_node), ', executable:', executable.name, ', process:', process.name)
                    #print('parameters:', parameters.content)
                    parameters.content[field.name] = nodes_dict[dest_node.name][plug_name]
                    break
                if field.is_output():
                    for dest_node_name, dest_plug_name, dest_node, dest_plug, is_weak in process.plugs[field.name].links_to:
                        if dest_node.activated and dest_node not in disabled_nodes and not dest_node.field(dest_plug_name).is_output():
                            process_chronology.setdefault(dest_node.uuid, set()).add(process.uuid)
            for node in nodes:
                for plug_name in node.plugs:
                    first = nodes_dict[node.name].get(plug_name)
                    for dest_node, dest_plug_name in process.get_linked_items(node, plug_name,
                                                                              in_sub_pipelines=False):
                        
                        second = nodes_dict.get(dest_node.name, {}).get(dest_plug_name)
                        if dest_node.pipeline is not node.pipeline:
                            continue
                        if not parameters.is_proxy(first):
                            if parameters.is_proxy(second):
                                if first is not None:
                                    parameters.set_proxy_value(second, first)
                        elif not parameters.is_proxy(second):
                            if second is not None:
                                parameters.set_proxy_value(first, second)
                        else:
                            first_index = first[1]
                            second_index = second[1]
                            if first_index == second_index:
                                continue
                            elif first_index > second_index:
                                tmp = second
                                second = first
                                first = tmp
                                first_index = first[1]
                                second_index = second[1]
                            parameters.proxy_values[second_index] = first
        elif isinstance(process, ProcessIteration):
            parameters['_iterations'] = []
            iteration_index = 0
            for inner_process in process.iterate_over_process_parmeters():
                parameters['_iterations'].append({})
                job_parameters = self._create_jobs(
                    executable=executable,
                    jobs_per_process=jobs_per_process,
                    processes_proxies=processes_proxies,
                    process_chronology=process_chronology,
                    process=inner_process,
                    parent_executables=parent_executables + [process], 
                    parameters_location=parameters_location + ['_iterations', str(iteration_index)],
                    disabled=disabled)
                for k, v in job_parameters.content.items():
                    if k in process.iterative_parameters:
                        parameters.content.setdefault(k, []).append(v)
                    elif k in process.regular_parameters:
                        parameters.content[k] = v
                iteration_index += 1
            if isinstance(executable, Pipeline):
                for field in process.user_fields():
                    if field.is_output():
                        for dest_node, plug_name in executable.get_linked_items(process, field.name):
                            process_chronology.setdefault(dest_node.uuid, set()).add(process.uuid)
        elif isinstance(process, Process):
            job_uuid = str(uuid4())
            if disabled:
                self.jobs[job_uuid] = {
                    'command': None,
                    'wait_for': set(),
                    'waited_by': set(),
                }
            else:
                self.jobs[job_uuid] = {
                    'command': ['python', '-m', 'capsul.run', 'process', job_uuid],
                    'wait_for': set(),
                    'process': process.json(include_parameters=False),
                    'parameters_location': parameters_location
                }
            for parent_executable in parent_executables:
                jobs_per_process.setdefault(parent_executable.uuid, set()).add(job_uuid)
            jobs_per_process.setdefault(process.uuid, set()).add(job_uuid)
            for field in process.user_fields():
                if getattr(field, 'generate_temporary', False):
                    prefix = f'!{{dataset.tmp.path}}/{process.full_name}'
                    e = field.metadata('extensions')
                    if e:
                        suffix = e[0]
                    else:
                        suffix = ''
                    uuid = str(uuid4())
                    value = f'{prefix}.{field.name}_{uuid}{suffix}'
                else:
                    value = getattr(process, field.name, None)
                proxy = parameters.proxy(executable.json_value(value))
                parameters[field.name] = proxy
                if field.is_output() and isinstance(executable, Pipeline):
                    for dest_node, plug_name in executable.get_linked_items(process, field.name):
                        process_chronology.setdefault(dest_node.uuid, set()).add(process.uuid)
        return parameters

    def find_temporary_to_generate(self, executable):
        if isinstance(executable, Pipeline):
            nodes = executable.all_nodes()
        else:
            nodes = [executable]
        for node in nodes:
            for field in node.user_fields():
                field.generate_temporary = False
        self._find_temporary_to_generate(executable)
    
    
    def _find_temporary_to_generate(self, executable):
        """Finds all output fields that are empty and linked to an input
        and set their generate_temporary attribute to True (ans set it to
        False for other fields).
        """
        if isinstance(executable, Pipeline):
            for node in executable.nodes.values():
                if node is executable:
                    continue
                if isinstance(node, NipypeProcess):
                    #nipype processes do not use temporaries, they produce output
                    # file names
                    return

                if isinstance(node, ProcessIteration):
                    iteration_size = node.iteration_size()
                else:
                    iteration_size = None

                for plug_name, plug in node.plugs.items():
                    value = getattr(node, plug_name, undefined)
                    if not plug.activated or not plug.enabled:
                        continue
                    field = node.field(plug_name)
                    if field.output or not field.metadata('write', False):
                        continue
                    if field.is_list() and field.path_type is not None:
                        if value is not undefined and len([x for x in value if x in ('', undefined)]) == 0:
                            continue
                    elif value not in (undefined, '') \
                            or (field.path_type is None
                                or len(plug.links_to) == 0):
                        continue
                    # check that it is really temporary: not exported
                    # to the main pipeline
                    temporary = False
                    for n, pn in executable.get_linked_items(node, plug_name, in_sub_pipelines=False, process_only=False):
                        if n is executable:
                            continue
                        temporary = True
                        break
                    temporary = temporary or getattr(field, 'generate_temporary', False)
                    field.generate_temporary = temporary
                    for n, p in executable.get_linked_items(node, field.name):
                        f = n.field(p)
                        if f.is_output():
                            setattr(n.field(p), 'generate_temporary', temporary)
                self._find_temporary_to_generate(node)
        elif isinstance(executable, ProcessIteration):
            for name in executable.iterative_parameters:
                temporary = getattr(executable.field(name), 'generate_temporary', False)
                executable.process.field(name).generate_temporary = temporary
                if isinstance(executable.process, Pipeline):
                    for n, p in executable.process.get_linked_items(executable.process, name):
                        f = n.field(p)
                        if f.is_output():
                            setattr(n.field(p), 'generate_temporary', temporary)
            if isinstance(executable.process, Pipeline):
                self._find_temporary_to_generate(executable.process)
