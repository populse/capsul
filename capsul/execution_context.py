import importlib
import os
from uuid import uuid4

from soma.api import DictWithProxy, undefined
from soma.controller import (
    Controller,
    Directory,
    File,
    OpenKeyDictController,
    field,
    to_json_controller,
)

from capsul.config.configuration import get_config_class

from .config.configuration import ModuleConfiguration
from .dataset import Dataset
from .pipeline import pipeline_tools
from .pipeline.pipeline import Pipeline, Process
from .pipeline.process_iteration import IndependentExecutables, ProcessIteration


class ExecutionContext(Controller):
    python_modules: list[str] = field(type=list[str], default_factory=list)
    config_modules: list[str] = field(type=list[str], default_factory=list)
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None, activate_modules=False):
        super().__init__()
        if config:
            python_modules = config.get("python_modules", [])
            for m in python_modules:
                importlib.import_module(m)
            config_modules = config.get("config_modules", [])
            self.config_modules = config_modules
            for m in config_modules:
                # The following function loads the appropriate module
                get_config_class(m)
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
                elif "." in k:
                    new_k = k.rsplit(".", 1)[-1]
                    config[new_k] = config[k]
                    del config[k]
                    k = new_k
                if cls:
                    self.add_field(k, cls, doc=cls.__doc__, default_factory=cls)
            dataset = config.pop("dataset", None)
            if dataset:
                self.dataset = dataset
            self.import_dict(config)
        self.executable = executable
        if activate_modules:
            self.activate_modules_config()

    def activate_modules_config(self):
        for cm in self.config_modules:
            cls = get_config_class(cm)
            if hasattr(cls, "init_execution_context"):
                cls.init_execution_context(self)

    def json(self):
        json_context = self.json_controller()
        for k in list(json_context):
            # replace module classes with long name, if they are not in the
            # standard location (capsul.config)
            m = getattr(self, k)
            if isinstance(m, ModuleConfiguration) and m.__class__.__module__.split(
                "."
            ) != ["capsul", "config", m.name]:
                cls_name = f"{m.__class__.__module__}.{m.__class__.__name__}"
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
                if (
                    node is not executable
                    and isinstance(node, Process)
                    and node.activated
                ):
                    result.update(self.executable_requirements(node))
        result.update(getattr(executable, "requirements", {}))
        return result


