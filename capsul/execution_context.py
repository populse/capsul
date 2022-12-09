# -*- coding: utf-8 -*-

from uuid import uuid4
import importlib

from soma.controller import Controller, OpenKeyDictController
from soma.api import DictWithProxy
from soma.undefined import undefined

from .dataset import Dataset
from .pipeline.pipeline import Process, Pipeline
from capsul.process.process import NipypeProcess
from .pipeline.process_iteration import ProcessIteration
from capsul.config.configuration import get_config_class
from .config.configuration import ModuleConfiguration


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

    def json(self):
        json_context = super().json()
        for k in list(json_context):
            # replace module classes with long name, if they are not in the
            # standard location (capsul.config)
            m = getattr(self, k)
            if isinstance(m, ModuleConfiguration) \
                    and m.__class__.__module__.split('.') \
                        != ['capsul', 'config', m.name]:
                cls_name = f'{m.__class__.__module__}.{m.__class__.__name__}'
                json_context[cls_name] = json_context[k]
                del json_context[k]
        return json_context

    def executable_requirements(self, executable):
        result = {}
        if isinstance(executable, ProcessIteration):
            for process in executable.iterate_over_process_parmeters():
                if process.activated:
                    result.update(self.executable_requirements(process))
        elif isinstance(executable, Pipeline):
            for node in executable.all_nodes():
                if node is not executable and isinstance(node, Process) and node.activated:
                    result.update(self.executable_requirements(node))
        result.update(getattr(executable, 'requirements', {}))
        return result


