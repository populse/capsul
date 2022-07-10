# -*- coding: utf-8 -*-
import datetime
import shutil
import tempfile
import dateutil
import dateutil.parser
import json
import os
import signal
import subprocess
import time

import redis

from soma.api import DictWithProxy
from populse_db.database import json_encode, json_decode, json_dumps


from . import ExecutionDatabase
from ..application import Capsul
from ..execution_context import ExecutionContext

# def json_dumps(value):
#     return json.dumps(value, separators=(',', ':'))

# _json_encodings = {
#     datetime.datetime: lambda d: f'{d.isoformat()}ℹdatetimeℹ',
#     datetime.date: lambda d: f'{d.isoformat()}ℹdateℹ',
#     datetime.time: lambda d: f'{d.isoformat()}ℹtimeℹ',
#     list: lambda l: [json_encode(i) for i in l],
#     dict: lambda d: dict((k, json_encode(v)) for k, v in d.items()),
# }

# _json_decodings = {
#     'datetime': lambda s: dateutil.parser.parse(s),
#     'date': lambda s: dateutil.parser.parse(s).date(),
#     'time': lambda s: dateutil.parser.parse(s).time(),
# }

# def json_encode(value):
#     global _json_encodings

#     type_ = type(value)
#     encode = _json_encodings.get(type_)
#     if encode is not None:
#         return encode(value)
#     return value

# def json_decode(value):
#     global _json_decodings

#     if isinstance(value, list):
#         return [json_decode(i) for i in value]
#     elif isinstance(value, dict):
#         return dict((k, json_decode(v)) for k, v in value.items())
#     elif isinstance(value, str):
#         if value.endswith('ℹ'):
#             l = value[:-1].rsplit('ℹ', 1)
#             if len(l) == 2:
#                 encoded_value, decoding_name = l
#                 decode = _json_decodings.get(decoding_name)
#                 if decode is None:
#                     raise ValueError(f'Invalid JSON encoding type for value "{value}"')
#                 return decode(encoded_value)
#     return value


class RedisExecutionPipeline:
    def __init__(self, pipeline, execution_id):
        self.pipeline = pipeline
        self.execution_id = execution_id

    def key(self, name):
        return f'capsul:{self.execution_id}:{name}'
    
    def get(self, name):
        return self.pipeline.get(self.key(name))

    def set(self, name, item, value):
        self.pipeline.set(self.key(name), value)

    def set_list(self, name, values):
        key = self.key(name)
        self.pipeline.delete(key)
        self.pipeline.rpush(key, values)

    def hset(self, name, item, value):
        self.pipeline.hset(self.key(name), item, value)

    def execute(self):
        return self.pipeline.execute()

