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
    def __init__(self, url):
        super().__init__(url)
        self.uuid = str(uuid4())
        if url.scheme == 'redis+socket':
            self.redis_socket = f'{url.netloc}{url.path}'
            if not os.path.exists(self.redis_socket):
                # Start the redis server
                tmp = tempfile.mkdtemp(prefix='capsul_redis_')
                try:
                    pid_file = f'{tmp}/redis.pid'
                    cmd = [
                        'redis-server',
                        '--unixsocket', self.redis_socket,
                        '--port', '0', # port 0 means no TCP connection
                        '--daemonize', 'yes',
                        '--pidfile', pid_file,
                        '--dir', tmp,
                        '--dbfilename', 'redis.rdb',
                    ]
                    subprocess.run(cmd)
                    for i in range(20):
                        if os.path.exists(self.redis_socket):
                            break
                        time.sleep(0.1)
                    self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                              decode_responses=True)
                    self.redis.set('capsul_tmp', tmp)
                    self.redis.set('capsul_redis_pid_file', pid_file)
                except Exception:
                    shutil.rmtree(tmp)
            else:
                self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                           decode_responses=True)
            self.redis.hset('capsul_connections', self.uuid, datetime.now().isoformat())

            # Som functions are implemented as a Lua script in redis
            # in order to be atomic.
            self._start_next_job = self.redis.register_script('''
                local function key(name)
                    return 'capsul:' .. ARGV[1] .. ':' .. name
                end

                print('!redis:start_next_job!')
                local job_uuid = redis.call('lpop', key('ready'))
                if job_uuid then
                    redis.call('set', key('status'), 'running')
                    local job = cjson.decode(redis.call('hget', key('jobs'), job_uuid))
                    job['start_time'] = ARGV[2]
                    job = cjson.encode(job)
                    redis.call('hset', key('jobs'), job_uuid, job)
                    redis.call('rpush', key('ongoing'), job_uuid)
                    return job
                end
                return nil
            ''')
            self._job_finished = self.redis.register_script('''
                local function key(name)
                    return 'capsul:' .. ARGV[1] .. ':' .. name
                end

                local job_uuid = ARGV[2]
                local end_time = ARGV[3]
                local returncode = ARGV[4]
                local stdout = ARGV[5]
                local stderr = ARGV[6]

                local job = cjson.decode(redis.call('hget', key('jobs'), job_uuid))
                job['end_time'] = end_time
                job['returncode'] = returncode
                job['stdout'] = stdout
                job['stderr'] = stderr
                redis.call('hset', key('jobs'), job_uuid, cjson.encode(job))

                redis.call('lrem', key('ongoing'), 1, job_uuid)

                if returncode ~= '0' then
                    redis.call('rpush', key('failed'), job_uuid)
                    local stack = {}
                    if job['waited_by'] then
                        for key, value in pairs(job['waited_by']) do
                            stack[key] = value
                        end
                    end

                    local uuid = table.remove(stack)
                    while uuid do
                        job = cjson.decode(redis.call('hget', key('jobs'), uuid))
                        job['returncode'] = 'Not started because de dependent job failed'
                        redis.call('hset', key('jobs'), uuid, cjson.encode(job))
                        redis.call('lrem', key('waiting'), 1, uuid)
                        redis.call('rpush', key('failed'), uuid)
                        if job['waited_by'] then
                            for key, value in ipairs(job['waited_by']) do
                                table.insert(stack, value)
                            end
                        end
                        uuid = table.remove(stack)
                    end
                else
                    redis.call('rpush', key('done'), job_uuid)
                    if job['waited_by'] then
                        for _, waiting_uuid in ipairs(job['waited_by']) do
                            local waiting_job = cjson.decode(redis.call('hget', key('jobs'), waiting_uuid))
                            local ready_to_go = true
                            if waiting_job['wait_for'] then
                                for key2, waited in ipairs(waiting_job['wait_for']) do
                                    if not redis.call('lpos', key('done'), waited) then
                                        ready_to_go = false
                                        break
                                    end
                                end
                            end
                            if ready_to_go then
                            redis.call('lrem', key('waiting'), 1, waiting_uuid)
                                redis.call('rpush', key('ready'), waiting_uuid)
                            end
                        end
                    end
                end

                if (redis.call('llen', key('ongoing')) ~= 0) or (redis.call('llen', key('ready')) ~= 0) then
                    return false
                else
                    if redis.call('llen', key('failed')) ~= 0 then
                        redis.call('set', key('error'), 'Some jobs failed')
                    end
                    redis.call('set', key('status'), 'ended')
                    redis.call('set', key('end_time'), end_time)
                    return true
                end
            ''')

            self._full_report = self.redis.register_script('''
                local function key(name)
                    return 'capsul:' .. ARGV[1] .. ':' .. name
                end

                local executable = redis.call('get', key('executable'))
                local execution_context = redis.call('get', key('execution_context'))
                local workflow_parameters = redis.call('get', key('workflow_parameters'))
                local status = redis.call('get', key('status'))
                local error = redis.call('get', key('error'))
                local error_detail = redis.call('get', key('error_detail'))
                local start_time = redis.call('get', key('start_time'))
                local end_time = redis.call('get', key('end_time'))
                local waiting = redis.call('lrange', key('waiting'), 0, -1)
                local ready = redis.call('lrange', key('ready'), 0, -1)
                local ongoing = redis.call('lrange', key('ongoing'), 0, -1)
                local done = redis.call('lrange', key('done'), 0, -1)
                local failed = redis.call('lrange', key('failed'), 0, -1)
                local jobs = {}
                for i, v in ipairs(redis.call('hgetall', key('jobs'))) do
            		if i % 2 == 0 then
            			table.insert(jobs, v)
                    end
        		end
                return {executable, execution_context, workflow_parameters, 
                    status, error, error_detail, start_time, end_time, 
                    waiting, ready, ongoing, done, failed, jobs}                
                ''')
            self._dispose = self.redis.register_script('''
                local function key(name)
                    return 'capsul:' .. ARGV[1] .. ':' .. name
                end

                if redis.call('get', key('status')) == 'ended' then
                    redis.call('del', key('executable'))
                    redis.call('del', key('execution_context'))
                    redis.call('del', key('status'))
                    redis.call('del', key('error'))
                    redis.call('del', key('error_detail'))
                    redis.call('del', key('start_time'))
                    redis.call('del', key('end_time'))
                    redis.call('del', key('waiting'))
                    redis.call('del', key('ready'))
                    redis.call('del', key('ongoing'))
                    redis.call('del', key('done'))
                    redis.call('del', key('failed'))
                    redis.call('del', key('jobs'))
                    redis.call('del', key('workflow_parameters'))
                    redis.call('del', key('dispose'))
                else
                    redis.call('set', key('dispose'), 1)
                end
                ''')
        else:
            raise NotImplementedError(f'Redis connection with {self.url} is not implemented')
        
    def close(self):
        pipe = self.redis.pipeline()
        pipe.hdel('capsul_connections', self.uuid)
        pipe.hlen('capsul_connections')
        connections_count = pipe.execute()[-1]
        if connections_count == 0:
            tmp = self.redis.get('capsul_tmp')
            pid_file = self.redis.get('capsul_redis_pid_file')
            
            # Kill the redis server
            self.redis.shutdown()

            # Ensure the pid file is deleted
            for i in range(20):
                if not os.path.exists(pid_file):
                    break
                time.sleep(0.1)

            shutil.rmtree(tmp)

    @property
    def capsul_tmp(self):
        return self.redis.get('capsul_tmp')
    
    def key(self, execution_id, name):
        return f'capsul:{execution_id}:{name}'

    def get(self, execution_id, name):
        return self.redis.get(self.key(execution_id, name))
    
    def set(self, execution_id, name, value):
        self.redis.set(self.key(execution_id, name), value)

    def pipeline(self, execution_id):
        return RedisExecutionPipeline(self.redis.pipeline(), execution_id)

    def store_execution(self,
            start_time, 
            executable_json,
            execution_context_json,
            workflow_parameters_json,
            jobs,
            ready,
            waiting
        ):
        execution_id = str(uuid4())
        pipe = self.pipeline(execution_id)
        pipe.rpush('capsul_execution_ids', execution_id)
        pipe.set( 'status', ('ready' if ready else 'ended'))
        pipe.set('start_time', start_time)
        pipe.set('executable', json.dumps(executable_json))
        pipe.set('execution_context', json.dumps(execution_context_json))
        pipe.set('workflow_parameters', json.dumps(workflow_parameters_json))
        pipe.set_list('ready', ready)
        pipe.set_list('waiting', waiting)
        pipe.delete('ongoing')
        pipe.delete('done')
        pipe.delete('failed')
        pipe.set('dispose', 0)
        if not ready:
            pipe.set('end_time', start_time)
        for job in jobs:
            pipe.hset('jobs', job['uuid'], json.dumps(job))
        pipe.execute()
        return execution_id
    
    def status(self, execution_id):
        return self.get(execution_id, 'status')

    def error(self, execution_id):
        return self.get(execution_id, 'error')

    def error_detail(self, execution_id):
        return self.get(execution_id, 'error_detail')

    def set_error(self, execution_id, error, error_detail=None):
        pipe = self.pipeline(execution_id)
        pipe.set( 'error', error)
        pipe.set( 'error_detail', error_detail)
        pipe.execute()
    
    def execution_context_json(self, execution_id):
        return json.loads(self.get(execution_id, 'execution_context'))

    def executable_json(self, execution_id):
        return json.loads(self.get(execution_id, 'executable'))
    
    def workflow_parameters_json(self, execution_id):
        return json.loads(self.get(execution_id, 'workflow_parameters'))

    def set_workflow_parameters_json(self, execution_id, workflow_parameters_json):
        self.set(execution_id, 'workflow_parameters', json.dumps(workflow_parameters_json))

    def start_time_json(self, execution_id):
        return self.get(execution_id, 'start_time')

    def end_time_json(self, execution_id):
        return self.get(execution_id, 'end_time')

    def jobs_json(self, execution_id):
        jobs_key = self.key(execution_id, 'jobs')
        for job_uuid in self.redis.hkeys(jobs_key):
            yield json.loads(self.redis.hget(jobs_key, job_uuid))


    def job_json(self, execution_id, job_uuid):
        job = json.loads(self.redis.hget(self.key(execution_id, 'jobs'), job_uuid))
        return job

    def ready(self ,execution_id):
        return self.get_list(execution_id, 'ready')

    def waiting(self ,execution_id):
        return self.get_list(execution_id, 'waiting')

    def ongoing(self ,execution_id):
        return self.get_list(execution_id, 'ongoing')

    def done(self ,execution_id):
        return self.get_list(execution_id, 'done')

    def failed(self ,execution_id):
        return self.get_list(execution_id, 'failed')
   
    def start_next_job_json(self, execution_id, start_time):
        next_job = self._start_next_job(args=[execution_id, start_time])
        if next_job is not None:
            next_job = json.loads(next_job)
        return next_job
    
    def job_finished_json(self, execution_id, job_uuid, end_time, returncode, stdout, stderr):
        return self._job_finished(args=[execution_id, job_uuid, end_time, returncode, stdout, stderr])

    def execution_report_json(self, execution_id):
        (executable, execution_context, workflow_parameters, status, error,
         error_detail, start_time, end_time, waiting, ready,
         ongoing, done, failed, jobs) = self._full_report(args=[execution_id])
        result = dict(
            executable=json.loads(executable),
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
        
    def dispose(self, execution_id):
        self._dispose(args=[execution_id])

    
