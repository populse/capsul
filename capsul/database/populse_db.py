import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from populse_db import Storage
from soma.undefined import undefined

from . import ExecutionDatabase

schemas = [
    {
        "version": "1.0.0",
        "schema": {
            "capsul_engine": [
                {
                    "engine_id": [str, {"primary_key": True}],
                    "label": [str, {"index": True}],
                    "config": dict,
                    "workers": list[str],
                    "executions": list[str],
                    "persistent": bool,
                    "connections": int,
                }
            ],
            "capsul_connection": [
                {
                    "connection_id": [str, {"primary_key": True}],
                    "date": datetime,
                }
            ],
            "capsul_execution": [
                {
                    "engine_id": [str, {"primary_key": True}],
                    "execution_id": [str, {"primary_key": True}],
                    "label": str,
                    "status": str,
                    "tmp": str,
                    "error": str,
                    "error_detail": str,
                    "start_time": str,
                    "end_time": str,
                    "executable": dict,
                    "execution_context": dict,
                    "workflow_parameters_values": list,
                    "workflow_parameters_dict": dict,
                    "waiting": list[str],
                    "ready": list[str],
                    "ongoing": list[str],
                    "done": list[str],
                    "failed": list[str],
                    "dispose": bool,
                }
            ],
            "capsul_job": [
                {
                    "engine_id": [str, {"primary_key": True}],
                    "execution_id": [str, {"primary_key": True}],
                    "job_id": [str, {"primary_key": True}],
                    "job": dict,
                    "killed": bool,
                }
            ],
        },
    },
]


