# -*- coding: utf-8 -*-

from uuid import uuid4
import importlib

from soma.controller import Controller, OpenKeyDictController, File
from soma.api import DictWithProxy, undefined

from .dataset import Dataset
from .pipeline.pipeline import Process, Pipeline
from .pipeline.process_iteration import (IndependentExecutables,
                                         ProcessIteration)
from .pipeline import pipeline_tools
from capsul.config.configuration import get_config_class
from .config.configuration import ModuleConfiguration


class ExecutionContext(Controller):
    python_modules: list[str]
    config_modules: list[str]
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None):
        mod_classes = []
        if config:
            python_modules = config.get('python_modules', ())
            for m in python_modules:
                importlib.import_module(m)
            config_modules = config.get('config_modules', ())
            for m in config_modules:
                # The following function loads the appropriate module
                get_config_class(m)
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
            dataset = config.pop('dataset', None)
            if dataset:
                self.dataset = dataset
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
        if isinstance(executable, IndependentExecutables):
            result = {}
            for e in executable.executables:
                result.update(self.executable_requirements(e))
            return result
        elif isinstance(executable, ProcessIteration):
            for process in executable.iterate_over_process_parmeters():
                if process.activated:
                    result.update(self.executable_requirements(process))
        elif isinstance(executable, Pipeline):
            for node in executable.all_nodes():
                if node is not executable and isinstance(node, Process) \
                        and node.activated:
                    result.update(self.executable_requirements(node))
        result.update(getattr(executable, 'requirements', {}))
        return result


