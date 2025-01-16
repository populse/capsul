import os
import subprocess
import sys
from datetime import datetime

from soma.controller import Controller, undefined

from ..api import Pipeline
from ..config.configuration import ModuleConfiguration
from ..database import engine_database
from ..execution_context import CapsulWorkflow, ExecutionContext


def execution_context(engine_label, engine_config, executable):
    config = {}

    # ExecutionContext constructor takes a config dict as input, *BUT* it is
    # not the engine_config we get here: engine_config contains all the
    # possible values of config modules, ie
    # {'spm': {'spm12-standalone': {...}, 'spm8': {...}}
    # whereas EXecutionContext expects an execution-side single, filtered
    # config: {'spm': {...}}
    # This filtering is done here in this function, but later after the context
    # is built.
    # So for now, give it only the dataset and config_modules part, removing
    # all modules config.
    cdict = engine_config.asdict()
    for conf_item in ("dataset", "config_modules", "python_modules"):
        if conf_item in cdict:
            config[conf_item] = cdict[conf_item]
    execution_context = ExecutionContext(
        executable=executable, config=config, activate_modules=False
    )

    req_to_check = execution_context.executable_requirements(executable)
    done_req = []  # record requirements to avoid loops
    valid_configs = {}
    needed_modules = set()
    invalid_needed_configs = {}

    # just now we filter configurations with requirements.
    while req_to_check:
        module_name, requirements = req_to_check.popitem()
        if (module_name, requirements) in done_req:
            continue
        done_req.append((module_name, requirements))
        needed_modules.add(module_name)

        module_configs = getattr(engine_config, module_name, None)
        if module_configs is None:
            # maybe the module is not loaded in the config. Load it.
            engine_config.add_module(module_name)
            module_configs = getattr(engine_config, module_name, {})
        if not isinstance(module_configs, Controller):
            raise ValueError(f'Unknown requirement: "{module_name}"')
        for module_field in module_configs.fields():
            module_config = getattr(module_configs, module_field.name)
            added_req = module_config.is_valid_config(requirements)
            if added_req not in (False, None):
                valid_configs.setdefault(module_name, {})[module_field] = module_config
                if isinstance(added_req, dict):
                    req_to_check.update(added_req)
            else:
                if module_name in needed_modules:
                    # Keep the invalid config in order to be able to display explanation
                    # later
                    invalid_needed_configs.setdefault(module_name, {})[module_field] = (
                        module_config
                    )

    # now check we have only one module for each
    for module_name in needed_modules:
        valid_module_configs = valid_configs.get(module_name)
        if valid_module_configs is None:
            message = (
                f'Execution environment "{engine_label}" has no '
                f"valid configuration for module {module_name}."
            )

            for module_field, module_config in invalid_needed_configs.get(
                module_name, {}
            ).items():
                # Get explanation about invalid config rejection
                explaination = module_config.is_valid_config(requirements, explain=True)
                message += f"\n  - {module_field.name} is not valid for requirements: {explaination}"

            raise RuntimeError(message)

        if len(valid_module_configs) > 1:
            # print(f"several {module_name} valid condfigs:")
            # for field, v in valid_module_configs.items():
            #     print(field.name, ":", v.asdict())
            # print(valid_module_configs)
            raise RuntimeError(
                f'Execution environment "{engine_label}" has '
                f"{len(valid_configs)} possible configurations for "
                f"module {module_name}"
            )
        # get the single remaining config
        valid_config = next(iter(valid_module_configs.values()))
        execution_context.add_field(
            module_name, type_=ModuleConfiguration, override=True
        )
        setattr(execution_context, module_name, valid_config)

    # context activation should be done only in real execution (server)
    # situation. This is done in database.execution_context(), not here
    # because here we are on client-side API.
    # execution_context.activate_modules_config()

    return execution_context


