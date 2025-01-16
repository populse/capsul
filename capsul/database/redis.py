import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from uuid import uuid4

import redis

from . import ConnectionError, ExecutionDatabase, ResponseError


class RedisExecutionDatabase(ExecutionDatabase):
    @property
    def is_ready(self):
        if self.config["type"] == "redis+socket":
            return os.path.exists(f"{self.path}.socket")
        else:
            try:
                r = self._connect(socket_connect_timeout=0.2)
                r.ping()
                return True
            except (redis.ConnectionError, redis.TimeoutError):
                return False

    def _connect(self, **kwargs):
        r = redis.Redis(
            host=self.config["host"], port=self.config.get("port"), **kwargs
        )
        if self.config.get("login"):
            r.auth(self.config["password"], self.config["login"])
        return r

    @property
    def is_connected(self):
        return hasattr(self, "redis")

    def engine_id(self, label):
        return self.redis.hget("capsul:engine", label)

    def _enter(self):
        self.uuid = str(uuid4())

        if self.config["type"] == "redis+socket":
            if self.path is None:
                raise ValueError("Database path is missing in configuration")
            self.redis_socket = f"{self.path}.socket"

            if self.path == "" or not os.path.exists(self.redis_socket):
                # Start the redis server
                tmp = tempfile.mkdtemp(prefix="capsul_redis_")
                try:
                    if self.path == "":
                        self._path = os.path.join(tmp, "database.rdb")
                        self.redis_socket = f"{self.path}.socket"
                    dir, dbfilename = os.path.split(self.path)
                    pid_file = f"{tmp}/redis.pid"
                    log_file = f"{tmp}/redis.log"
                    cmd = [
                        "redis-server",
                        "--unixsocket",
                        self.redis_socket,
                        "--port",
                        "0",  # port 0 means no TCP connection
                        "--daemonize",
                        "yes",
                        "--pidfile",
                        pid_file,
                        "--dir",
                        dir,
                        "--logfile",
                        log_file,
                        "--dbfilename",
                        dbfilename,
                        # Snapshot every 60 seconds if at least one change
                        # had been done to the database
                        "--save",
                        "60",
                        "1",
                    ]
                    subprocess.run(cmd, cwd=tmp)
                    for i in range(20):
                        if os.path.exists(self.redis_socket):
                            break
                        time.sleep(0.1)
                    self.redis = redis.Redis(
                        unix_socket_path=self.redis_socket, decode_responses=True
                    )
                    self.redis.delete("capsul:shutting_down")
                    self.redis.set("capsul:redis_tmp", tmp)
                    self.redis.set("capsul:redis_pid_file", pid_file)
                except Exception as e:
                    shutil.rmtree(tmp)
                    # translate exception type
                    exc_types = {
                        redis.ConnectionError: ConnectionError,
                        redis.ResponseError: ResponseError,
                        redis.TimeoutError: TimeoutError,
                    }
                    exc_type = exc_types.get(type(e))
                    if exc_type is not None:
                        exc = exc_type(e.args)
                        exc.with_traceback(e.__traceback__)
                        raise e from None
                    raise
            else:
                self.redis = redis.Redis(
                    unix_socket_path=self.redis_socket, decode_responses=True
                )
        elif self.config["type"] == "redis":
            self.redis = self._connect(decode_responses=True)
        else:
            raise NotImplementedError(
                f"Invalid Redis connection type: {self.config['type']}"
            )
        if self.redis.get("capsul:shutting_down"):
            raise RuntimeError(
                "Cannot connect to database because it is shutting down: "
                f"{self._path}: {self.redis_socket}"
            )
        self.redis.hset("capsul:connections", self.uuid, datetime.now().isoformat())

        # Some functions are implemented as a Lua script in redis
        # in order to be atomic. In redis these scripts must always
        # be registered before using them.
        self._store_execution = self.redis.register_script(
            """
            local engine_key = KEYS[1]
            local execution_key = KEYS[2]

            local execution_id = ARGV[1]
            local label = ARGV[2]
            local start_time = ARGV[3]
            local executable_json = ARGV[4]
            local execution_context_json = ARGV[5]
            local workflow_parameters_values_json = ARGV[6]
            local workflow_parameters_dict_json = ARGV[7]
            local jobs = cjson.decode(ARGV[8])
            local ready = ARGV[9]
            local waiting = ARGV[10]

            local executions = cjson.decode(redis.call('hget', engine_key, 'executions'))
            table.insert(executions, execution_id)
            redis.call('hset', engine_key, 'executions', cjson.encode(executions))

            redis.call('hset', execution_key, 'label', label)
            redis.call('hset', execution_key, 'status', 'ready')
            redis.call('hset', execution_key, 'start_time', start_time)
            redis.call('hset', execution_key, 'executable', executable_json)
            redis.call('hset', execution_key, 'execution_context', execution_context_json)
            redis.call('hset', execution_key, 'workflow_parameters_values', workflow_parameters_values_json)
            redis.call('hset', execution_key, 'workflow_parameters_dict', workflow_parameters_dict_json)

            redis.call('hset', execution_key, 'ready', ready)
            --  An empty list modified with Redis Lua scripts may be encoded as empty dict
            if ready  == '[]' or ready == '{}' then
                redis.call('hset', execution_key, 'status', 'ended')
                redis.call('hset', execution_key, 'end_time', start_time)
            end

            redis.call('hset', execution_key, 'waiting', waiting)
            redis.call('hset', execution_key, 'ongoing', '[]')
            redis.call('hset', execution_key, 'done', '[]')
            redis.call('hset', execution_key, 'failed', '[]')

            for _, job in pairs(jobs) do
                redis.call('hset', execution_key, 'job:' .. job['uuid'], cjson.encode(job))
            end
            """
        )

        self._pop_job = self.redis.register_script(
            """
            local execution_key = KEYS[1]

            local start_time = ARGV[1]

            local status = redis.call('hget', execution_key, 'status')

            if status == 'ready' then
                redis.call('hset', execution_key, 'status', 'initialization')
                return 'start_execution'
            end
            if status == 'running' then
                local ready = cjson.decode(redis.call('hget', execution_key, 'ready'))
                if next(ready) ~= nil then
                    local job_uuid = table.remove(ready, 1)
                    redis.call('hset', execution_key, 'ready', cjson.encode(ready))
                    local job_key = 'job:' .. job_uuid
                    local job = cjson.decode(redis.call('hget', execution_key, job_key))
                    job['start_time'] = start_time
                    job = cjson.encode(job)
                    redis.call('hset', execution_key, job_key, job)
                    local ongoing = cjson.decode(redis.call('hget', execution_key, 'ongoing'))
                    table.insert(ongoing, job_uuid)
                    redis.call('hset', execution_key, 'ongoing', cjson.encode(ongoing))
                    return job_uuid
                end
            end
            if status == 'finalization' then
                return 'end_execution'
            end
            return nil
        """
        )

        self._job_finished = self.redis.register_script(
            """
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local engine_key = KEYS[1]
            local execution_key = KEYS[2]

            local execution_id = ARGV[1]
            local job_uuid = ARGV[2]
            local end_time = ARGV[3]
            local return_code = ARGV[4]
            local stdout = ARGV[5]
            local stderr = ARGV[6]

            local job_key = 'job:' .. job_uuid
            local job = cjson.decode(redis.call('hget', execution_key, job_key))
            job['end_time'] = end_time
            job['return_code'] = return_code
            job['stdout'] = stdout
            job['stderr'] = stderr
            redis.call('hset', execution_key, job_key, cjson.encode(job))

            local ready = cjson.decode(redis.call('hget', execution_key, 'ready'))
            local ongoing = cjson.decode(redis.call('hget', execution_key, 'ongoing'))
            local failed = cjson.decode(redis.call('hget', execution_key, 'failed'))
            local waiting = cjson.decode(redis.call('hget', execution_key, 'waiting'))
            local done = cjson.decode(redis.call('hget', execution_key, 'done'))


            table.remove(ongoing, table_find(ongoing, job_uuid))
            redis.call('hdel', execution_key, 'kill_job:' .. job_uuid)

            if return_code ~= '0' then
                table.insert(failed, job_uuid)

                local stack = {}
                if job['waited_by'] then
                    for key, value in pairs(job['waited_by']) do
                        stack[key] = value
                    end
                end

                local uuid = table.remove(stack)
                while uuid do
                    local job_key = 'job:' .. uuid
                    job = cjson.decode(redis.call('hget', execution_key, job_key))
                    job['return_code'] = 'Not started because de dependent job failed'
                    redis.call('hset', execution_key, job_key, cjson.encode(job))
                    local waiting_index = table_find(waiting, uuid)
                    if waiting_index then
                        table.remove(waiting, waiting_index)
                        table.insert(failed, uuid)
                        if job['waited_by'] then
                            for key, value in ipairs(job['waited_by']) do
                                table.insert(stack, value)
                            end
                        end
                    end
                    uuid = table.remove(stack)
                end
            else
                table.insert(done, job_uuid)
                if job['waited_by'] then
                    for _, waiting_uuid in ipairs(job['waited_by']) do
                        local waiting_job = cjson.decode(redis.call('hget', execution_key, 'job:' .. waiting_uuid))
                        local ready_to_go = true
                        if waiting_job['wait_for'] then
                            for _, waited in ipairs(waiting_job['wait_for']) do
                                if not table_find(done, waited) then
                                    ready_to_go = false
                                    break
                                end
                            end
                        end
                        if ready_to_go then
                            table.remove(waiting, table_find(waiting, waiting_uuid))
                            table.insert(ready, waiting_uuid)
                        end
                    end
                end
            end

            redis.call('hset', execution_key, 'ready', cjson.encode(ready))
            redis.call('hset', execution_key, 'ongoing', cjson.encode(ongoing))
            redis.call('hset', execution_key, 'failed', cjson.encode(failed))
            redis.call('hset', execution_key, 'waiting', cjson.encode(waiting))
            redis.call('hset', execution_key, 'done', cjson.encode(done))

            if (next(ongoing) == nil) and (next(ready) == nil) then
                if next(failed) ~= nil then
                    redis.call('hset', execution_key, 'error', 'Some jobs failed')
                end
                redis.call('hset', execution_key, 'status', 'finalization')
                redis.call('hset', execution_key, 'end_time', end_time)
            end
        """
        )

        self._dispose = self.redis.register_script(
            """
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local engine_key = KEYS[1]
            local execution_key = KEYS[2]

            local execution_id = ARGV[1]
            local bypass_persistence = ARGV[2]

            redis.call('hset', execution_key, 'dispose', 1)
            if (redis.call('hget', execution_key, 'status') == 'ended') and
               (bypass_persistence ~= '0' or (redis.call('hget', engine_key, 'persistent') == '0')) then
                redis.call('del', execution_key)
                local executions = cjson.decode(redis.call('hget', engine_key, 'executions'))
                table.remove(executions, table_find(executions, execution_id))
                redis.call('hset', engine_key, 'executions', cjson.encode(executions))
            end
            """
        )

        self._worker_started = self.redis.register_script(
            """
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local engine_key = KEYS[1]

            local worker_id = ARGV[1]

            local workers = redis.call('hget', engine_key, 'workers')
            if workers then
                workers = cjson.decode(workers)
                table.insert(workers, worker_id)
                redis.call('hset', engine_key, 'workers', cjson.encode(workers))
            end
        """
        )

        self._worker_ended = self.redis.register_script(
            """
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local engine_key = KEYS[1]

            local worker_id = ARGV[1]

            local workers = redis.call('hget', engine_key, 'workers')
            if workers then
                workers = cjson.decode(workers)
                table.remove(workers, table_find(workers, worker_id))
                redis.call('hset', engine_key, 'workers', cjson.encode(workers))
            end
        """
        )

        self._full_report = self.redis.register_script(
            """
            local execution_key = KEYS[1]

            local label = redis.call('hget', execution_key, 'label')
            local execution_context = redis.call('hget', execution_key, 'execution_context')
            local status = redis.call('hget', execution_key, 'status')
            local error = redis.call('hget', execution_key, 'error')
            local error_detail = redis.call('hget', execution_key, 'error_detail')
            local start_time = redis.call('hget', execution_key, 'start_time')
            local end_time = redis.call('hget', execution_key, 'end_time')
            local waiting = cjson.decode(redis.call('hget', execution_key, 'waiting'))
            local ready = cjson.decode(redis.call('hget', execution_key, 'ready'))
            local ongoing = cjson.decode(redis.call('hget', execution_key, 'ongoing'))
            local done = cjson.decode(redis.call('hget', execution_key, 'done'))
            local failed = cjson.decode(redis.call('hget', execution_key, 'failed'))
            local jobs = {}
            local cursor = 0
            repeat
                local result = redis.call('hscan', execution_key, cursor, 'MATCH', 'job:*')
                cursor = tonumber(result[1])
                for i, job in ipairs(result[2]) do
                    if i % 2 == 0 then
                        table.insert(jobs, job)
                    end
                end
            until cursor == 0

            return {label, execution_context, status, error, error_detail,
                start_time, end_time, waiting, ready, ongoing, done, failed,
                jobs}
            """
        )

        self._check_shutdown = self.redis.register_script(
            """
            if redis.call('get', 'capsul:redis_pid_file') and
               redis.call('hlen', 'capsul:connections') == 0
            then
                redis.call('set', 'capsul:shutting_down', 1)
                return true
            else
                return false
            end
            """
        )

        self._set_job_output_parameters = self.redis.register_script(
            """
            local execution_key = KEYS[1]

            local job_uuid = ARGV[1]
            local output_parameters = cjson.decode(ARGV[2])

            local job_key = 'job:' .. job_uuid
            local values = cjson.decode(redis.call('hget', execution_key, 'workflow_parameters_values'))
            local job = cjson.decode(redis.call('hget', execution_key, job_key))
            local indices = job['parameters_index']
            for name, value in pairs(output_parameters) do
                values[indices[name]+1] = value
            end
            job['output_parameters'] = output_parameters
            redis.call('hset', execution_key, job_key, cjson.encode(job))
            redis.call('hset', execution_key, 'workflow_parameters_values', cjson.encode(values))
        """
        )

        self._kill_jobs = self.redis.register_script(
            """
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local execution_key = KEYS[1]

            local job_ids = cjson.decode(ARGV[1])
            local ongoing = cjson.decode(redis.call('hget', execution_key, 'ongoing'))

            if (next(job_ids) == nil) then
                job_ids = ongoing
            end

            for _, job_uuid in ipairs(job_ids) do
                if table_find(ongoing, job_uuid) then
                    redis.call('hset', execution_key, 'kill_job:' .. job_uuid, 1)
                end
            end
            """
        )

    def _exit(self):
        self.redis.hdel("capsul:connections", self.uuid)
        try:
            self.check_shutdown()
        finally:
            del self.redis

    def get_or_create_engine(self, engine, update_database=False):
        engine_id = self.redis.hget("capsul:engine", engine.label)
        if not engine_id:
            # Create new engine in database
            engine_id = str(uuid4())
            # Engine configuration dictionary
            self.redis.hset(
                f"capsul:{engine_id}", "config", json.dumps(engine.config.json())
            )
            # List of running workers
            self.redis.hset(f"capsul:{engine_id}", "workers", "[]")
            # List of executions_id
            self.redis.hset(f"capsul:{engine_id}", "executions", "[]")
            # Create association between label and engine_id
            self.redis.hset(f"capsul:{engine_id}", "label", engine.label)
            self.redis.hset("capsul:engine", engine.label, engine_id)
            # Store engine persistency
            self.set_persistent(engine_id, engine.config.persistent)
        elif update_database:
            # Update configuration stored in database
            self.redis.hset(
                f"capsul:{engine_id}", "config", json.dumps(engine.config.json())
            )
            self.set_persistent(engine_id, engine.config.persistent)
        self.redis.hincrby(f"capsul:{engine_id}", "connections", 1)
        return engine_id

    def engine_connections(self, engine_id):
        return self.redis.hget(f"capsul:{engine_id}", "connections")

    def engine_config(self, engine_id):
        config = self.redis.hget(f"capsul:{engine_id}", "config")
        if config:
            return json.loads(config)
        raise ValueError(f"Invalid engine_id: {engine_id}")

    def workers_count(self, engine_id):
        workers = json.loads(self.redis.hget(f"capsul:{engine_id}", "workers"))
        return len(workers)

    def worker_database_config(self, engine_id):
        return self.config

    def worker_started(self, engine_id):
        worker_id = str(uuid4())
        keys = [
            f"capsul:{engine_id}",
        ]
        args = [
            worker_id,
        ]
        self._worker_started(keys=keys, args=args)
        return worker_id

    def worker_ended(self, engine_id, worker_id):
        keys = [
            f"capsul:{engine_id}",
        ]
        args = [
            worker_id,
        ]
        self._worker_ended(keys=keys, args=args)

    def persistent(self, engine_id):
        p = self.redis.hget(f"capsul:{engine_id}", "persistent")
        r = bool(int(p))
        return r

    def set_persistent(self, engine_id, persistent):
        self.redis.hset(f"capsul:{engine_id}", "persistent", (1 if persistent else 0))

    def dispose_engine(self, engine_id):
        label = self.redis.hget(f"capsul:{engine_id}", "label")
        if label:
            connections = self.redis.hincrby(f"capsul:{engine_id}", "connections", -1)
            if connections == 0 and not self.persistent(engine_id):
                # Removes association between label and engine_id
                self.redis.hdel("capsul:engine", label)
                self.redis.hdel(f"capsul:{engine_id}", "label")
                # Check if some executions had been submitted or are ongoing
                # An empty list modified with Redis Lua scripts may be encoded as empty dict
                executions = json.loads(
                    self.redis.hget(f"capsul:{engine_id}", "executions")
                )
                if all(
                    not self.redis.hget(f"capsul:{engine_id}:{execution_id}", "dispose")
                    for execution_id in executions
                ):
                    # Nothing is ongoing, completely remove engine
                    self.redis.delete(f"capsul:{engine_id}")

    def executions_summary(self, engine_id):
        result = []
        executions = self.redis.hget(f"capsul:{engine_id}", "executions")
        if executions:
            executions = json.loads(executions)
            for execution_id in executions:
                execution_key = f"capsul:{engine_id}:{execution_id}"
                info = {
                    "label": self.redis.hget(execution_key, "label"),
                    "status": self.status(engine_id, execution_id),
                    "waiting": len(
                        json.loads(self.redis.hget(execution_key, "waiting"))
                    ),
                    "ready": len(json.loads(self.redis.hget(execution_key, "ready"))),
                    "ongoing": len(
                        json.loads(self.redis.hget(execution_key, "ongoing"))
                    ),
                    "done": len(json.loads(self.redis.hget(execution_key, "done"))),
                    "failed": len(json.loads(self.redis.hget(execution_key, "failed"))),
                    "engine_label": self.redis.hget(f"capsul:{engine_id}", "label"),
                    "execution_id": execution_id,
                }
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
        execution_id = str(uuid4())
        keys = [f"capsul:{engine_id}", f"capsul:{engine_id}:{execution_id}"]
        args = [
            execution_id,
            label,
            start_time,
            json.dumps(executable_json),
            json.dumps(execution_context_json),
            json.dumps(workflow_parameters_values_json),
            json.dumps(workflow_parameters_dict_json),
            json.dumps(jobs),
            json.dumps(ready),
            json.dumps(waiting),
        ]
        self._store_execution(keys=keys, args=args)
        return execution_id

    def execution_context_json(self, engine_id, execution_id):
        return json.loads(
            self.redis.hget(f"capsul:{engine_id}:{execution_id}", "execution_context")
        )

    def pop_job_json(self, engine_id, start_time):
        executions = self.redis.hget(f"capsul:{engine_id}", "executions")
        if executions is None:
            # engine_id does not exists anymore
            # return None to say to workers that they can die
            return None, None
        else:
            all_disposed = True
            for execution_id in json.loads(executions):
                all_disposed = all_disposed and self.redis.hget(
                    f"capsul:{engine_id}:{execution_id}", "dispose"
                )
                keys = [f"capsul:{engine_id}:{execution_id}"]
                args = [start_time]
                job_uuid = self._pop_job(keys=keys, args=args)
                if job_uuid:
                    return execution_id, job_uuid
            if all_disposed:
                # No more active execution, worker can die.
                return None, None
            else:
                # Empty string means "no job ready yet"
                return "", ""

    def job_finished_json(
        self, engine_id, execution_id, job_uuid, end_time, return_code, stdout, stderr
    ):
        keys = [f"capsul:{engine_id}", f"capsul:{engine_id}:{execution_id}"]
        args = [execution_id, job_uuid, end_time, return_code, stdout, stderr]
        self._job_finished(keys=keys, args=args)

    def status(self, engine_id, execution_id):
        return self.redis.hget(f"capsul:{engine_id}:{execution_id}", "status")

    def workflow_parameters_values_json(self, engine_id, execution_id):
        return json.loads(
            self.redis.hget(
                f"capsul:{engine_id}:{execution_id}", "workflow_parameters_values"
            )
            or "null"
        )

    def workflow_parameters_dict(self, engine_id, execution_id):
        return json.loads(
            self.redis.hget(
                f"capsul:{engine_id}:{execution_id}", "workflow_parameters_dict"
            )
            or "null"
        )

    def get_job_input_parameters(self, engine_id, execution_id, job_uuid):
        values = self.workflow_parameters_values_json(engine_id, execution_id)
        job = self.job_json(engine_id, execution_id, job_uuid)
        indices = job.get("parameters_index", {})
        result = {}
        for k, i in indices.items():
            if isinstance(i, list):
                result[k] = [values[j] for j in i]
            else:
                result[k] = values[i]
        job["input_parameters"] = result
        self.redis.hset(
            f"capsul:{engine_id}:{execution_id}", f"job:{job_uuid}", json.dumps(job)
        )
        return result

    def set_job_output_parameters(
        self, engine_id, execution_id, job_uuid, output_parameters
    ):
        keys = [f"capsul:{engine_id}:{execution_id}"]
        args = [
            job_uuid,
            json.dumps(output_parameters),
        ]
        self._set_job_output_parameters(keys=keys, args=args)

    def job_json(self, engine_id, execution_id, job_uuid):
        job = json.loads(
            self.redis.hget(f"capsul:{engine_id}:{execution_id}", f"job:{job_uuid}")
        )
        return job

    def kill_jobs(self, engine_id, execution_id, job_ids):
        """Request killing of jobs"""
        # we just set a flag to 1 associated with the jobs to be killed.
        # Workers will poll for it while jobs are running, and react
        # accordingly.
        if not job_ids:
            job_ids = []

        keys = [
            f"capsul:{engine_id}",
        ]
        args = [
            json.encode(job_ids),
        ]
        self._kill_jobs(keys=keys, args=args)

    def job_kill_requested(self, engine_id, execution_id, job_id):
        return self.redis.hget(
            f"capsul:{engine_id}:{execution_id}", f"kill_job:{job_id}"
        )

    def execution_report_json(self, engine_id, execution_id):
        (
            label,
            execution_context,
            status,
            error,
            error_detail,
            start_time,
            end_time,
            waiting,
            ready,
            ongoing,
            done,
            failed,
            jobs,
        ) = self._full_report(keys=[f"capsul:{engine_id}:{execution_id}"])
        parameters_values = self.workflow_parameters_values_json(
            engine_id, execution_id
        )
        result = dict(
            label=label,
            engine_id=engine_id,
            execution_id=execution_id,
            execution_context=json.loads(execution_context),
            status=status,
            error=error,
            error_detail=error_detail,
            start_time=start_time,
            end_time=end_time,
            waiting=waiting,
            ready=ready,
            ongoing=ongoing,
            done=done,
            failed=failed,
            jobs=[json.loads(i) for i in jobs],
            engine_debug={},
        )
        result["temporary_directory"] = self.tmp(engine_id, execution_id)
        result["workflow_parameters"] = parameters_values

        for job in result["jobs"]:
            job["parameters"] = self.job_parameters_from_values(job, parameters_values)

        return result

    def failed_node_paths(self, engine_id, execution_id):
        execution_key = f"capsul:{engine_id}:{execution_id}"
        failed = json.loads(self.redis.hget(execution_key, "failed"))
        for job_uuid in failed:
            job = json.loads(
                self.redis.hget(f"capsul:{engine_id}:{execution_id}", f"job:{job_uuid}")
            )
            parameters_location = job.get("parameters_location")
            if parameters_location:
                result = tuple(i for i in parameters_location if i != "nodes")
                if result != ("directories_creation",):
                    yield result

    def dispose(self, engine_id, execution_id, bypass_persistence=False):
        keys = [f"capsul:{engine_id}", f"capsul:{engine_id}:{execution_id}"]
        args = [execution_id, int(bool(bypass_persistence))]
        self._dispose(keys=keys, args=args)

    def check_shutdown(self):
        try:
            if self._check_shutdown():
                pipeline = self.redis.pipeline()
                pipeline.get("capsul:redis_tmp")
                pipeline.delete("capsul:redis_tmp")
                tmp = pipeline.execute()[0]
                if tmp:
                    pid_file = self.redis.get("capsul:redis_pid_file")
                    self.redis.delete("capsul:redis_pid_file")

                    keys = self.redis.keys("capsul:*")
                    if not keys or keys == ["capsul:shutting_down"]:
                        # Nothing in the database, do not save it
                        save = False
                    else:
                        save = True
                        self.redis.save()

                    # Kill the redis server
                    self.redis.shutdown()

                    # Ensure the pid file is deleted
                    for i in range(20):
                        if not os.path.exists(pid_file):
                            break
                        time.sleep(0.1)

                    shutil.rmtree(tmp)
                    if not save and os.path.exists(self.path):
                        os.remove(self.path)
        except redis.exceptions.ResponseError as e:
            exc = ResponseError(e.args)
            exc.with_traceback(e.__traceback__)
            raise exc from None

    def start_execution(self, engine_id, execution_id, tmp):
        self.redis.hset(f"capsul:{engine_id}:{execution_id}", "tmp", tmp)
        self.redis.hset(f"capsul:{engine_id}:{execution_id}", "status", "running")

    def stop_execution(self, engine_id, execution_id):
        status = self.status(engine_id, execution_id)
        if status == "running":
            self.redis.hset(
                f"capsul:{engine_id}:{execution_id}", "error", "Aborted by user"
            )
            self.redis.hset(
                f"capsul:{engine_id}:{execution_id}", "status", "finalization"
            )

    def end_execution(self, engine_id, execution_id):
        self.redis.hset(f"capsul:{engine_id}:{execution_id}", "status", "ended")
        tmp = self.redis.hget(f"capsul:{engine_id}:{execution_id}", "tmp")
        self.redis.hdel(f"capsul:{engine_id}:{execution_id}", "tmp")
        if (
            self.redis.hget(f"capsul:{engine_id}:{execution_id}", "dispose")
            and not self.persistent
        ):
            executions = json.loads(
                self.redis.hget(f"capsul:{engine_id}", "executions")
            )
            executions.remove(execution_id)
            self.redis.hset(f"capsul:{engine_id}", "executions", json.dumps(executions))
            self.redis.delete(f"capsul:{engine_id}:{execution_id}")
            if not executions and not self.redis.hget(f"capsul:{engine_id}", "label"):
                # Engine is already disopsed: delete it
                self.redis.delete(f"capsul:{engine_id}")
        return tmp

    def tmp(self, engine_id, execution_id):
        return self.redis.hget(f"capsul:{engine_id}:{execution_id}", "tmp")

    def error(self, engine_id, execution_id):
        return self.redis.hget(f"capsul:{engine_id}:{execution_id}", "error")