class CapsulWorkflow(Controller):
    # parameters: DictWithProxy
    jobs: dict

    def __init__(self, executable, debug=False):
        super().__init__()
        top_parameters = DictWithProxy(all_proxies=True)
        self.jobs = {}
        jobs_per_process = {}
        process_chronology = {}
        processes_proxies = {}
        nodes = pipeline_tools.topological_sort_nodes(executable.all_nodes())
        pipeline_tools.propagate_meta(executable, nodes)
        job_parameters = self._create_jobs(
            top_parameters=top_parameters,
            executable=executable,
            jobs_per_process=jobs_per_process,
            processes_proxies=processes_proxies,
            process_chronology=process_chronology,
            process=executable,
            parent_executables=[],
            parameters_location=[],
            process_iterations={},
            disabled=False)
        top_parameters.content.update(job_parameters.content)
        self.parameters_values = top_parameters.proxy_values
        self.parameters_dict = top_parameters.content
        # self.parameters = top_parameters

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
        disabled_jobs = [(uuid, job) for uuid, job in self.jobs.items()
                         if job['disabled']]
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
        for job_id, job in self.jobs.items():
            wait_for = list(job['wait_for'])
            job['wait_for'] = wait_for
            for waited in wait_for:
                self.jobs[waited].setdefault('waited_by',[]).append(job_id)

            parameters = top_parameters
            for index in job['parameters_location']:
                if index.isnumeric():
                    index = int(index)
                parameters = parameters[index]
            parameters_index = {}
            stack = list((k, v[1]) for k, v in parameters.content.items() if k != 'nodes')
            while stack:
                k, i = stack.pop()
                i = self._no_proxy(parameters, i)
                v = parameters.proxy_values[i]
                if isinstance(v, list) and v and DictWithProxy.is_proxy(v[0]):
                    parameters_index[k] = [self._no_proxy(parameters, i)
                                           for i in v]
                else:
                    parameters_index[k] = i
            job['parameters_index'] = parameters_index

    @staticmethod
    def _no_proxy(parameters, i):
        if DictWithProxy.is_proxy(i):
            return CapsulWorkflow._no_proxy(parameters, i[1])
        v = parameters.proxy_values[i]
        if DictWithProxy.is_proxy(v):
            return CapsulWorkflow._no_proxy(parameters, v[1])
        return i

    def _create_jobs(self,
                     top_parameters,
                     executable,
                     jobs_per_process,
                     processes_proxies,
                     process_chronology,
                     process,
                     parent_executables,
                     parameters_location,
                     process_iterations,
                     disabled):
        parameters = top_parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        nodes = []
        nodes_dict = parameters.content.setdefault('nodes', {})
        if isinstance(process, Pipeline):
            find_temporary_to_generate(executable)
            disabled_nodes = process.disabled_pipeline_steps_nodes()
            for node_name, node in process.nodes.items():
                if (node is process
                        or not node.activated
                        or not isinstance(node, Process)
                        or node in disabled_nodes):
                    continue
                nodes_dict[node_name] = {}
                job_parameters = self._create_jobs(
                    top_parameters=top_parameters,
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
                links = list(executable.get_linked_items(
                    process,
                    field.name,
                    in_sub_pipelines=False,
                    direction='links_from')) \
                    + list(executable.get_linked_items(
                        process,
                        field.name,
                        in_sub_pipelines=False,
                        direction='links_to'))
                for dest_node, plug_name in links:
                    if dest_node in disabled_nodes:
                        continue
                    if field.metadata('write', False) \
                            and field.name in parameters.content:
                        nodes_dict.get(dest_node.name, {})[plug_name] \
                            = parameters.content[field.name]
                    else:
                        parameters.content[field.name] \
                            = nodes_dict.get(dest_node.name, {}).get(plug_name)
                    # break
                if field.is_output():
                    for dest_node, dest_plug_name \
                            in executable.get_linked_items(
                                process, field.name, direction='links_to',
                                in_sub_pipelines=True,
                                in_outer_pipelines=True):
                        if (isinstance(dest_node, Process)
                                and dest_node.activated
                                and dest_node not in disabled_nodes
                                and not dest_node.field(
                                    dest_plug_name).is_output()):
                            if isinstance(dest_node, Pipeline):
                                continue
                            process_chronology.setdefault(
                                dest_node.uuid + ','.join(process_iterations.get(dest_node.uuid, [])),
                                set()).add(
                                    process.uuid + ','.join(process_iterations.get(process.uuid, [])))
            for node in nodes:
                for plug_name in node.plugs:
                    first = nodes_dict[node.name].get(plug_name)
                    for dest_node, dest_plug_name in process.get_linked_items(
                            node, plug_name,
                            in_sub_pipelines=False,
                            direction=('links_from', 'links_to')):

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
                            v1 = parameters.proxy_values[
                                self._no_proxy(parameters, first_index)]
                            v2 = parameters.proxy_values[
                                self._no_proxy(parameters, second_index)]
                            parameters.proxy_values[second_index] = first
                            if v1 is None and v2 is not None:
                                # move former dest value to source (temporary)
                                parameters.proxy_values[first_index] = v2
        elif isinstance(process, ProcessIteration):
            parameters['_iterations'] = []
            iteration_index = 0
            if isinstance(process.process, Pipeline):
                all_iterated_processes = [p for p in process.process.all_nodes() if isinstance(p, Process)]
            else:
                all_iterated_processes = [process.process]
            for inner_process in process.iterate_over_process_parmeters():
                if isinstance(inner_process, Pipeline):
                    find_temporary_to_generate(executable)
                parameters['_iterations'].append({})
                for p in all_iterated_processes:
                    process_iterations.setdefault(p.uuid, []).append(str(iteration_index))
                job_parameters = self._create_jobs(
                    top_parameters=top_parameters,
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
                        for dest_node, plug_name \
                                in executable.get_linked_items(
                                    process, field.name,
                                    direction='links_to',
                                    in_sub_pipelines=True,
                                    in_outer_pipelines=True):
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
                value = undefined
                if getattr(field, 'generate_temporary', False):
                    if field.type is File:
                        prefix = f'!{{dataset.tmp.path}}/{process.full_name}'
                        e = field.metadata('extensions')
                        if e:
                            suffix = e[0]
                        else:
                            suffix = ''
                        uuid = str(uuid4())
                        value = f'{prefix}.{field.name}_{uuid}{suffix}'
                    else:
                        # If we are here, field.type is list[File]
                        value = process.getattr(field.name, None)
                        if value:
                            for i in range(len(value)):
                                if not value[i]:
                                    prefix = f'!{{dataset.tmp.path}}/{process.full_name}'
                                    e = field.metadata('extensions')
                                    if e:
                                        suffix = e[0]
                                    else:
                                        suffix = ''
                                    uuid = str(uuid4())
                                    value[i] = f'{prefix}.{field.name}_{i}_{uuid}{suffix}'
                    # print('generate tmp:', value)
                if value is undefined:
                    value = process.getattr(field.name, None)
                # print('  ', field.name, '<-', repr(value), getattr(field, 'generate_temporary', False))
                proxy = parameters.proxy(executable.json_value(value))
                parameters[field.name] = proxy
                if field.is_output() and isinstance(
                        executable, (Pipeline, ProcessIteration)):
                    for dest_node, plug_name \
                            in executable.get_linked_items(
                                process, field.name,
                                direction='links_to',
                                in_sub_pipelines=True,
                                in_outer_pipelines=True):
                        if isinstance(dest_node, Pipeline):
                            continue
                        process_chronology.setdefault(
                            dest_node.uuid + ','.join(process_iterations.get(dest_node.uuid, [])), 
                            set()).add(
                                process.uuid + ','.join(process_iterations.get(process.uuid, [])))
        return parameters

    def find_job(self, full_name):
        for job in self.jobs.values():
            pl = [p for p in job['parameters_location'] if p != 'nodes']
            name = '.'.join(pl)
            if name == full_name:
                return job
        return None


def find_temporary_to_generate(executable):
    # print('!temporaries! ->', executable.label)
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