class Engine:
    """The Capsul Engine provides the client API for executions control.

    You normally get an Engine object from the application::

        from capsul.api import Capsul

        capsul = Capsul()  # plus options to reuse a config
        engine = capsul.engine()
        with engine as ce:
            # ce is self, actually
            print('current executions:', ce.executions_summary()

    The engine contains a reference to the engine config
    (:class:`~capsul.config.configuration.EngineConfiguration` object),
    normally selected from the :class:`~capsul.application.Capsul` object for
    the selected computing resource.
    """

    def __init__(self, label, config, databases_config, update_database=False):
        super().__init__()
        self.label = label
        self.config = config
        self.database_config = databases_config[self.config.database]
        self.database = engine_database(self.database_config)
        self.nested_context = 0
        self.update_database = update_database

    def __del__(self):
        if self.nested_context != 0:
            # force exit the engine
            self.nested_context = 1
            self.__exit__(None, None, None)

    def __enter__(self):
        if self.nested_context == 0:
            # Connect to the database
            self.database.__enter__()
            # Connect to the engine in the database. Adds the engine in
            # the database if it does not exist.
            self.engine_id = self.database.get_or_create_engine(
                self, update_database=self.update_database
            )
            self.config.persistent = self.database.persistent(self.engine_id)
        self.nested_context += 1
        return self

    @property
    def persistent(self):
        return self.database.persistent(self.engine_id)

    @persistent.setter
    def persistent(self, persistent):
        return self.database.set_persistent(self.engine_id, persistent)

    def engine_status(self):
        """ """
        result = {
            "label": self.label,
            "config": self.config.json(),
        }
        result["database_connected"] = self.database.is_connected
        if result["database_connected"]:
            result["database_ready"] = True
            database = self.database
        else:
            result["database_ready"] = self.database.is_ready
            if result["database_ready"]:
                database = engine_database(self.database_config)
            else:
                database = None
        if database:
            with database:
                engine_id = result["engine_id"] = database.engine_id(self.label)
                if engine_id:
                    result["workers_count"] = database.workers_count(engine_id)
                    result["connections"] = database.engine_connections(engine_id)
                    result["persistent"] = database.persistent(engine_id)
        return result

    def start_workers(self):
        """Start workers for the current engine.

        The engine configuration ``start_workers `` subsection allows to
        customize how workers will be started (local processes, or via ssh, or
        through a job management system...)
        """
        requested = self.config.start_workers.get("count", 0)
        start_count = max(0, requested - self.database.workers_count(self.engine_id))
        if start_count:
            for i in range(start_count):
                workers_command = self.database.workers_command(self.engine_id)
                # TODO: we should keep track of the running worker in order
                # to be able to contact / kill him later.
                try:
                    subprocess.run(
                        workers_command,
                        capture_output=False,
                        check=True,
                    )
                except Exception as e:

                    def quote(x):
                        return f"'{x}'"

                    raise RuntimeError(
                        f"Command failed: {' '.join(quote(i) for i in workers_command)}"
                    ) from e

    def kill_workers(self, worker_ids=None):
        if worker_ids is None:
            # kill all workers
            worker_ids = self.database_get_workers(self.engine_id)
        for worker_id in worker_ids:
            cmd = self.database.kill_worker_command(self.engine_id, worker_id)
            try:
                subprocess.run(
                    cmd,
                    capture_output=False,
                    check=True,
                )
            except Exception as e:

                def quote(x):
                    return f"'{x}'"

                raise RuntimeError(
                    f"Command failed: {' '.join(quote(i) for i in cmd)}"
                ) from e
            self.database.worker_ended(self.engine_id, worker_id)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        # exiting the engine disposes it from the database: executions will
        # be deleted from it, and later inspection will not be possible.
        # should we allow leaving the execution workflow in the database under
        # certain settings ?
        self.nested_context -= 1
        if self.nested_context == 0:
            if "CAPSUL_DEBUG" not in os.environ:
                self.database.dispose_engine(self.engine_id)
            self.database.__exit__(exception_type, exception_value, exception_traceback)
            del self.engine_id

    def execution_context(self, executable):
        """ """
        return execution_context(self.label, self.config, executable)

    def assess_ready_to_start(self, executable):
        """ """
        missing = []
        for field in executable.user_fields():
            value = getattr(executable, field.name)
            if value is undefined and not field.optional and not field.is_output():
                missing.append(field.name)
        if missing:
            raise ValueError(
                f"Value missing for the following parameters: {', '.join(missing)}"
            )

    def start(self, executable, debug=False):
        """Start the execution for an executable.

        Start workers if needed.

        Execution will be asynchronous: start() returns as soon as the workflow
        is pushed to the engine database. It can be monitored using
        :meth:`status`, :meth:`wait`, :meth:`stop` [TODO].

        :meth:`run` provides a shorthand for combining these methods to work as
        a synchronous (blocking) execution.
        """
        # Starts workers if necessary
        econtext = self.execution_context(executable)
        workflow = CapsulWorkflow(executable, debug=debug)
        # from pprint import pprint
        # print('!start!', flush=True)
        # pprint(workflow.jobs)
        # pprint(workflow.parameters.proxy_values)
        # pprint(workflow.parameters.content)
        # pprint(workflow.parameters.no_proxy())
        # print('----')
        # pprint(workflow.jobs)
        execution_id = self.database.new_execution(
            executable, self.engine_id, econtext, workflow, start_time=datetime.now()
        )
        self.start_workers()
        return execution_id

    def executions_summary(self):
        """ """
        with self:
            return self.database.executions_summary(self.engine_id)

    def status(self, execution_id):
        """ """
        return self.database.status(self.engine_id, execution_id)

    def wait(self, execution_id, *args, **kwargs):
        """Wait for the given execution to end.

        Keyword arguments may specify additional parameters

        Parameters
        ----------
        execution_id: str
            ID of the execution to be monitored
        timeout: float
            wait timeout (in seconds). If execution has not ended by that time,
            return anyway but the execution status will not be "done". If not
            provided (or None), wait() will not return before the execution is
            finished (which may block indefinitely in case of problem).
        """
        self.database.wait(self.engine_id, execution_id, *args, **kwargs)

    def stop(self, execution_id, kill_running=True):
        """Stop a running execution"""
        self.database.stop_execution(self.engine_id, execution_id)
        if kill_running:
            self.kill_jobs(execution_id)

    def kill_jobs(self, execution_id, job_ids=None):
        """Kill running jobs during execution

        Passing None as the job_ids argument kills all currently running jobs
        """
        self.database.kill_jobs(self.engine_id, execution_id, job_ids)

    def restart_jobs(
        self,
        execution_id: str,
        job_ids: list[str],
        force_stop: bool = False,
        allow_restart_execution: bool = False,
    ):
        """Restart jobs which have been stopped or have failed.

        Jobs are reset to ready or waiting state in the execution workflow,
        thus can be run again when their dependencies are satisfied.

        Parameters
        ----------
        execution_id: str
            execution ID
        job_ids: list[str]
            list of jobs to be restarted
        force_stop: bool
            if True, jobs in the job_ids list which are currently running are
            killed then reset to ready state. Otherwise a running job is not
            modified (we let it finish and do not restart it)
        allow_restart_execution: bool
            if the execution workflow is stopped, by default only the jobs
            state is modified, the workdlow is left waiting. If
            allow_restart_execution is True, then restart() is called and the
            workflow starts execution again.
        """
        raise NotImplementedError()

    def restart(self, execution_id):
        """Restart a workflow which has failed or has been stopped, and is
        thus not currently running.
        """
        raise NotImplementedError()

    def raise_for_status(self, *args, **kwargs):
        """Raises an exception according to the execution status."""
        self.database.raise_for_status(self.engine_id, *args, **kwargs)

    def execution_report(self, *args, **kwargs):
        """ """
        return self.database.execution_report(self.engine_id, *args, **kwargs)

    def print_execution_report(self, engine_id, *args, **kwargs):
        """ """
        self.database.print_execution_report(engine_id, *args, **kwargs)

    def update_executable(self, *args, **kwargs):
        self.database.update_executable(self.engine_id, *args, **kwargs)

    def dispose(self, *args, **kwargs):
        """Remove the given execution from the database and the associated
        resources (temporary files etc.)
        """
        self.database.dispose(self.engine_id, *args, **kwargs)

    def run(self, executable, timeout=None, print_report=False, debug=False, **kwargs):
        """Run synchronously an executable, blocking until execution has
        finished or a timeout has been reached.

        If execution does not finish without an error, an exception will be
        raised (also if a timeout occurs).

        Execution will not continue after the timeout, jobs will be stopped
        [should be.. ?](TODO).
        """
        for k, v in kwargs.items():
            setattr(executable, k, v)
        self.assess_ready_to_start(executable)
        execution_id = self.start(executable, debug=debug)
        try:
            try:
                self.wait(execution_id, timeout=timeout)
            except TimeoutError:
                self.print_execution_report(
                    self.execution_report(execution_id), sys.stderr
                )
                raise
            status = self.status(execution_id)
            self.raise_for_status(execution_id)
            if print_report:
                self.print_execution_report(
                    self.execution_report(execution_id), file=sys.stdout
                )
            self.update_executable(execution_id, executable)
        finally:
            if "CAPSUL_DEBUG" not in os.environ:
                self.dispose(execution_id)
        return status

    def prepare_pipeline_for_retry(self, pipeline, execution_id):
        """Modify a pipeline given a previous execution to select only the nodes that
        weren't successful. Running the pipeline after this step will retry the
        execution of failed jobs. This method sets a `self._enabled_nodes` attribute
        containing the list of active jobs. I such an attribute exists and is not
        empty, not job is created for any node outside this list.
        """
        # Parse successful nodes in previous execution and set the corresponding
        # "successfully_executed" steps.
        enabled_nodes = set()
        for path in self.database.failed_node_paths(self.engine_id, execution_id):
            node = pipeline
            for i in path[:-1]:
                node = node.nodes[i]
            failed_node = node.nodes[path[-1]]
            enabled_nodes.add(failed_node)
        pipeline._enabled_nodes = enabled_nodes or None


class Workers(Controller):
    def __init__(self, engine_label, engine_config, database):
        self.engine_label = engine_label
        self.engine_config = engine_config
        self.database = database