class CapsulWorkflow(Controller):
    # parameters: DictWithProxy
    jobs: dict

    def __init__(self, executable, create_output_dirs=True, priority=None, debug=False):
        super().__init__()
        top_parameters = DictWithProxy(all_proxies=True)
        self.jobs = {}
        jobs_per_process = {}
        process_chronology = {}
        processes_proxies = {}
        enabled_nodes = None
        if isinstance(executable, (Pipeline, ProcessIteration)):
            pipeline_tools.propagate_meta(executable)
            if isinstance(executable, Pipeline):
                enabled_nodes = executable.enabled_pipeline_nodes()
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
            disabled=False,
            enabled_nodes=enabled_nodes,
            priority=priority,
            debug=debug,
        )
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
                        aj["wait_for"].add(before_job)
                        bj = self.jobs[before_job]
                        if bj["disabled"]:
                            bj.setdefault("waited_by", set()).add(after_job)

        # Resolve disabled jobs
        disabled_jobs = [
            (uuid, job) for uuid, job in self.jobs.items() if job["disabled"]
        ]
        for disabled_job in disabled_jobs:
            wait_for = set()
            stack = disabled_job[1]["wait_for"]
            while stack:
                job = stack.pop()
                if self.jobs[job]["disabled"]:
                    stack.update(self.jobs[job]["wait_for"])
                else:
                    wait_for.add(job)
            waited_by = set()
            stack = list(disabled_job[1].get("waited_by", ()))
            while stack:
                job = stack.pop(0)
                if self.jobs[job]["disabled"]:
                    stack.extend(self.jobs[job].get("waited_by", ()))
                else:
                    waited_by.add(job)
            for job in disabled_job[1].get("waited_by", ()):
                self.jobs[job]["wait_for"].remove(disabled_job[0])
            del self.jobs[disabled_job[0]]

        out_dirs = set()
        out_deps = []
        out_job_id = None

        # Transform wait_for sets to lists for json storage
        # and add waited_by
        for job_id, job in self.jobs.items():
            wait_for = list(job["wait_for"])
            job["wait_for"] = wait_for
            for waited in wait_for:
                self.jobs[waited].setdefault("waited_by", []).append(job_id)

            parameters = top_parameters
            for index in job["parameters_location"]:
                if index.isnumeric():
                    index = int(index)
                parameters = parameters[index]
            parameters_index = {}
            stack = list(
                (k, v[1]) for k, v in parameters.content.items() if k != "nodes"
            )
            while stack:
                k, i = stack.pop()
                i = self._no_proxy(parameters, i)
                v = parameters.proxy_values[i]
                if isinstance(v, list) and v and DictWithProxy.is_proxy(v[0]):
                    parameters_index[k] = [self._no_proxy(parameters, i) for i in v]
                else:
                    parameters_index[k] = i
            job["parameters_index"] = parameters_index

            if create_output_dirs:
                # record output directories
                outputs = job.get("write_parameters", [])
                add_dep = False
                for param in outputs:
                    todo = [parameters_index[param]]
                    pindices = []
                    while todo:
                        pind = todo.pop(0)
                        if isinstance(pind, (list, tuple)):
                            todo += pind
                        else:
                            pindices.append(pind)

                    value = [self.parameters_values[pind] for pind in pindices]
                    todo = value
                    while todo:
                        value = todo.pop(0)
                        if isinstance(value, (list, tuple)):
                            todo += value
                        elif isinstance(value, str):
                            dpath = os.path.normpath(os.path.dirname(value))
                            if not dpath:
                                continue  # skip empty dpath
                            # remove redundant paths (parents of others)
                            dpathf = os.path.join(dpath, "")
                            do_add = True
                            to_remove = []
                            for p in out_dirs:
                                if p.startswith(dpathf):
                                    # already a deeper one present
                                    do_add = False
                                    break
                                if dpath.startswith(os.path.join(p, "")):
                                    # current is deeper
                                    to_remove.append(p)
                            for p in to_remove:
                                out_dirs.remove(p)
                            if do_add:
                                out_dirs.add(dpath)
                            # anyway make a dependency of job over dir_job
                            add_dep = True
                if add_dep:
                    out_deps.append(job_id)
                    if out_job_id is None:
                        out_job_id = str(uuid4())
                    wait_for.insert(0, out_job_id)

        # print('out_dirs:', out_dirs)
        if len(out_dirs) != 0:
            self._create_directories_job(out_job_id, out_dirs, out_deps)

    @staticmethod
    def _no_proxy(parameters, i):
        if DictWithProxy.is_proxy(i):
            return CapsulWorkflow._no_proxy(parameters, i[1])
        v = parameters.proxy_values[i]
        if DictWithProxy.is_proxy(v):
            return CapsulWorkflow._no_proxy(parameters, v[1])
        return i

    def _create_jobs(
        self,
        top_parameters,
        executable,
        jobs_per_process,
        processes_proxies,
        process_chronology,
        process,
        parent_executables,
        parameters_location,
        process_iterations,
        disabled,
        enabled_nodes,
        priority=None,
        debug=None,
    ):
        # debug_plugs = ('output_transformation', 'normalization_transformation', 'transformation')
        parameters = top_parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        nodes = []
        nodes_dict = parameters.content.setdefault("nodes", {})
        if isinstance(process, Pipeline):
            find_temporary_to_generate(executable)
            disabled_nodes = process.disabled_pipeline_steps_nodes()
            for node_name, node in process.nodes.items():
                if (
                    node is process
                    or not node.activated
                    or not isinstance(node, Process)
                    or node in disabled_nodes
                ):
                    continue
                nodes_dict[node_name] = {}
                # print('create job for:', node.name)
                job_parameters = self._create_jobs(
                    top_parameters=top_parameters,
                    executable=executable,
                    jobs_per_process=jobs_per_process,
                    processes_proxies=processes_proxies,
                    process_chronology=process_chronology,
                    process=node,
                    parent_executables=parent_executables + [process],
                    parameters_location=parameters_location + ["nodes", node_name],
                    process_iterations=process_iterations,
                    disabled=disabled or node in disabled_nodes,
                    enabled_nodes=enabled_nodes,
                    priority=priority,
                    debug=debug,
                )
                nodes.append(node)
            for field in process.user_fields():  # noqa: F402
                # debug = (field.name in debug_plugs)
                # if debug: print('field:', process.name, '.', field.name)
                links = list(
                    executable.get_linked_items(
                        process,
                        field.name,
                        in_sub_pipelines=False,
                        direction="links_from",
                    )
                ) + list(
                    executable.get_linked_items(
                        process,
                        field.name,
                        in_sub_pipelines=False,
                        direction="links_to",
                    )
                )
                # if debug: print('proc links:', links)
                for dest_node, plug_name in links:
                    if dest_node in disabled_nodes:
                        continue
                    # debug = (debug and plug_name in debug_plugs)
                    # if debug: print('set', process.name, '.', field.name, '<->', dest_node.name, '.', plug_name, ', field write:', field.metadata('write', False), ', in content:', field.name in parameters.content)
                    if (
                        field.metadata("write", False)
                        and field.name in parameters.content
                    ):
                        nodes_dict.setdefault(dest_node.name, {})[plug_name] = (
                            parameters.content[field.name]
                        )
                        # if debug: print('-> add write in nodes_dict')
                    else:
                        parameters.content[field.name] = nodes_dict.get(
                            dest_node.name, {}
                        ).get(plug_name)
                        # if debug: print('<- add non_write in params')
                    # break
                if field.is_output():
                    for dest_node, dest_plug_name in executable.get_linked_items(
                        process,
                        field.name,
                        direction="links_to",
                        in_sub_pipelines=True,
                        in_outer_pipelines=True,
                    ):
                        if (
                            isinstance(dest_node, Process)
                            and dest_node.activated
                            and dest_node not in disabled_nodes
                            and not dest_node.field(dest_plug_name).is_output()
                        ):
                            if isinstance(dest_node, Pipeline):
                                continue
                            process_chronology.setdefault(
                                dest_node.uuid
                                + ",".join(process_iterations.get(dest_node.uuid, [])),
                                set(),
                            ).add(
                                process.uuid
                                + ",".join(process_iterations.get(process.uuid, []))
                            )
            for node in nodes:
                for plug_name in node.plugs:
                    # debug = (plug_name in debug_plugs)
                    # if debug: print('plug:', node.name, '.', plug_name)
                    first = nodes_dict[node.name].get(plug_name)
                    # if debug:
                    # print('links:', list(process.get_linked_items(
                    # node, plug_name,
                    # in_sub_pipelines=False,
                    # direction=('links_from', 'links_to'))))
                    for dest_node, dest_plug_name in process.get_linked_items(
                        node,
                        plug_name,
                        in_sub_pipelines=False,
                        direction=("links_from", "links_to"),
                    ):
                        second = nodes_dict.get(dest_node.name, {}).get(dest_plug_name)
                        # if debug: print('dest:', dest_node.name, dest_plug_name, dest_node.pipeline.name, node.pipeline.name)
                        if dest_node.pipeline is not node.pipeline:
                            continue
                        # if debug: print(first, second)
                        # if debug: print('proxies:', parameters.is_proxy(first), parameters.is_proxy(second))
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
                            # if debug: print('index:', first_index, second_index)
                            if first_index == second_index:
                                continue
                            elif first_index > second_index:
                                tmp = second
                                second = first
                                first = tmp
                                first_index = first[1]
                                second_index = second[1]
                            v1 = parameters.proxy_values[
                                self._no_proxy(parameters, first_index)
                            ]
                            v2 = parameters.proxy_values[
                                self._no_proxy(parameters, second_index)
                            ]
                            parameters.proxy_values[second_index] = first
                            if v1 is None and v2 is not None:
                                # move former dest value to source (temporary)
                                parameters.proxy_values[first_index] = v2
        elif isinstance(process, ProcessIteration):
            parameters["_iterations"] = []
            iteration_index = 0
            if isinstance(process.process, Pipeline):
                all_iterated_processes = [
                    p for p in process.process.all_nodes() if isinstance(p, Process)
                ]
            else:
                all_iterated_processes = [process.process]
            for inner_process in process.iterate_over_process_parmeters():
                if isinstance(inner_process, Pipeline):
                    find_temporary_to_generate(inner_process)
                parameters["_iterations"].append({})
                for p in all_iterated_processes:
                    process_iterations.setdefault(p.uuid, []).append(
                        str(iteration_index)
                    )
                new_priority = iteration_index
                if priority is not None:
                    new_priority += priority
                job_parameters = self._create_jobs(
                    top_parameters=top_parameters,
                    executable=executable,
                    jobs_per_process=jobs_per_process,
                    processes_proxies=processes_proxies,
                    process_chronology=process_chronology,
                    process=inner_process,
                    parent_executables=parent_executables + [process],
                    parameters_location=parameters_location
                    + ["_iterations", str(iteration_index)],
                    process_iterations=process_iterations,
                    disabled=disabled,
                    enabled_nodes=enabled_nodes,
                    priority=new_priority,
                    debug=debug,
                )
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
                        for dest_node, plug_name in executable.get_linked_items(
                            process,
                            field.name,
                            direction="links_to",
                            in_sub_pipelines=True,
                            in_outer_pipelines=True,
                        ):
                            if isinstance(dest_node, Pipeline):
                                continue
                            process_chronology.setdefault(
                                dest_node.uuid
                                + ",".join(process_iterations.get(dest_node.uuid, [])),
                                set(),
                            ).add(
                                process.uuid
                                + ",".join(process_iterations.get(process.uuid, []))
                            )
        elif isinstance(process, Process):
            # print('create process job for:', process.name)
            job_uuid = str(uuid4())
            if disabled:
                job = {
                    "uuid": job_uuid,
                    "disabled": True,
                    "wait_for": set(),
                    "waited_by": set(),
                }
            else:
                job = {
                    "uuid": job_uuid,
                    "disabled": enabled_nodes and process not in enabled_nodes,
                    "wait_for": set(),
                    "process": process.json(include_parameters=False),
                    "parameters_location": parameters_location,
                }
            if priority is not None:
                job["priority"] = priority
            self.jobs[job_uuid] = job
            for parent_executable in parent_executables:
                jobs_per_process.setdefault(
                    parent_executable.uuid
                    + ",".join(process_iterations.get(parent_executable.uuid, [])),
                    set(),
                ).add(job_uuid)
            jobs_per_process.setdefault(
                process.uuid + ",".join(process_iterations.get(process.uuid, [])), set()
            ).add(job_uuid)
            # print('!create_job!', process.full_name)
            opar = []
            wpar = []
            for field in process.user_fields():
                value = undefined
                if field.metadata().get("write", False):
                    wpar.append(field.name)
                if field.metadata().get("output", False):
                    opar.append(field.name)
                if getattr(field, "generate_temporary", False):
                    if field.type is File:
                        prefix = f"!{{dataset.tmp.path}}/{process.full_name}"
                        e = field.metadata("extensions")
                        if e:
                            suffix = e[0]
                        else:
                            suffix = ""
                        uuid = str(uuid4())
                        value = f"{prefix}.{field.name}_{uuid}{suffix}"
                    else:
                        # If we are here, field.type is list[File]
                        value = process.getattr(field.name, None)
                        if value:
                            for i in range(len(value)):
                                if not value[i]:
                                    prefix = (
                                        f"!{{dataset.tmp.path}}/{process.full_name}"
                                    )
                                    e = field.metadata("extensions")
                                    if e:
                                        suffix = e[0]
                                    else:
                                        suffix = ""
                                    uuid = str(uuid4())
                                    value[i] = (
                                        f"{prefix}.{field.name}_{i}_{uuid}{suffix}"
                                    )
                    # print('generate tmp:', value)
                if value is undefined:
                    value = process.getattr(field.name, None)
                # print('  ', field.name, '<-', repr(value), getattr(field, 'generate_temporary', False))
                # debug = (field.name in debug_plugs)
                proxy = parameters.proxy(to_json_controller(value))
                parameters[field.name] = proxy
                # if debug: print('create proxy for', field.name, ':', proxy)
                if field.is_output() and isinstance(
                    executable, (Pipeline, ProcessIteration)
                ):
                    for dest_node, plug_name in executable.get_linked_items(
                        process,
                        field.name,
                        direction="links_to",
                        in_sub_pipelines=True,
                        in_outer_pipelines=True,
                    ):
                        if isinstance(dest_node, Pipeline):
                            continue
                        process_chronology.setdefault(
                            dest_node.uuid
                            + ",".join(process_iterations.get(dest_node.uuid, [])),
                            set(),
                        ).add(
                            process.uuid
                            + ",".join(process_iterations.get(process.uuid, []))
                        )
            if opar:
                job["output_parameters"] = opar
            if wpar:
                job["write_parameters"] = wpar

        return parameters

    def find_job(self, full_name):
        for job in self.jobs.values():
            name = self.job_name(job)
            if name == full_name:
                return job
        return None

    def _create_directories_job(self, job_uuid, out_dirs, out_deps):
        if len(out_dirs) == 0:
            return None  # no dirs to create.
        name = "directories_creation"

        pindex = len(self.parameters_values)
        self.parameters_dict["nodes"][name] = {"directories": ["&", pindex]}
        self.parameters_values.append(list(out_dirs))
        self.jobs[job_uuid] = {
            "uuid": job_uuid,
            "disabled": False,
            "process": {
                "type": "process",
                "definition": "capsul.execution_context.CreateDirectories",
                "uuid": str(uuid4()),
            },
            "parameters_location": ["nodes", name],
            "parameters_index": {"directories": pindex},
            "wait_for": [],
            "waited_by": list(out_deps),
            "write_parameters": ["directories"],
        }

    def job_name(self, job):
        if isinstance(job, str):  # job_id
            job = self.jobs[job]

        return ".".join([x for x in job["parameters_location"] if x != "nodes"])

    def to_soma_workflow(self, name=None):
        """Convert a CapsulWorkflow to a Soma-Workflow Workflow object

        This conversion is provided for compatibility and used by older tools
        (Axon, Morphologist-UI) before they are ported to CapsulWorkflow.

        Remember that Soma-Workflow will be stopped and removed. This method
        will disappear also in the future, so it is already obsolete.

        In order to work, soma-workflow needs to be installed also.

        Each Capsul job is converted into a SWF job which will run using the
        commandline interface
        ``python -m capsul run --non-persistent <proc> [params...]``.
        This means that execution will be done in each Soma-Workflow job using
        the "full" Capsul execution system, which will run a local redis
        database and workers, just for a job. It is somewhat overkill, but
        allows to run Capsul pipelines integrated into Soma-Workflow-based
        tools.
        """
        import json
        import tempfile

        import soma_workflow.client as swc

        def resolve_tmp(value, temps, ref_param, param_dict, pname):
            if isinstance(value, list):
                return [
                    resolve_tmp(v, temps, ref_param, param_dict, "%s_%d" % (pname, i))
                    for i, v in enumerate(value)
                ]
            if isinstance(value, str) and value.startswith("!{dataset.tmp.path}"):
                tvalue = temps.get(value)
                if tvalue is not None:
                    ref_param.append(tvalue)
                    param_dict[pname] = tvalue
                    return tvalue
                if len(value) == 19:  # exactly temp dir
                    tvalue = tempfile.gettempdir()  # FIXME
                else:
                    tvalue = swc.TemporaryPath(suffix=value[20:])
                    ref_param.append(tvalue)
                temps[value] = tvalue
                param_dict[pname] = tvalue
                return tvalue
            return value

        deps = []
        job_map = {}
        temps = {}
        for job_id, cjob in self.jobs.items():
            cmd = [
                "python",
                "-m",
                "capsul",
                "run",
                "--non-persistent",
                cjob["process"]["definition"],
            ]
            ref_inputs = []
            ref_outputs = []
            param_dict = {}
            for param, index in cjob.get("parameters_index", {}).items():
                value = self.parameters_values[index]
                while isinstance(value, list) and len(value) == 2 and value[0] == "&":
                    value = value[1]
                if param in cjob.get("write_parameters", []):
                    ref_param = ref_outputs
                else:
                    ref_param = ref_inputs
                value = resolve_tmp(value, temps, ref_param, param_dict, param)
                try:
                    value = json.dumps(value)
                except TypeError:  # TemporaryPath are not jsonisable
                    pass
                if isinstance(value, str):
                    cmd.append(f"{param}={value}")
                else:
                    cmd.append(["<join>", f"{param}=", value])
            job = swc.Job(
                command=cmd,
                name=self.job_name(cjob) + " (" + cjob["process"]["definition"] + ")",
                param_dict=param_dict,
                referenced_input_files=ref_inputs,
                referenced_output_files=ref_outputs,
            )
            job_map[job_id] = job
            priority = cjob.get("priority")
            if priority is not None:
                job.priority = priority
            # TODO param links

        for job_id, cjob in self.jobs.items():
            for dep in cjob.get("wait_for", []):
                deps.append((job_map[dep], job_map[job_id]))

        wf = swc.Workflow(name=name, jobs=list(job_map.values()), dependencies=deps)
        return wf