class CapsulWorkflow(Controller):
    parameters: DictWithProxy
    jobs: dict
    
    def __init__(self, executable, debug=False):
        super().__init__()
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
            process_iterations={},
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
                        if bj['disabled']:
                            bj['waited_by'].add(after_job)

        # Resolve disabled jobs
        disabled_jobs = [(uuid, job) for uuid, job in self.jobs.items() if job['disabled']]
        for disabled_job in disabled_jobs:
            wait_for = set()
            stack = disabled_job[1]['wait_for']
            while stack:
                job = stack.pop()
                if self.jobs[job]['disabled']:
                    stack.update(self.jobs[job]['wait_for'])
                else:
                    wait_for.add(job)
            waited_by = set()
            stack = list(disabled_job[1]['waited_by'])
            while stack:
                job = stack.pop(0)
                if self.jobs[job]['disabled']:
                    stack.extend(self.jobs[job]['waited_by'])
                else:
                    waited_by.add(job)
            for job in disabled_job[1]['waited_by']:
                self.jobs[job]['wait_for'].remove(disabled_job[0])
            del self.jobs[disabled_job[0]]
    
        # Transform wait_for sets to lists for json storage
        # and add waited_by
        for waiting, job in self.jobs.items():
            wait_for = list(job['wait_for'])
            job['wait_for'] = wait_for
            for waited in wait_for:
                self.jobs[waited].setdefault('waited_by',[]).append(waiting)
        
    def _create_jobs(self,
                     executable,
                     jobs_per_process,
                     processes_proxies,
                     process_chronology,
                     process,
                     parent_executables,
                     parameters_location,
                     process_iterations,
                     disabled):
        parameters = self.parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        nodes = []
        nodes_dict = parameters.content.setdefault('nodes', {})
        if isinstance(process, Pipeline):
            self.find_temporary_to_generate(executable, iteration_process=None)
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
                    process_iterations=process_iterations,
                    disabled=disabled or node in disabled_nodes)
                nodes.append(node)
            for field in process.user_fields():
                for dest_node, plug_name in executable.get_linked_items(process, 
                                                                        field.name,
                                                                        in_sub_pipelines=False):
                    if dest_node in disabled_nodes:
                        continue
                    parameters.content[field.name] = nodes_dict.get(dest_node.name, {}).get(plug_name)
                    break
                if field.is_output():
                    for dest_node_name, dest_plug_name, dest_node, dest_plug, is_weak in process.plugs[field.name].links_to:
                        if (isinstance(dest_node, Process) and dest_node.activated and 
                            dest_node not in disabled_nodes and 
                            not dest_node.field(dest_plug_name).is_output()):
                            if isinstance(dest_node, Pipeline):
                                continue
                            process_chronology.setdefault(
                                dest_node.uuid + ','.join(process_iterations.get(dest_node.uuid, [])),
                                set()).add(
                                    process.uuid + ','.join(process_iterations.get(process.uuid, [])))
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
            if isinstance(process.process, Pipeline):
                all_iterated_processes = [p for p in process.process.all_nodes() if isinstance(p, Process)]
            else:
                all_iterated_processes = [process.process]
            for inner_process in process.iterate_over_process_parmeters():
                if isinstance(inner_process, Pipeline):
                    self.find_temporary_to_generate(executable, iteration_process=process)
                parameters['_iterations'].append({})
                for p in all_iterated_processes:
                    process_iterations.setdefault(p.uuid, []).append(str(iteration_index))
                job_parameters = self._create_jobs(
                    executable=executable,
                    jobs_per_process=jobs_per_process,
                    processes_proxies=processes_proxies,
                    process_chronology=process_chronology,
                    process=inner_process,
                    parent_executables=parent_executables + [process], 
                    parameters_location=parameters_location + ['_iterations', str(iteration_index)],
                    process_iterations=process_iterations,
                    disabled=disabled)
                for k, v in job_parameters.content.items():
                    if k in process.iterative_parameters:
                        parameters.content.setdefault(k, []).append(v)
                    elif k in process.regular_parameters:
                        parameters.content[k] = v
                for p in all_iterated_processes:
                    del process_iterations[p.uuid][-1]
                iteration_index += 1
            if isinstance(executable, Pipeline):
                for field in process.user_fields():
                    if field.is_output():
                        for dest_node, plug_name in executable.get_linked_items(process, field.name, 
                                direction='links_to'):
                            if isinstance(dest_node, Pipeline):
                                continue
                            process_chronology.setdefault(
                                dest_node.uuid + ','.join(process_iterations.get(dest_node.uuid, [])),
                                set()).add(
                                    process.uuid + ','.join(process_iterations.get(process.uuid, []))
                                )
        elif isinstance(process, Process):
            job_uuid = str(uuid4())
            if disabled:
                self.jobs[job_uuid] = {
                    'uuid': job_uuid,
                    'disabled': True,
                    'wait_for': set(),
                    'waited_by': set(),
                }
            else:
                self.jobs[job_uuid] = {
                    'uuid': job_uuid,
                    'disabled': False,
                    'wait_for': set(),
                    'process': process.json(include_parameters=False),
                    'parameters_location': parameters_location
                }
            for parent_executable in parent_executables:
                jobs_per_process.setdefault(
                    parent_executable.uuid + ','.join(process_iterations.get(parent_executable.uuid, [])),
                    set()).add(job_uuid)
            jobs_per_process.setdefault(
                process.uuid + ','.join(process_iterations.get(process.uuid, [])),
                set()).add(job_uuid)
            # print('!create_job!', process.full_name)
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
                # print('  ', field.name, '<-', repr(value), getattr(field, 'generate_temporary', False))
                proxy = parameters.proxy(executable.json_value(value))
                parameters[field.name] = proxy
                if field.is_output() and isinstance(executable, (Pipeline, ProcessIteration)):
                    for dest_node, plug_name in executable.get_linked_items(process, field.name, 
                            direction='links_to'):
                        if isinstance(dest_node, Pipeline):
                            continue
                        process_chronology.setdefault(
                            dest_node.uuid + ','.join(process_iterations.get(dest_node.uuid, [])), 
                            set()).add(
                                process.uuid + ','.join(process_iterations.get(process.uuid, [])))
        return parameters

    def find_temporary_to_generate(self, executable, iteration_process):
        # print('!temporaries! ->', executable.label, iteration_process and iteration_process.label)
        if isinstance(executable, Pipeline):
            nodes = executable.all_nodes(in_iterations=True)
        elif isinstance(executable, ProcessIteration) and isinstance(executable.process, Pipeline):
            nodes = executable.process.all_nodes(in_iterations=True)
        else:
            nodes = [executable]
        for node in nodes:
            # print('!temporaries! initialize node', node.full_name)
            for field in node.user_fields():
                if (field.output or 
                    not field.metadata('write', False) or
                    not node.plugs[field.name].activated):
                    field.generate_temporary = False
                else:
                    field.generate_temporary = True
                if isinstance(node, ProcessIteration):
                    node.process.field(field.name).generate_temporary = field.generate_temporary
                # print('!temporaries!  ', field.name, '=', field.generate_temporary)

        stack = [(executable, field) for field in executable.user_fields()]
        while stack:
            node, field = stack.pop(0)
            # print('!temporaries! no temporary for', node.full_name, ':', field.name)
            field.generate_temporary = False
            if isinstance(node, ProcessIteration):
                node.process.field(field.name).generate_temporary = field.generate_temporary
            for node, parameter in executable.get_linked_items(
                    node, field.name, direction='links_from', in_outer_pipelines=True):
                if isinstance(node, ProcessIteration):
                    stack.append((node.process, node.process.field(parameter)))
                    # print('!temporaries!   + ', node.process.full_name, ':', parameter)
                else:
                    stack.append((node, node.field(parameter)))
                    # print('!temporaries!   + ', node.full_name, ':', parameter)

        # print('!temporaries!  parameters with temporary')
        # for n, p in temporaries:
            # print('!temporaries!   ', n, ':', p)


    # def _find_temporary_to_generate(self, executable, iteration_process):
    #     """Finds all output fields that are empty and linked to an input
    #     and set their generate_temporary attribute to True (and set it to
    #     False for other fields).
    #     """
    #     if isinstance(executable, Pipeline):
    #         print('!temporaries! ---------', executable.full_name, iteration_process and iteration_process.full_name)
    #         for node in executable.nodes.values():
    #             if node is executable:
    #                 continue
    #             if isinstance(node, NipypeProcess):
    #                 #nipype processes do not use temporaries, they produce output
    #                 # file names
    #                 return

    #             print('!temporaries 2!', node.full_name)
    #             for plug_name, plug in node.plugs.items():
    #                 print('!temporaries 3!', plug_name)
    #                 value = getattr(node, plug_name, undefined)
    #                 if not plug.activated or not plug.enabled:
    #                     continue
    #                 field = node.field(plug_name)
    #                 print('!  temporaries 3.1!', plug_name, field.output, field.metadata('write', False))
    #                 if field.output or not field.metadata('write', False):
    #                     continue
    #                 print('!  temporaries 3.2!', plug_name)
    #                 if field.is_list() and field.path_type:
    #                     if value is not undefined and len([x for x in value if x in ('', undefined)]) == 0:
    #                         continue
    #                 elif value not in (undefined, '') \
    #                         or (not field.path_type
    #                             or len(plug.links_to) == 0):
    #                     continue
    #                 # check that it is really temporary: not exported
    #                 # to the main pipeline
    #                 temporary = False
    #                 item_stack = list(executable.get_linked_items(node, plug_name, 
    #                     in_sub_pipelines=True, process_only=False, in_outer_pipelines=True,
    #                     direction='links_to'))
    #                 print('!  temporaries 3.3!', node.full_name, plug_name)
    #                 while item_stack:
    #                     n, pn = item_stack.pop(0)
    #                     print('!    temporary 3.3.1!  ', n.full_name, pn, n is executable, isinstance(n, Pipeline))
    #                     if n is executable and iteration_process:
    #                         print('!    temporary 3.3.2!  ', iteration_process.full_name, pn)
    #                         item_stack.extend(executable.get_linked_items(iteration_process, pn, 
    #                             in_sub_pipelines=True, process_only=False, in_outer_pipelines=True,
    #                             direction='links_to'))
    #                     if n is executable or isinstance(n, Pipeline):
    #                         continue
    #                     temporary = True
    #                     break
    #                 temporary = temporary or getattr(field, 'generate_temporary', False)
    #                 print('!  temporaries 4!', plug_name, temporary)
    #                 field.generate_temporary = temporary
    #                 if isinstance(node, ProcessIteration):
    #                     node.process.field(field.name).generate_temporary = temporary
    #                 for n, p in executable.get_linked_items(node, field.name, in_outer_pipelines=False):
    #                     print('!  temporaries 5!', n.full_name, p)
    #                     if isinstance(n, Pipeline):
    #                         continue
    #                     f = n.field(p)
    #                     if f.is_output():
    #                         print('!  temporaries 5.1!', n.full_name, p)
    #                         setattr(f, 'generate_temporary', temporary)
    #             if isinstance(node, ProcessIteration):
    #                 self._find_temporary_to_generate(node.process, node)
    #             else:
    #                 self._find_temporary_to_generate(node, None)