class RedisExecutionDatabase(ExecutionDatabase):
    def __init__(self, url):
        super().__init__(url)
        if url.scheme == 'redis+socket':
            self.redis_socket = f'{url.netloc}{url.path}'
            if not os.path.exists(socket):
                # Start the redis server
                directory = tempfile.mkdtemp(prefix='capsul_redis_')
                try:
                    pid_file = f'{directory}/redis.pid'
                    cmd = [
                        'redis-server',
                        '--unixsocket', self.redis_socket,
                        '--port', '0', # port 0 means no TCP connection
                        '--daemonize', 'yes',
                        '--pidfile', pid_file,
                        '--dir', directory,
                        '--dbfilename', 'redis.rdb',
                    ]
                    subprocess.run(cmd)
                    for i in range(20):
                        if os.path.exists(self.redis_socket):
                            break
                        time.sleep(0.1)
                    self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                              decode_responses=True)
                    self.redis.set('capsul_directory', directory)
                    self.redis.set('capsul_redis_pid_file', pid_file)
                    self.redis.set('capsul_connection_count', 1)
                except Exception:
                    shutil.rmtree(directory)
            else:
                self.redis  = redis.Redis(unix_socket_path=self.redis_socket,
                                           decode_responses=True)
                self.redis.incr('capsul_connection_count')

        else:
            raise NotImplemented(f'Redis connection with {self.url} is not implemented')
        
    def close(self):
        connection_count = self.redis.decr('capsul_connection_count')
        if connection_count == 0:
            directory = self.redis.get('capsul_directory')
            pid_file = self.redis.get('capsul_redis_pid_file')
            
            # Kill the redis server
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)

            # Ensure the pid file is deleted
            for i in range(20):
                if not os.path.exists(pid_file):
                    break
                time.sleep(0.1)

            shutil.rmtree(directory)

    def key(self, name):
        return f'capsul:{self.execution_id}:{name}'

    def get(self, execution_id, name):
        return self.redis.get(self.key(execution_id, name))
    
    def set(self, execution_id, name, value):
        self.redis.set(self.key(execution_id, name), value)

    def pipeline(self, execution_id):
        return RedisExecutionPipeline(self.redis.pipeline(), execution_id)


    def job_key(self, execution_id, job_uuid):
        return f'capsul:{execution_id}:{name}'

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
        pipe.set( 'status', ('ready' if ready else 'ended'))
        pipe.set('start_time', start_time.isoformat())
        pipe.set('executable', json.dumps(executable_json))
        pipe.set('execution_context', json.dumps(execution_context_json))
        pipe.set('workflow_parameters', json.dumps(workflow_parameters_json))
        pipe.set_list('ready', ready)
        pipe.set_list('waiting', waiting)
        pipe.delete('ongoing')
        pipe.delete('done')
        pipe.delete('failed')
        if not ready:
            pipe.set('end_time', start_time.isoformat())
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
        self.set(execution_id, 'workflow_parameters', workflow_parameters_json)

    def start_time(self, execution_id):
        return dateutil.parser.parse(self.get(execution_id, 'start_time'))

    def end_time(self, execution_id):
        return dateutil.parser.parse(self.get(execution_id, 'end_time'))

    def jobs(self, execution_id):
        jobs_key = self.key(execution_id, 'jobs')
        for job_uuid in self.redis.hkeys(jobs_key):
            yield json.loads(self.redis.hget(jobs_key, job_uuid))


    def job(self, execution_id, job_uuid):
        return json.loads(self.redis.hget(self.key(execution_id, 'jobs'), job_uuid))

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
   
    def start_next_job(self, execution_id, start_time):
        with self.database as session:
            execution= {}
            executions = session['execution']
            ready, ongoing = executions.document(
                execution_id,
                fields=('ready', 'ongoing'),
                as_list=True)
            if ready:
                execution['status'] = 'running'
                job_uuid = ready.pop(0)
                execution['ready'] = ready
                job = session['job'][(execution_id, job_uuid)]
                job['start_time'] = start_time
                session['job'][(execution_id, job_uuid)] = job
                ongoing.append(job_uuid)
                execution['ongoing'] = ongoing
                result = job
            else:
                result = None
            executions.update_document(execution_id, execution)
            return result
    
    def job_finished(self, execution_id, job_uuid, end_time, returncode, stdout, stderr):
        with self.database as session:
            session['job'].update_document(
                (execution_id, job_uuid),
                {
                    'end_time': end_time,
                    'returncode': returncode,
                    'stdout': stdout,
                    'stderr': stderr,
                })
            execution = session['execution'].document(
                execution_id, fields=('ready', 'ongoing', 'waiting', 'failed', 'done')
            )
            execution['ongoing'].remove(job_uuid)

            job = session['job'][(execution_id, job_uuid)]
            if returncode:
                execution['failed'].append(job_uuid)
                stack = list(job.get('waited_by', []))
                while stack:
                    uuid = stack.pop(0)
                    job = session['job'][(execution_id, uuid)]
                    job['returncode'] = 'Not started because de dependent job failed'
                    session['job'][(execution_id, uuid)] = job
                    execution['waiting'].remove(uuid)
                    execution['failed'].append(uuid)
                    stack.extend(job.get('waited_by', []))
            else:
                execution['done'].append(job_uuid)
                done = set(execution['done'])
                for waiting_uuid in job.get('waited_by', []):
                    waiting_job = self.job(execution_id, waiting_uuid)
                    for waited in waiting_job.get('wait_for', []):
                        if waited not in done:
                            break
                    else:
                        execution['waiting'].remove(waiting_uuid)
                        execution['ready'].append(waiting_uuid)
            if execution['ongoing'] or execution['ready']:
                result = False
            else:
                if execution['failed']:
                    execution['status'] = 'error'
                    execution['error'] = 'Some jobs failed'
                else:
                    execution['status'] = 'ended'
                execution['end_time'] = end_time
                result = True
            session['execution'].update_document(execution_id, execution)
            return result

    def full_report(self, execution_id):
        with self.database as session:
            jobs = []
            result = dict(
                executable = self.executable(execution_id),
                execution_context = self.execution_context(execution_id),
                status = self.status(execution_id),
                error = self.error(execution_id),
                error_detail = self.error_detail(execution_id),
                start_time = self.start_time(execution_id),
                end_time = self.end_time(execution_id),
                waiting = self.waiting(execution_id),
                ready = self.ready(execution_id),
                ongoing = self.ongoing(execution_id),
                done = self.done(execution_id),
                failed = self.failed(execution_id),
                jobs = jobs,
                workflow_parameters = self.workflow_parameters(execution_id),
            )
            for job in self.jobs(execution_id):
                job_uuid = job['uuid']
                if job_uuid in result['done']:
                    job['status'] = 'done'
                elif job_uuid in result['failed']:
                    job['status'] = 'failed'
                elif job_uuid in result['ongoing']:
                    job['status'] = 'ongoing'
                elif job_uuid in result['ready']:
                    job['status'] = 'ready'
                elif job_uuid in result['waiting']:
                    job['status'] = 'waiting'
                else:
                    job['status'] = 'unknown'
                jobs.append(job)
        return result
        
    def dispose(self, execution_id):
        with self.database as session:
            if self.status(execution_id) == 'ended':
                session['job'].delete(f'{{execution_id}}=="{execution_id}"')
                del session['execution'][execution_id]
    
    def debug_info(self, execution_id):
        return {}