def find_temporary_to_generate(executable):
    # print('!temporaries! ->', executable.label)
    if isinstance(executable, Pipeline):
        nodes = executable.all_nodes(in_iterations=True)
    elif isinstance(executable, ProcessIteration) and isinstance(
        executable.process, Pipeline
    ):
        nodes = executable.process.all_nodes(in_iterations=True)
        executable = executable.process
    else:
        nodes = [executable]
    for node in nodes:
        # print('!temporaries! initialize node', node.full_name)
        for field in node.user_fields():  # noqa: F402
            if (
                field.output
                or not field.metadata("write", False)
                or not node.plugs[field.name].activated
            ):
                field.generate_temporary = False
            else:
                field.generate_temporary = True
            if isinstance(node, ProcessIteration):
                node.process.field(
                    field.name
                ).generate_temporary = field.generate_temporary
            # print('!temporaries!  ', field.name, '=', field.generate_temporary)

    stack = [(executable, field) for field in executable.user_fields()]
    while stack:
        node, field = stack.pop(0)
        # print('!temporaries! no temporary for', node.full_name, ':', field.name)
        field.generate_temporary = False
        if isinstance(node, ProcessIteration):
            node.process.field(field.name).generate_temporary = field.generate_temporary
        for snode, parameter in executable.get_linked_items(
            node, field.name, direction="links_from", in_outer_pipelines=True
        ):
            if isinstance(node, ProcessIteration):
                stack.append((snode.process, snode.process.field(parameter)))
                # print('!temporaries!   + ', snode.process.full_name, ':', parameter)
            else:
                stack.append((snode, snode.field(parameter)))
                # print('!temporaries!   + ', snode.full_name, ':', parameter)

    # print('!temporaries!  parameters with temporary')
    # for n, p in temporaries:
    # print('!temporaries!   ', n, ':', p)


class CreateDirectories(Process):
    directories: list[Directory] = field(
        type_=list[Directory],
        write=True,
        doc="create output directories so that later processes can write "
        "their output files there.",
    )

    def execute(self, execution_context):
        for odir in self.directories:
            os.makedirs(odir, exist_ok=True)
