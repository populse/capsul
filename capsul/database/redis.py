# -*- coding: utf-8 -*-
from datetime import datetime
import shutil
import tempfile
import json
import os
import subprocess
import time
from uuid import uuid4

import redis

from . import ExecutionDatabase


class RedisExecutionPipeline:
    def __init__(self, pipeline, execution_id):
        self.pipeline = pipeline
        self.execution_id = execution_id

    def key(self, name):
        return f'capsul:{self.execution_id}:{name}'
    
    def get(self, name):
        return self.pipeline.get(self.key(name))

    def set(self, name, value):
        self.pipeline.set(self.key(name), value)

    def set_list(self, name, values):
        key = self.key(name)
        self.pipeline.delete(key)
        if values:
            self.pipeline.rpush(key, *values)

    def hset(self, name, item, value):
        self.pipeline.hset(self.key(name), item, value)

    def rpush(self, name, value):
        self.pipeline.rpush(self.key(name), value)

    def delete(self, name):
        self.pipeline.delete(self.key(name))

    def execute(self):
        return self.pipeline.execute()

class RedisExecutionDatabase(ExecutionDatabase):
    def __enter__(self):
        self.uuid = str(uuid4())

        if self.config['type'] == 'redis+socket':
            if not self.path:
                raise ValueError('Database path is missing in configuration')
            self.redis_socket = f'{self.path}.socket'
            if not os.path.exists(self.redis_socket):
                # Start the redis server
                tmp = tempfile.mkdtemp(prefix='capsul_redis_')
                try:
                    dir, dbfilename = os.path.split(self.path)
                    pid_file = f'{tmp}/redis.pid'
                    log_file = f'{tmp}/redis.log'
                    cmd = [
                        'redis-server',
                        '--unixsocket', self.redis_socket,
                        '--port', '0', # port 0 means no TCP connection
                        '--daemonize', 'yes',
                        '--pidfile', pid_file,
                        '--dir', dir,
                        '--logfile', log_file,
                        '--dbfilename', dbfilename,
                    ]
                    subprocess.run(cmd, cwd=tmp)
                    for i in range(20):
                        if os.path.exists(self.redis_socket):
                            break
                        time.sleep(0.1)
                    self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                                decode_responses=True)
                    self.redis.delete('capsul:connections') 
                    self.redis.set('capsul:redis_tmp', tmp)
                    self.redis.set('capsul:redis_pid_file', pid_file)
                except Exception:
                    shutil.rmtree(tmp)
            else:
                self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                          decode_responses=True)
        elif self.config['type'] == 'redis':
            self.redis  = redis.Redis(host=self.config['host'], port=self.config.get('port'),
                                      decode_responses=True)
            if self.config.get('login'):
                self.redis.auth(self.config['password'], self.config['login'])
        else:
            raise NotImplementedError(f'Invalid Redis connection type: {self.config["type"]}')
        self.redis.hset('capsul:connections', self.uuid, datetime.now().isoformat())

        # Some functions are implemented as a Lua script in redis
        # in order to be atomic. In redis these scripts must always
        # be registered before using them.
        self._store_execution = self.redis.register_script('''
            local engine_key = KEYS[1]
            local execution_key = KEYS[2]

            local execution_id = ARGV[1]
            local label = ARGV[2]
            local start_time = ARGV[3]
            local executable_json = ARGV[4]
            local execution_context_json = ARGV[5]
            local workflow_parameters_json = ARGV[6]
            local jobs = cjson.decode(ARGV[7])
            local ready = ARGV[8]
            local waiting = ARGV[9]

            local executions = cjson.decode(redis.call('hget', engine_key, 'executions'))
            table.insert(executions, execution_id)
            redis.call('hset', engine_key, 'executions', cjson.encode(executions))

            redis.call('hset', execution_key, 'label', label)
            redis.call('hset', execution_key, 'status', 'ready')
            redis.call('hset', execution_key, 'start_time', start_time)
            redis.call('hset', execution_key, 'executable', executable_json)
            redis.call('hset', execution_key, 'execution_context', execution_context_json)
            redis.call('hset', execution_key, 'workflow_parameters', workflow_parameters_json)

            redis.call('hset', execution_key, 'ready', ready)
            if ready  == '[]' then
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
            ''')

        self._pop_job = self.redis.register_script('''
            local execution_key = KEYS[1]

            local start_time = ARGV[2]

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
                    job['start_time'] = ARGV[2]
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
        ''')

        self._job_finished = self.redis.register_script('''
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
            local returncode = ARGV[4]
            local stdout = ARGV[5]
            local stderr = ARGV[6]

            local job_key = 'job:' .. job_uuid
            local job = cjson.decode(redis.call('hget', execution_key, job_key))
            job['end_time'] = end_time
            job['returncode'] = returncode
            job['stdout'] = stdout
            job['stderr'] = stderr
            redis.call('hset', execution_key, job_key, cjson.encode(job))

            local ready = cjson.decode(redis.call('hget', execution_key, 'ready'))
            local ongoing = cjson.decode(redis.call('hget', execution_key, 'ongoing'))
            local failed = cjson.decode(redis.call('hget', execution_key, 'failed'))
            local waiting = cjson.decode(redis.call('hget', execution_key, 'waiting'))
            local done = cjson.decode(redis.call('hget', execution_key, 'done'))


            table.remove(ongoing, table_find(ongoing, job_uuid))

            if returncode ~= '0' then
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
                    job['returncode'] = 'Not started because de dependent job failed'
                    redis.call('hset', execution_key, job_key, cjson.encode(job))

                    table.remove(waiting, table_find(waiting, uuid))
                    table.insert(failed, uuid)
                    if job['waited_by'] then
                        for key, value in ipairs(job['waited_by']) do
                            table.insert(stack, value)
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
        ''')

        self._update_workflow_parameters = self.redis.register_script('''
            local execution_key = KEYS[1]

            local parameters_location = cjson.decode(ARGV[1])
            local output_parameters = cjson.decode(ARGV[2])
            local workflow_parameters = cjson.decode(redis.call('hget', execution_key, 'workflow_parameters'))

            local parameters = workflow_parameters['content']
            for index, value in ipairs(parameters_location) do
                local i = tonumber(value)
                if i then
                    parameters = parameters[i+1]
                else
                    parameters = parameters[value]
                end
            end

            for k, v in pairs(output_parameters) do
                workflow_parameters['proxy_values'][parameters[k][2]+1] = v
            end
            redis.call('hset', execution_key, 'workflow_parameters', cjson.encode(workflow_parameters))
            ''')


        self._dispose = self.redis.register_script('''
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

            redis.call('hset', execution_key, 'dispose', 1)
            if redis.call('hget', execution_key, 'status') == 'ended' then
                redis.call('del', execution_key)
                local executions = cjson.decode(redis.call('hget', engine_key, 'executions'))
                table.remove(executions, table_find(executions, execution_id))
                redis.call('hset', engine_key, 'executions', cjson.encode(executions))
            end
            ''')

        self._worker_started = self.redis.register_script('''
            local function table_find(array, value)
                for i, v in pairs(array) do
                    if v == value then
                        return i
                    end
                end
            end

            local engine_key = KEYS[1]

            local worker_id = ARGV[1]

            local workers = cjson.decode(redis.call('hget', engine_key, 'workers'))
            table.insert(workers, worker_id)
            redis.call('hset', engine_key, 'workers', cjson.encode(workers))
        ''')

        self._worker_ended = self.redis.register_script('''
            local engine_key = KEYS[1]

            local worker_id = ARGV[1]

            local workers = cjson.decode(redis.call('hget', engine_key, 'workers'))
            table.remove(workers, table_find(workers, worker_id))
            redis.call('hset', engine_key, 'workers', cjson.encode(workers))
        ''')


        self._full_report = self.redis.register_script('''
            local execution_key = KEYS[1]

            local label = redis.call('hget', execution_key, 'label')
            local execution_context = redis.call('hget', execution_key, 'execution_context')
            local workflow_parameters = redis.call('hget', execution_key, 'workflow_parameters')
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

            return {label, execution_context, workflow_parameters, 
                status, error, error_detail, start_time, end_time, 
                waiting, ready, ongoing, done, failed, jobs}                
            ''')


        self._check_shutdown = self.redis.register_script('''
            if redis.call('get', 'capsul:redis_pid_file') and
               redis.call('hlen', 'capsul:connections') == 0
            then
                -- setting capsul_connection to a string value will prevent
                -- the creation of new connections because they will use
                -- hset command that raises an error value type is not a hash
                redis.call('set', 'capsul:connections', 'shutting down')
                return true
            else
                return false
            end
            ''')

        return self
    

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.redis.hdel('capsul:connections', self.uuid)
        self.check_shutdown()
        del self.redis
   

    def connect_to_engine(self, engine):
        engine_id = self.redis.hget('capsul:engine', engine.label)
        if not engine_id:
            # Create new engine in database
            engine_id = str(uuid4())
            # Engine configuration dictionary
            self.redis.hset(f'capsul:{engine_id}', 'config', json.dumps(engine.config.json()))
            # List of running workers
            self.redis.hset(f'capsul:{engine_id}', 'workers', '[]')
            # List of executions_id
            self.redis.hset(f'capsul:{engine_id}', 'executions', '[]')
            # Create association between label and engine_id
            self.redis.hset(f'capsul:{engine_id}', 'label', engine.label)
            self.redis.hset('capsul:engine', engine.label, engine_id)
        return engine_id
    

    def engine_config(self, engine_id):
        config = self.redis.hget(f'capsul:{engine_id}', 'config')
        if config:
            return json.loads(config)
        raise ValueError(f'Invalid engine_id: {engine_id}')


    def number_of_workers_to_start(self, engine_id):
        config = self.engine_config(engine_id)
        workers = json.loads(self.redis.hget(f'capsul:{engine_id}', 'workers'))
        requested = config.get('start_workers', {}).get('count', 0)
        return max(0, requested - len(workers))


    def worker_database_config(self, engine_id):
        return self.config


    def worker_started(self, engine_id):
        worker_id = str(uuid4())
        keys = [
            f'capsul:{engine_id}',
        ]
        args = [
            worker_id,
        ]
        self._worker_started(keys=keys, args=args)
        return worker_id


    def worker_ended(self, engine_id, worker_id):
        keys = [
            f'capsul:{engine_id}',
        ]
        args = [
            worker_id,
        ]
        self._worker_ended(keys=keys, args=args)


    def dispose_engine(self, engine_id):
        label = self.redis.hget(f'capsul:{engine_id}', 'label')
        if label:
            # Removes association between label and engine_id
            self.redis.hdel('capsul:engine', label)
            self.redis.hdel(f'capsul:{engine_id}', 'label')
            # Check if some executions had been submited or are ongoing
            if (self.redis.hget(f'capsul:{engine_id}', 'ready') == '[]' and
                self.redis.hget(f'capsul:{engine_id}', 'ongoing') == '[]'):
                # Nothing is ongoing, completely remove engine
                for i in ('config', 'workers', 'ready', 'ongoing', 'ended'):
                    self.redis.hdel(f'capsul:{engine_id}', i)


    def store_execution(self,
            engine_id,
            label,
            start_time, 
            executable_json,
            execution_context_json,
            workflow_parameters_json,
            jobs,
            ready,
            waiting
        ):
        execution_id = str(uuid4())
        keys = [
            f'capsul:{engine_id}',
            f'capsul:{engine_id}:{execution_id}'
        ]
        args = [
            execution_id,
            label,
            start_time,
            json.dumps(executable_json),
            json.dumps(execution_context_json),
            json.dumps(workflow_parameters_json),
            json.dumps(jobs),
            json.dumps(ready),
            json.dumps(waiting),
        ]
        self._store_execution(keys=keys, args=args)
        return execution_id


    def execution_context_json(self, engine_id, execution_id):
        return json.loads(self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'execution_context'))


    def pop_job_json(self, engine_id, start_time):
        executions = self.redis.hget(f'capsul:{engine_id}','executions')
        if executions is None:
            # engine_id does not exists anymore
            # return None to say to workers that they can die
            return None, None
        else:
            for execution_id in json.loads(self.redis.hget(f'capsul:{engine_id}',
                                                           'executions')):
                keys = [
                    f'capsul:{engine_id}:{execution_id}'
                ]
                args=[start_time]
                job_uuid = self._pop_job(keys=keys, args=args)
                if job_uuid:
                    return execution_id, job_uuid
            # Empty string means "no job ready yet"
            return '', ''

    def job_finished_json(self, engine_id, execution_id, job_uuid, 
                          end_time, returncode, stdout, stderr):
        keys = [
            f'capsul:{engine_id}',
            f'capsul:{engine_id}:{execution_id}'
        ]
        args = [
            execution_id, 
            job_uuid, 
            end_time, 
            returncode, 
            stdout, 
            stderr
        ]
        self._job_finished(keys=keys, args=args)
    
    def status(self, engine_id, execution_id):
        return self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'status')

        
    def workflow_parameters_json(self, engine_id, execution_id):
        return json.loads(self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'workflow_parameters') or 'null')


    def set_workflow_parameters_json(self, engine_id, execution_id, workflow_parameters_json):
        self.redis.hset(f'capsul:{engine_id}:{execution_id}', 'workflow_parameters',
                        json.dumps(workflow_parameters_json))


    def update_workflow_parameters_json(self, engine_id, execution_id, parameters_location, output_values):
        keys = [
            f'capsul:{engine_id}:{execution_id}'
        ]
        args = [
            json.dumps(parameters_location),
            json.dumps(output_values)
        ]
        self._update_workflow_parameters(keys=keys, args=args)


    def job_json(self, engine_id, execution_id, job_uuid):
        job = json.loads(self.redis.hget(f'capsul:{engine_id}:{execution_id}', f'job:{job_uuid}'))
        return job


    def execution_report_json(self, engine_id, execution_id):
        (label, execution_context, workflow_parameters, status, error,
         error_detail, start_time, end_time, waiting, ready,
         ongoing, done, failed, jobs) = self._full_report(keys=[f'capsul:{engine_id}:{execution_id}'])
        result = dict(
            label=label,
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
            workflow_parameters =json.loads(workflow_parameters),
            engine_debug = {},
        )
        return result
    

    def dispose(self, engine_id, execution_id):
        keys = [
            f'capsul:{engine_id}',
            f'capsul:{engine_id}:{execution_id}'
        ]
        args = [
            execution_id,
        ]
        self._dispose(keys=keys, args=args)


    def check_shutdown(self):
        if self._check_shutdown():
            pipeline = self.redis.pipeline()
            pipeline.get('capsul:redis_tmp')
            pipeline.delete('capsul:redis_tmp')
            tmp = pipeline.execute()[0]
            pid_file = self.redis.get('capsul:redis_pid_file')
            
            # Kill the redis server
            self.redis.save()
            self.redis.shutdown()

            # Ensure the pid file is deleted
            for i in range(20):
                if not os.path.exists(pid_file):
                    break
                time.sleep(0.1)

            shutil.rmtree(tmp)

    
    def start_execution(self, engine_id, execution_id, tmp):
        self.redis.hset(f'capsul:{engine_id}:{execution_id}', 'tmp', tmp)
        self.redis.hset(f'capsul:{engine_id}:{execution_id}', 'status', 'running')


    def end_execution(self, engine_id, execution_id):
        self.redis.hset(f'capsul:{engine_id}:{execution_id}', 'status', 'ended')
        tmp = self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'tmp')
        self.redis.hdel(f'capsul:{engine_id}:{execution_id}', 'tmp')
        if self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'dispose'):
            executions = json.loads(self.redis.hget(f'capsul:{engine_id}', 'executions'))
            executions.remove(executions, execution_id)
            self.redis.hset(f'capsul:{engine_id}', 'executions', json.dumps(executions))
            self.redis.delete(f'capsul:{engine_id}:{execution_id}')
        return tmp


    def tmp(self, engine_id, execution_id):
        return self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'tmp')


    def error(self, engine_id, execution_id):
        return self.redis.hget(f'capsul:{engine_id}:{execution_id}', 'error')

    