# class RedisExecutionDatabase:
#     def __init__(self, directory):
#         self.directory = os.path.abspath(directory)
#         self.redis_socket = f'{self.directory}/redis.socket'
#         self.redis_pid_file = f'{self.directory}/redis.pid'
#         self.redis = None
    
#     def claim_server(self):
#         if not os.path.exists(self.redis_socket):
#             # Start the redis server
#             cmd = [
#                 'redis-server',
#                 '--unixsocket', self.redis_socket,
#                 '--port', '0', # port 0 means no TCP connection
#                 '--daemonize', 'yes',
#                 '--pidfile', self.redis_pid_file,
#                 '--dir', self.directory,
#                 '--dbfilename', 'redis.rdb',
#             ]
#             subprocess.run(cmd)
#             for i in range(20):
#                 if os.path.exists(self.redis_socket):
#                     break
#                 time.sleep(0.1)
#             r  = redis.Redis(unix_socket_path=self.redis_socket)
#             r.set('capsul_connection_count', 1)
#         else:
#             r  = redis.Redis(unix_socket_path=self.redis_socket)
#             r.incr('capsul_connection_count')


#     def release_server(self):
#         if os.path.exists(self.redis_socket):
#             r  = redis.Redis(unix_socket_path=self.redis_socket)
#             capsul_connection_count = r.decr('capsul_connection_count')
#             if capsul_connection_count == 0:
#                 # Kill the redis server
#                 with open(self.redis_pid_file) as f:
#                     pid = int(f.read().strip())
#                 os.kill(pid, signal.SIGTERM)

#     def __enter__(self):
#         self.claim_server()
#         self.redis = redis.Redis(unix_socket_path=self.redis_socket, decode_responses=True)
#         return self

#     def __exit__(self, *args):
#         self.redis = None
#         self.release_server()
    
#     def save(self):
#         self.redis.save()
    
#     @property
#     def status(self):
#         return self.redis.get('status')

#     @status.setter
#     def status(self, status):
#         self.redis.set('status', status)

#     @property
#     def error(self):
#         return self.redis.get('error')

#     @error.setter
#     def error(self, error):
#         self.redis.set('error', error)

#     @property
#     def error_detail(self):
#         return self.redis.get('error_detail')

#     @error_detail.setter
#     def error_detail(self, error_detail):
#         self.redis.set('error_detail', error_detail)

#     @property
#     def execution_context(self):
#         s = self.redis.get('execution_context')
#         if s is not None:
#             return ExecutionContext(config=json.loads(s))

#     @execution_context.setter
#     def execution_context(self, execution_context):
#         self.redis.set('execution_context', json_dumps(execution_context.json()))
    
#     @property
#     def executable(self):
#         s = self.redis.get('executable')
#         if s is not None:
#             if s.startswith('!'):
#                 j = json_decode(json.loads(s[1:]))
#             else:
#                 j = json.loads(s)
#             return Capsul.executable(j)

#     @executable.setter
#     def executable(self, executable):
#         j = executable.json(include_parameters=False)
#         try:
#             s = json_dumps(j)
#         except TypeError:
#             s = '!' + json_dumps(json_encode(j))
#         self.redis.set('executable', s)
    
#     @property
#     def start_time(self):
#         s = self.redis.get('start_time')
#         if s is not None:
#             return dateutil.parser.parse(s)

#     @start_time.setter
#     def start_time(self, value):
#         self.redis.set('start_time', value.isoformat())

#     @property
#     def end_time(self):
#         s = self.redis.get('end_time')
#         if s is not None:
#             return dateutil.parser.parse(s)

