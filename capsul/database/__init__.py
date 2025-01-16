import importlib
import json
import re
import sys
import time
from datetime import datetime
from pprint import pprint

import dateutil.parser
from populse_db.database import json_decode, json_encode
from soma.api import DictWithProxy, undefined

from ..application import Capsul
from ..execution_context import ExecutionContext
from ..pipeline.pipeline import Pipeline, Process

database_classes = {
    "populse-db": "capsul.database.populse_db:PopulseDBExecutionDatabase",
    "redis": "capsul.database.redis:RedisExecutionDatabase",
    "redis+socket": "capsul.database.redis:RedisExecutionDatabase",
}


class URL:
    pattern = re.compile(
        r"^(?P<scheme>[^:]+)://"
        r"(?:(?P<login>[^:]+)(?::(?P<password>[^@]+))?@)?"
        r"(?:(?P<host>[\w\.]+)(?::(?P<port>\d+))?)?"
        r"(?P<path>[^;?#]*)"
        r"(?:;(?P<parameters>[^?#]+))?"
        r"(?:\?(?P<query>[^#]+))?"
        r"(?:#(?P<fragment>.+))?$"
    )

    def __init__(self, string):
        m = self.pattern.match(string)
        if not m:
            raise ValueError(f"Invalid URL: {string}")
        for k, v in m.groupdict().items():
            setattr(self, k, v)

    def __str__(self):
        if self.login:
            if self.password:
                login = f"{self.login}:{self.password}@"
            else:
                login = f"{self.login}@"
        else:
            login = ""
        if self.host:
            if self.port:
                host = f"{self.host}:{self.port}"
            else:
                host = self.host
        else:
            host = ""
        if self.path:
            path = self.path
        else:
            path = ""
        if self.parameters:
            parameters = f";{self.parameters}"
        else:
            parameters = ""
        if self.query:
            query = f"?{self.query}"
        else:
            query = ""
        if self.fragment:
            fragment = f"#{self.fragment}"
        else:
            fragment = ""
        return f"{self.scheme}://{login}{host}{path}{parameters}{query}{fragment}"


class ResponseError(Exception):
    pass


class ConnectionError(Exception):
    pass


def engine_database(config):
    class_string = database_classes.get(config["type"])
    if class_string is None:
        raise ValueError(f"Invalid database type: {config['type']}")
    module_name, class_name = class_string.rsplit(":", 1)
    module = importlib.import_module(module_name)
    database_class = getattr(module, class_name)
    return database_class(config)