class PopulseDBExecutionDatabase(ExecutionDatabase):
    @property
    def is_ready(self):
        return os.path.exists(self.path)

    @property
    def is_connected(self):
        return False

    def engine_id(self, label):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                s = db.capsul_engine.search(
                    label=label, fields=["engine_id"], as_list=True
                )
                if s:
                    return s[0][0]

    def _enter(self):
        self.uuid = str(uuid4())

        if self.config["type"] == "populse-db":
            if self.path is None:
                raise ValueError("Database path is missing in configuration")
            if self.path == "":
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, prefix="capsul_", suffix=".sqlite"
                )
                try:
                    self._path = tmp.name
                    self.storage = Storage(self.path)
                    with self.storage.data(write=True) as db:
                        db.tmp = self.path
                except Exception:
                    os.remove(tmp.name)
                    raise
            else:
                self.storage = Storage(self.path)
        else:
            raise NotImplementedError(
                f"Invalid populse-db connection type: {self.config['type']}"
            )
        with self.storage.schema() as schema:
            schema.add_schema("capsul.database.populse_db")
        with self.storage.data(write=True) as db:
            db.capsul_connection[self.uuid] = {"date": datetime.now()}

    def _exit(self):
        if os.path.exists(self.path):
            with self.storage.data(write=True) as db:
                del db.capsul_connection[self.uuid]
            self.check_shutdown()

    def get_or_create_engine(self, engine, update_database=False):
        with self.storage.data(write=True) as db:
            row = db.capsul_engine.search(
                label=engine.label, fields=["engine_id"], as_list=True
            )
            persistent = engine.config.persistent
            if persistent is undefined:
                persistent = db.tmp.get() is None
            if row:
                engine_id = row[0][0]
                if update_database:
                    # Update configuration stored in database
                    db.capsul_engine[engine_id].update(
                        {
                            "congig": engine.config.json(),
                            "persistent": persistent,
                        }
                    )
            else:
                # Create new engine in database
                engine_id = str(uuid4())
                db.capsul_engine[engine_id] = {
                    "label": engine.label,
                    # config: Engine configuration dictionary
                    "config": engine.config.json(),
                    # workers: list of running workers
                    "workers": [],
                    # executions: list of execution_id
                    "executions": [],
                    "persistent": persistent,
                    # connections: number of connections
                    "connections": 0,
                }
            db.capsul_engine[engine_id].connections = (
                db.capsul_engine[engine_id].connections.get() + 1
            )
            return engine_id

    def engine_connections(self, engine_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_engine[engine_id].connections.get()

    def engine_config(self, engine_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                r = db.capsul_engine[engine_id].config.get()
                if r:
                    return r
        raise ValueError(f"Invalid engine_id: {engine_id}")

    def workers_count(self, engine_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                workers = db.capsul_engine[engine_id].workers.get()
                if workers:
                    return len(workers)
        return 0

    def worker_database_config(self, engine_id):
        return self.config

    def worker_started(self, engine_id):
        with self.storage.data(write=True, exclusive=True) as db:
            worker_id = str(uuid4())
            workers = db.capsul_engine[engine_id].workers.get()
            if workers is not None:
                workers.append(worker_id)
                db.capsul_engine[engine_id].workers = workers
        return worker_id
        raise ValueError(f"Invalid engine_id: {engine_id}")

    def worker_ended(self, engine_id, worker_id):
        with self.storage.data(write=True) as db:
            if not db:
                return
            workers = db.capsul_engine[engine_id].workers.get()
            if workers and worker_id in workers:
                workers.remove(worker_id)
                db.capsul_engine[engine_id].workers = workers

    def persistent(self, engine_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_engine[engine_id].persistent.get(False)
        return False

    def set_persistent(self, engine_id, persistent):
        with self.storage.data(write=True) as db:
            db.capsul_engine[engine_id].persistent = bool(persistent)

    def dispose_engine(self, engine_id):
        with self.storage.data(write=True) as db:
            row = db.capsul_engine[engine_id].get(
                fields=["connections", "persistent", "executions"], as_list=True
            )
            if row:
                connections, persistent, executions = row
                connections -= 1
                if connections == 0 and not persistent:
                    # Check if some executions had not been disposed
                    erase = True
                    for execution_id in executions:
                        dispose = db.capsul_execution[
                            engine_id, execution_id
                        ].dispose.get()
                        if dispose is not None and not dispose:
                            erase = False
                            break
                    if erase:
                        # Nothing is ongoing, completely remove engine
                        db.capsul_execution.search_and_delete(engine_id=engine_id)
                        db.capsul_engine.search_and_delete(engine_id=engine_id)
                        db.capsul_job.search_and_delete(engine_id=engine_id)
                else:
                    db.capsul_engine[engine_id].connections = connections
        self.check_shutdown()

    def executions_summary(self, engine_id):
        result = []
        if os.path.exists(self.path):
            with self.storage.data() as db:
                row = db.capsul_engine[engine_id].get(
                    fields=["label", "executions"], as_list=True
                )
                if row:
                    label, executions = row
                    for execution_id in executions:
                        info = db.capsul_execution[engine_id, execution_id].get(
                            fields=[
                                "execution_id",
                                "label",
                                "status",
                                "waiting",
                                "ready",
                                "ongoing",
                                "done",
                                "failed",
                            ],
                        )
                        if info:
                            for i in ("waiting", "ready", "ongoing", "done", "failed"):
                                info[i] = len(info[i])
                            info["engine_label"] = label
                            result.append(info)
        return result

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
        with self.storage.data(write=True) as db:
            execution_id = str(uuid4())
            executions = db.capsul_engine[engine_id].executions.get()
            if executions is not None:
                executions.append(execution_id)
                db.capsul_engine[engine_id].executions = executions
                if ready:
                    status = "ready"
                    end_time = None
                else:
                    status = "ended"
                    end_time = start_time

                db.capsul_execution[engine_id, execution_id] = dict(
                    label=label,
                    status=status,
                    start_time=start_time,
                    end_time=end_time,
                    executable=executable_json,
                    execution_context=execution_context_json,
                    workflow_parameters_values=workflow_parameters_values_json,
                    workflow_parameters_dict=workflow_parameters_dict_json,
                    ready=ready,
                    waiting=waiting,
                    ongoing=[],
                    done=[],
                    failed=[],
                    dispose=False,
                )
                for job in jobs:
                    db.capsul_job[engine_id, execution_id, job["uuid"]] = {
                        "job": job,
                        "killed": False,
                    }
            return execution_id

    def execution_context_json(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[
                    engine_id, execution_id
                ].execution_context.get()

    def pop_job_json(self, engine_id, start_time):
        if not os.path.exists(self.path):
            return None, None
        with self.storage.data(write=True) as db:
            if db is None:
                # database doesn't exist anymore
                executions = None
            else:
                executions = db.capsul_engine[engine_id].executions.get()
            if executions is None:
                # engine_id does not exist anymore
                # return None to say to workers that they can die
                return None, None
            all_disposed = True
            for execution_id in executions:
                dispose, status, ready, ongoing = db.capsul_execution[
                    engine_id, execution_id
                ].get(fields=["dispose", "status", "ready", "ongoing"], as_list=True)
                all_disposed = all_disposed and dispose
                if status == "ready":
                    db.capsul_execution[engine_id, execution_id].update(
                        {"status": "initialization"}
                    )
                    return execution_id, "start_execution"
                if status == "running":
                    if ready:
                        job_id = ready.pop(0)
                        ongoing.append(job_id)
                        db.capsul_execution[engine_id, execution_id].update(
                            {"ready": ready, "ongoing": ongoing}
                        )
                        db.capsul_job[
                            engine_id, execution_id, job_id
                        ].job.start_time = start_time
                        return execution_id, job_id
                if status == "finalization":
                    return execution_id, "end_execution"
            if all_disposed:
                # No more active execution, worker can die.
                return None, None
            else:
                # Empty string means "no job ready yet"
                return "", ""

    def job_finished_json(
        self, engine_id, execution_id, job_id, end_time, return_code, stdout, stderr
    ):
        with self.storage.data(write=True) as db:
            job = db.capsul_job[engine_id, execution_id, job_id].job.get()
            job["end_time"] = end_time
            job["return_code"] = return_code
            job["stdout"] = stdout
            job["stderr"] = stderr
            db.capsul_job[engine_id, execution_id, job_id].job = job

            ready, ongoing, failed, waiting, done = db.capsul_execution[
                engine_id, execution_id
            ].get(
                fields=["ready", "ongoing", "failed", "waiting", "done"], as_list=True
            )
            ongoing.remove(job_id)
            if return_code != 0:
                failed.append(job_id)

                stack = set(job.get("waited_by", []))
                while stack:
                    waiting_id = stack.pop()
                    if waiting_id in waiting:
                        waiting_job = db.capsul_job[
                            engine_id, execution_id, waiting_id
                        ].job.get()
                        waiting_job["return_code"] = (
                            "Not started because de dependent job failed"
                        )
                        db.capsul_job[
                            engine_id, execution_id, waiting_id
                        ].job = waiting_job
                        waiting.remove(waiting_id)
                        failed.append(waiting_id)
                    stack.update(waiting_job.get("waited_by", []))
            else:
                done.append(job_id)
                for waiting_id in job.get("waited_by", []):
                    waiting_job = db.capsul_job[
                        engine_id, execution_id, waiting_id
                    ].job.get()
                    ready_to_go = True
                    for waited in waiting_job.get("wait_for", []):
                        if waited not in done:
                            ready_to_go = False
                            break
                    if ready_to_go:
                        waiting.remove(waiting_id)
                        ready.append(waiting_id)
            db.capsul_execution[engine_id, execution_id].update(
                {
                    "ready": ready,
                    "ongoing": ongoing,
                    "failed": failed,
                    "waiting": waiting,
                    "done": done,
                }
            )

            if not ongoing and not ready:
                if failed:
                    db.capsul_execution[
                        engine_id, execution_id
                    ].error = "Some jobs failed"
                db.capsul_execution[engine_id, execution_id].update(
                    {
                        "status": "finalization",
                        "end_time": end_time,
                    }
                )

    def status(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[engine_id, execution_id].status.get()

    def workflow_parameters_values_json(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[
                    engine_id, execution_id
                ].workflow_parameters_values.get()

    def workflow_parameters_dict(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[
                    engine_id, execution_id
                ].workflow_parameters_dict.get()

    def get_job_input_parameters(self, engine_id, execution_id, job_id):
        with self.storage.data(write=True) as db:
            values = db.capsul_execution[
                engine_id, execution_id
            ].workflow_parameters_values.get()
            job = db.capsul_job[engine_id, execution_id, job_id].job.get()
            indices = job.get("parameters_index", {})
            result = {}
            for k, i in indices.items():
                if isinstance(i, list):
                    result[k] = [values[j] for j in i]
                else:
                    result[k] = values[i]
            db.capsul_job[engine_id, execution_id, job_id].job.input_parameters = result
            return result

    def set_job_output_parameters(
        self, engine_id, execution_id, job_id, output_parameters
    ):
        with self.storage.data(write=True) as db:
            values = db.capsul_execution[
                engine_id, execution_id
            ].workflow_parameters_values.get()
            job = db.capsul_job[engine_id, execution_id, job_id].job.get()
            indices = job.get("parameters_index", {})
            for name, value in output_parameters.items():
                values[indices[name]] = value
            db.capsul_job[
                engine_id, execution_id, job_id
            ].job.output_parameters = output_parameters
            db.capsul_execution[
                engine_id, execution_id
            ].workflow_parameters_values = values

    def job_json(self, engine_id, execution_id, job_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_job[engine_id, execution_id, job_id].job.get()

    def kill_jobs(self, engine_id, execution_id, job_ids=None):
        """Request killing of jobs"""
        # we just set a flag to 1 associated with the jobs to be killed.
        # Workers will poll for it while jobs are running, and react
        # accordingly.
        with self.storage.data(write=True) as db:
            if job_ids is None:
                job_ids = db.capsul_execution[engine_id, execution_id].ongoing.get()
            for job_id in job_ids:
                db.capsul_job[engine_id, execution_id, job_id].killed = True

    def job_kill_requested(self, engine_id, execution_id, job_id):
        with self.storage.data(write=True) as db:
            return db.capsul_job[engine_id, execution_id, job_id].killed.get()

    def execution_report_json(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                result = db.capsul_execution[engine_id, execution_id].get(
                    fields=[
                        "engine_id",
                        "execution_id",
                        "label",
                        "status",
                        "tmp",
                        "error",
                        "error_detail",
                        "start_time",
                        "end_time",
                        "executable",
                        "execution_context",
                        "workflow_parameters_values",
                        "waiting",
                        "ready",
                        "ongoing",
                        "done",
                        "failed",
                    ]
                )

                jobs = [
                    i[0]
                    for i in db.capsul_job.search(
                        fields=["job"],
                        as_list=True,
                        engine_id=engine_id,
                        execution_id=execution_id,
                    )
                ]
                result["jobs"] = jobs
                result["temporary_directory"] = result.pop("tmp")
                result["engine_debug"] = {}
                for job in jobs:
                    job["parameters"] = self.job_parameters_from_values(
                        job, result["workflow_parameters_values"]
                    )
                return result

    def failed_node_paths(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                failed = db.capsul_execution[engine_id, execution_id].failed.get()
                for job_uuid in failed:
                    job = db.capsul_job[engine_id, execution_id, job_uuid].job.get()
                    parameters_location = job.get("parameters_location")
                    if parameters_location:
                        result = tuple(i for i in parameters_location if i != "nodes")
                        if result != ("directories_creation",):
                            yield result

    def dispose(self, engine_id, execution_id, bypass_persistence=False):
        with self.storage.data(write=True) as db:
            db.capsul_execution[engine_id, execution_id].dispose = True
            status = db.capsul_execution[engine_id, execution_id].status.get()
            if status == "ended" and (
                bypass_persistence or not db.capsul_engine[engine_id].persistent.get()
            ):
                db.capsul_job.search_and_delete(
                    engine_id=engine_id, execution_id=execution_id
                )
                db.capsul_execution.search_and_delete(
                    engine_id=engine_id, execution_id=execution_id
                )
                executions = db.capsul_engine[engine_id].executions.get()
                executions.remove(execution_id)
                db.capsul_engine[engine_id].executions = executions

    def check_shutdown(self):
        database_empty = False
        if os.path.exists(self.path):
            with self.storage.data() as db:
                if db.capsul_connection.count() == 0:
                    if db.capsul_engine.count() == 0:
                        database_empty = True
        if database_empty and os.path.exists(self.path):
            os.remove(self.path)

    def start_execution(self, engine_id, execution_id, tmp):
        with self.storage.data(write=True) as db:
            db.capsul_execution[engine_id, execution_id].update(
                {
                    "status": "running",
                    "tmp": tmp,
                }
            )

    def end_execution(self, engine_id, execution_id):
        with self.storage.data(write=True) as db:
            tmp, dispose, label = db.capsul_execution[engine_id, execution_id].get(
                fields=["tmp", "dispose", "label"],
                as_list=True,
            )
            db.capsul_execution[engine_id, execution_id].update(
                {
                    "status": "ended",
                    "tmp": None,
                }
            )
            if dispose:
                executions = db.capsul_engine[engine_id].executions.get()
                executions.remove(execution_id)
                db.capsul_engine[engine_id].executions = executions
                db.capsul_job.search_and_delete(
                    engine_id=engine_id, execution_id=execution_id
                )
                db.capsul_execution.search_and_delete(
                    engine_id=engine_id, execution_id=execution_id
                )
                if not executions and not label:
                    # Engine is already disposed: delete it
                    db.capsul_execution.search_and_delete(engine_id=engine_id)
                    db.capsul_engine.search_and_delete(engine_id=engine_id)
                    db.capsul_job.search_and_delete(engine_id=engine_id)
                    self.check_shutdown()
            return tmp

    def tmp(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[engine_id, execution_id].tmp.get()

    def error(self, engine_id, execution_id):
        if os.path.exists(self.path):
            with self.storage.data() as db:
                return db.capsul_execution[engine_id, execution_id].error.get()