#     @end_time.setter
#     def end_time(self, value):
#         self.redis.set('end_time', value.isoformat())

#     def save_workflow(self, workflow):
#         self.redis.delete('waiting')
#         self.redis.delete('ready')
#         self.redis.delete('ongoing')
#         self.redis.delete('done')
#         self.redis.delete('failed')
#         for job_uuid, job in workflow.jobs.items():
#             self.set_job(job_uuid, job)
#             if job['wait_for']:
#                 self.redis.sadd('waiting', job_uuid)
#             else:
#                 self.redis.sadd('ready', job_uuid)
#         self.workflow_parameters = workflow.parameters

#     def set_job(self, job_uuid, job):
#         start_time = job.get('start_time')
#         end_time = job.get('end_time')
#         if start_time or end_time:
#             job = job.copy()
#             if start_time:
#                 job['start_time'] = json_encode(start_time)
#             if end_time:
#                 job['end_time'] = json_encode(end_time)
#         job['uuid'] = job_uuid
#         self.redis.hset('job', job_uuid, json_dumps(job))

#     @property
#     def workflow_parameters(self):
#         s = self.redis.get('workflow_parameters')
#         if s is not None:
#             if s.startswith('!'):
#                 j = json_decode(json.loads(s[1:]))
#             else:
#                 j = json.loads(s)
#             return DictWithProxy.from_json(j)
#         return None
    
#     @workflow_parameters.setter
#     def workflow_parameters(self, parameters):
#         j = parameters.json()
#         try:
#             s = json_dumps(j)
#         except TypeError:
#             s = '!' + json_dumps(json_encode(j))
#         self.redis.set('workflow_parameters', s)

#     def jobs(self):
#         return (self.job(i) for i in self.redis.hkeys('job'))

#     def job(self, job_uuid):
#         s = self.redis.hget('job', job_uuid)
#         if s is not None:
#             job = json.loads(s)
#             start_time = job.get('start_time')
#             if start_time:
#                 job['start_time'] = json_decode(start_time)
#             end_time = job.get('end_time')
#             if end_time:
#                 job['end_time'] = json_decode(end_time)
#             return job

#     @property
#     def waiting(self):
#         return self.redis.smembers('waiting')

#     @property
#     def ready(self):
#         return self.redis.smembers('ready')

#     @property
#     def ongoing(self):
#         return self.redis.smembers('ongoing')

#     @property
#     def done(self):
#         return self.redis.smembers('done')

#     @property
#     def failed(self):
#         return self.redis.smembers('failed')
   
#     def move_to_ready(self, job_uuid):
#         self.redis.sadd('ready', job_uuid)
#         self.redis.srem('waiting', job_uuid)

#     def move_to_ongoing(self, job_uuid):
#         job = self.job(job_uuid)
#         job['start_time'] = datetime.datetime.now()
#         self.set_job(job_uuid, job)
#         self.redis.sadd('ongoing', job_uuid)
#         self.redis.srem('ready', job_uuid)

#     def move_to_done(self, job_uuid, returncode, stdout, stderr):
#         job = self.job(job_uuid)
#         job['returncode'] = returncode
#         job['stdout'] = stdout
#         job['stderr'] = stderr
#         job['end_time'] = datetime.datetime.now()
#         self.set_job(job_uuid, job)
#         if returncode:
#             self.redis.sadd('failed', job_uuid)
#             stack = [job_uuid]
#             while stack:
#                 uuid = stack.pop(0)
#                 job = self.job(uuid)
#                 job['returncode'] = 'Not started because de dependent job failed'
#                 self.set_job(uuid, job)
#                 self.redis.srem('waiting', uuid)
#                 self.redis.sadd('failed', uuid)
#                 stack.extend(job.get('waited_by', []))
#         else:
#             self.redis.sadd('done', job_uuid)
#             for waiting_uuid in job.get('waited_by', []):
#                 waiting_job = self.job(waiting_uuid)
#                 for waited in waiting_job.get('wait_for', []):
#                     if not self.redis.sismember('done', waited):
#                         break
#                 else:
#                     self.redis.srem('waiting', waiting_uuid)
#                     self.redis.sadd('ready', waiting_uuid)
#         self.redis.srem('ongoing', job_uuid)
#         print(f"move_to_done {job_uuid} ongoing={self.redis.scard('ongoing')} ready={self.redis.scard('ready')}")
#         if self.redis.scard('ongoing') or self.redis.scard('ready'):
#             return False
#         else:
#             if self.redis.scard('failed'):
#                 self.status = 'error'
#                 self.error = 'Some jobs failed'
#             return True