class ExecutionDatabase:
    def __init__(self, config):
        self.config = config
        self._path = None
        self.nested_context = 0

    @property
    def path(self):
        if self._path is None:
            self._path = self.config.get("path")
        return self._path

    def __enter__(self):
        if self.nested_context == 0:
            self._enter()
        self.nested_context += 1
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.nested_context -= 1
        if self.nested_context == 0:
            self._exit()

    def workers_command(self, engine_id):
        db_config = dict(self.worker_database_config(self.engine_id))
        # fix db path in case it is different from the initial config
        # (happens if path == "")
        db_config["path"] = self.path
        db_config = json.dumps(db_config, separators=(",", ":"))
        workers_command = []
        config = self.engine_config(engine_id)
        config = config.get("start_workers")
        if not config:
            raise RuntimeError("No configuration defined to start workers")
        ssh = config.get("ssh")
        if ssh:
            host = ssh.get("host")
            if not host:
                raise ValueError(
                    "Host is mandatory in configuration for a ssh connection"
                )
            login = ssh.get("login")
            if login:
                host = f"{login}@{host}"
            workers_command += ["ssh", "-o", "StrictHostKeyChecking=no", "-f", host]
            db_config = db_config.replace('"', r"\"").replace(",", r"\,")

        if config.get("type") == "torque":
            qsub = config.get("qsub", "qsub")
            workers_command += [
                qsub,
                "-l",
                "ncpus=1",
                "-e",
                "/dev/null",
                "-o",
                "/dev/null",
                "--",
            ]

        casa_dir = config.get("casa_dir")
        if casa_dir:
            workers_command.append(f"{casa_dir}/bin/bv")

        workers_command += [
            "python",
            "-m",
            "capsul.engine.builtin",
            engine_id,
            db_config,
        ]
        return workers_command

    def kill_worker_command(self, engine_id, worker_id):
        raise NotImplementedError

    def new_execution(
        self, executable, engine_id, execution_context, workflow, start_time
    ):
        executable_json = json_encode(executable.json(include_parameters=False))
        execution_context_json = execution_context.json()
        workflow_parameters_values_json = json_encode(workflow.parameters_values)
        workflow_parameters_dict_json = workflow.parameters_dict
        ready = []
        waiting = []
        jobs = [self._job_to_json(job.copy()) for job in workflow.jobs.values()]
        for job in jobs:
            if job["wait_for"]:
                waiting.append(job["uuid"])
            else:
                ready.append(job["uuid"])
        execution_id = self.store_execution(
            engine_id,
            label=executable.label,
            start_time=self._time_to_json(start_time),
            executable_json=executable_json,
            execution_context_json=execution_context_json,
            workflow_parameters_values_json=workflow_parameters_values_json,
            workflow_parameters_dict_json=workflow_parameters_dict_json,
            jobs=jobs,
            ready=ready,
            waiting=waiting,
        )
        return execution_id

    def _executable_from_json(self, executable_json):
        return Capsul.executable(json_decode(executable_json))

    def executable(self, execution_id):
        j = self.executable_json(execution_id)
        if j is not None:
            return self._executable_from_json(j)

    @staticmethod
    def _time_from_json(time_json):
        return dateutil.parser.parse(time_json)

    @staticmethod
    def _time_to_json(time):
        return time.isoformat()

    def _job_from_json(self, job):
        for k in ("start_time", "end_time"):
            t = job.get(k)
            if t:
                job[k] = self._time_from_json(t)
        return job

    def _job_to_json(self, job):
        for k in ("start_time", "end_time"):
            t = job.get(k)
            if t:
                job[k] = self._time_to_json(t)
        return job

    def job(self, engine_id, execution_id, job_uuid):
        j = self.job_json(engine_id, execution_id, job_uuid)
        if j:
            return self._job_from_json(j)
        return None

    def execution_report(self, engine_id, execution_id):
        report = self.execution_report_json(engine_id, execution_id)
        execution_context = report["execution_context"]
        if execution_context is not None:
            execution_context = ExecutionContext(config=execution_context)
        report["execution_context"] = execution_context
        for n in ("start_time", "end_time"):
            j = report.get(n)
            if j:
                report[n] = self._time_from_json(j)

        for job in report["jobs"]:
            self._job_from_json(job)
            if job["uuid"] in report["done"]:
                job["status"] = "done"
            elif job["uuid"] in report["failed"]:
                job["status"] = "failed"
            elif job["uuid"] in report["ongoing"]:
                job["status"] = "ongoing"
            elif job["uuid"] in report["ready"]:
                job["status"] = "ready"
            elif job["uuid"] in report["waiting"]:
                job["status"] = "waiting"
            else:
                job["status"] = "unknown"
        return report

    def job_parameters_from_values(self, job_dict, parameters_values):
        indices = job_dict.get("parameters_index", {})
        result = {}
        for k, i in indices.items():
            if isinstance(i, list):
                result[k] = [parameters_values[j] for j in i]
            else:
                result[k] = parameters_values[i]
        return result

    def failed_node_paths(self, engine_id, execution_id):
        raise NotImplementedError

    def print_execution_report(self, report, file=sys.stdout):
        print(
            "====================\n| Execution report |\n====================\n",
            file=file,
        )
        print("label:", report["label"], file=file)
        print("status:", report["status"], file=file)
        print("start time:", report["start_time"], file=file)
        print("end time:", report["end_time"], file=file)
        print("execution_id:", report["execution_id"], file=file)
        print("execution context:", file=file)
        pprint(report["execution_context"].asdict(), stream=file)
        if report["error"]:
            print("error:", report["error"], file=file)
        if report["error_detail"]:
            print("-" * 50, file=file)
            print(report["error_detail"], file=file)
            print("-" * 50, file=file)
        print("\n---------------\n| Jobs status |\n---------------\n", file=file)
        print("waiting:", report["waiting"])
        print("ready:", report["ready"])
        print("ongoing:", report["ongoing"])
        print("done:", report["done"])
        print("failed:", report["failed"])
        now = datetime.now()
        for job in sorted(
            report["jobs"],
            key=lambda j: (j.get("start_time") if j.get("start_time") else now),
        ):
            job_uuid = job["uuid"]
            process_definition = job.get("process", {}).get("definition")
            start_time = job.get("start_time")
            end_time = job.get("end_time")
            pipeline_node = ".".join(
                i for i in job.get("parameters_location", "") if i != "nodes"
            )
            return_code = job.get("return_code")
            status = job["status"]
            disabled = job["disabled"]
            stdout = job.get("stdout")
            stderr = job.get("stderr")
            input_parameters = job.get("input_parameters")
            output_parameters = job.get("output_parameters")
            wait_for = job.get("wait_for", [])
            waited_by = job.get("waited_by", [])

            print("=" * 50, file=file)
            print("job uuid:", job_uuid, file=file)
            print("process:", process_definition, file=file)
            print("pipeline node:", pipeline_node, file=file)
            print("status:", status, file=file)
            print("return code:", return_code, file=file)
            print("start time:", start_time, file=file)
            print("end time:", end_time, file=file)
            print("disabled:", disabled, file=file)
            print("wait for:", wait_for, file=file)
            print("waited_by:", waited_by, file=file)
            if input_parameters:
                print("input parameters:", file=file)
                pprint(input_parameters, stream=file)
            else:
                print("input parameters: none", file=file)
            if output_parameters:
                print("output parameters:", file=file)
                pprint(output_parameters, stream=file)
            else:
                print("output parameters: none", file=file)
            if stdout:
                print("---------- standard output ----------", file=file)
                print(stdout, file=file)
            if stderr:
                print("---------- error output ----------", file=file)
                print(stderr, file=file)

        if report["engine_debug"]:
            print(
                "\n----------------\n| Engine debug |\n----------------\n",
                file=file,
            )
            for k, v in report["engine_debug"].items():
                print(k, file=file)
                print("-" * len(k), file=file)
                print(v, file=file)
                print(file=file)

    def wait(self, engine_id, execution_id, timeout=None):
        start = time.time()
        status = self.status(engine_id, execution_id)
        if status == "ready":
            for i in range(100):
                time.sleep(0.2)
                status = self.status(engine_id, execution_id)
                if status != "ready":
                    break
            else:
                self.print_execution_report(
                    self.execution_report(engine_id, execution_id), file=sys.stderr
                )
                raise SystemError(
                    f"workers are too slow to start execution ({datetime.now()})"
                )
        status = self.status(engine_id, execution_id)
        while status != "ended":
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError("Process execution timeout")
            time.sleep(0.1)
            status = self.status(engine_id, execution_id)

    def raise_for_status(self, engine_id, execution_id):
        error = self.error(engine_id, execution_id)
        if error:
            self.print_execution_report(
                self.execution_report(engine_id, execution_id), file=sys.stderr
            )
            raise RuntimeError(error)

    def update_executable(self, engine_id, execution_id, executable):
        parameters = DictWithProxy.from_json_controller(
            dict(
                proxy_values=self.workflow_parameters_values(engine_id, execution_id),
                content=self.workflow_parameters_dict(engine_id, execution_id),
            )
        )
        # print('!update_executable!')
        # from pprint import pprint
        # pprint(parameters.proxy_values)
        # pprint(parameters.content)
        # pprint(parameters.no_proxy())
        if isinstance(executable, Pipeline):
            enable_parameter_links = executable.enable_parameter_links
            executable.enable_parameter_links = False
        else:
            enable_parameter_links = None
        try:
            stack = [(executable, parameters)]
            # print('!update_executable! stack', executable.full_name)
            # pprint(parameters.content)
            while stack:
                node, parameters = stack.pop(0)
                if parameters is None:
                    continue
                for field in node.user_fields():
                    value = parameters.get(field.name, undefined)
                    value = parameters.no_proxy(value)
                    if value is None:
                        value = undefined
                    if value is not undefined:
                        if isinstance(value, list) and field.is_list():
                            value = list((undefined if i is None else i) for i in value)
                        setattr(node, field.name, value)
                if isinstance(node, Pipeline):
                    stack.extend(
                        (n, parameters["nodes"].get(n.name))
                        for n in node.nodes.values()
                        if n is not node and isinstance(n, Process) and n.activated
                    )
        finally:
            if enable_parameter_links is not None:
                executable.enable_parameter_links = enable_parameter_links

    @property
    def is_ready(self):
        raise NotImplementedError

    @property
    def is_connected(self):
        raise NotImplementedError

    def engine_id(self, label):
        raise NotImplementedError

    def _enter(self):
        raise NotImplementedError

    def _exit(self):
        raise NotImplementedError

    def get_or_create_engine(self, engine, update_database=False):
        """
        If engine with given label is in the database, simply return its
        engine_id. Otherwise, create a new engine in the database and return
        its engine_id.

        if `update_database` is `True`, the current configuration is
        copied in the database even if the engine already exists.
        """
        raise NotImplementedError

    def engine_connections(self, engine_id):
        """
        Return the current number of active connections to
        an engine. This number is incremented within the context
        of an engine (with the `with` statement).
        """
        raise NotImplementedError

    def engine_config(self, engine_id):
        """
        Return the configuration dict stored for an engine
        """
        raise NotImplementedError

    def workers_count(self, engine_id):
        """
        Return the number of workers that are running.
        """
        raise NotImplementedError

    def worker_database_config(self, engine_id):
        """
        Return database connection settings for workers. This
        connection may be different than the client connection
        if the database implementation create engine specific
        internal access with restricted access rights.
        """
        raise NotImplementedError

    def worker_started(self, engine_id):
        """
        Register a new worker that had been started for this engine and
        return an identifier for it.
        """
        raise NotImplementedError

    def worker_ended(self, engine_id, worker_id):
        """
        Remove a worker from the list of workers for this engine.
        """
        raise NotImplementedError

    def get_workers(self, engine_id):
        """
        returns the workers IDs list
        """
        raise NotImplementedError

    def persistent(self, engine_id):
        """
        Return whether an engine is persistent or not.
        """
        raise NotImplementedError

    def set_persistent(self, engine_id, persistent):
        """
        Sets the persitency status of an engine.
        """
        raise NotImplementedError

    def dispose_engine(self, engine_id):
        """
        Tell Capsul that this engine will not be used anymore by any client.
        The resource it uses must be freed as soon as possible. If no
        execution is running, engine is destroyed. Otherwise, workers will
        process ongoing executions and cleanup when done.
        """
        raise NotImplementedError

    def executions_summary(self, engine_id):
        """
        Returns a JSON-compatible list whose elements contains some
        information about each execution. Each list element is a dict
        with the following items:
            - label: a kind of name of the execution to display to users
            - engine_id: id of the engine containing execution
            - execution_id: id of the execution
            - status: status of the execution
            - waiting: number of jobs in the waiting list
            - ready: number of jobs in the ready list
            - ongoing: number of jobs in the ongoing list
            - done: number of jobs in the done list
            - failed: number of jobs in the failed list
        """
        raise NotImplementedError

    def store_execution(
        self,
        engine_id,
        label,
        start_time,
        executable_json,
        execution_context_json,
        workflow_parameters_values_json,
        workflow_parameters_dict_json,
        jobs,
        ready,
        waiting,
    ):
        raise NotImplementedError

    def execution_context(self, engine_id, execution_id):
        j = self.execution_context_json(engine_id, execution_id)
        if j is not None:
            return ExecutionContext(config=j)

    def execution_context_json(self, engine_id, execution_id):
        raise NotImplementedError

    def pop_job(self, engine_id, start_time):
        """
        Convert its parameters to JSON and calls pop_job_json()
        """
        return self.pop_job_json(engine_id, self._time_to_json(start_time))

    def pop_job_json(self, engine_id, start_time):
        raise NotImplementedError

    def get_job_input_parameters(self, engine_id, execution_id, job_uuid):
        """
        Return a dictionary of input parameters to use for a job. Also store
        the returned dict with the job to ease the creation of job execution
        monitoring tools.
        """
        raise NotImplementedError

    def job_finished(
        self, engine_id, execution_id, job_uuid, end_time, return_code, stdout, stderr
    ):
        """
        Convert its parameters to JSON and calls job_finished_json()
        """
        self.job_finished_json(
            engine_id,
            execution_id,
            job_uuid,
            self._time_to_json(end_time),
            return_code,
            stdout,
            stderr,
        )

    def job_finished_json(
        self, engine_id, execution_id, job_uuid, end_time, return_code, stdout, stderr
    ):
        raise NotImplementedError

    def status(self, engine_id, execution_id):
        raise NotImplementedError

    def workflow_parameters_values(self, engine_id, execution_id):
        return json_decode(
            self.workflow_parameters_values_json(engine_id, execution_id)
        )

    def workflow_parameters_values_json(self, engine_id, execution_id):
        raise NotImplementedError

    def workflow_parameters_dict_json(self, engine_id, execution_id):
        raise NotImplementedError

    def job_json(self, engine_id, execution_id, job_uuid):
        raise NotImplementedError

    def execution_report_json(self, engine_id, execution_id):
        raise NotImplementedError

    def dispose(self, engine_id, execution_id):
        raise NotImplementedError

    def start_execution(self, engine_id, execution_id, tmp):
        raise NotImplementedError

    def end_execution(self, engine_id, execution_id):
        raise NotImplementedError

    def tmp(self, engine_id, execution_id):
        raise NotImplementedError

    def error(self, engine_id, execution_id):
        raise NotImplementedError

    def stop_execution(self, engine_id, execution_id):
        raise NotImplementedError

    def kill_jobs(self, engine_id, execution_id, job_ids):
        raise NotImplementedError
