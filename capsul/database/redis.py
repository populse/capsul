import datetime
import dateutil
import dateutil.parser
import json
import os
import signal
import subprocess
import time

import redis

from soma.api import DictWithProxy

from .application import Capsul
from .execution_context import ExecutionContext

def json_dumps(value):
    return json.dumps(value, separators=(',', ':'))

_json_encodings = {
    datetime.datetime: lambda d: f'{d.isoformat()}ℹdatetimeℹ',
    datetime.date: lambda d: f'{d.isoformat()}ℹdateℹ',
    datetime.time: lambda d: f'{d.isoformat()}ℹtimeℹ',
    list: lambda l: [json_encode(i) for i in l],
    dict: lambda d: dict((k, json_encode(v)) for k, v in d.items()),
}

_json_decodings = {
    'datetime': lambda s: dateutil.parser.parse(s),
    'date': lambda s: dateutil.parser.parse(s).date(),
    'time': lambda s: dateutil.parser.parse(s).time(),
}

def json_encode(value):
    global _json_encodings

    type_ = type(value)
    encode = _json_encodings.get(type_)
    if encode is not None:
        return encode(value)
    return value

def json_decode(value):
    global _json_decodings

    if isinstance(value, list):
        return [json_decode(i) for i in value]
    elif isinstance(value, dict):
        return dict((k, json_decode(v)) for k, v in value.items())
    elif isinstance(value, str):
        if value.endswith('ℹ'):
            l = value[:-1].rsplit('ℹ', 1)
            if len(l) == 2:
                encoded_value, decoding_name = l
                decode = _json_decodings.get(decoding_name)
                if decode is None:
                    raise ValueError(f'Invalid JSON encoding type for value "{value}"')
                return decode(encoded_value)
    return value

class RedisExecutionDatabase:
    def __init__(self, directory):
        self.directory = os.path.abspath(directory)
        self.redis_socket = f'{self.directory}/redis.socket'
        self.redis_pid_file = f'{self.directory}/redis.pid'
        self.redis = None
    
    def claim_server(self):
        if not os.path.exists(self.redis_socket):
            # Start the redis server
            cmd = [
                'redis-server',
                '--unixsocket', self.redis_socket,
                '--port', '0', # port 0 means no TCP connection
                '--daemonize', 'yes',
                '--pidfile', self.redis_pid_file,
                '--dir', self.directory,
                '--dbfilename', 'redis.rdb',
            ]
            subprocess.run(cmd)
            for i in range(20):
                if os.path.exists(self.redis_socket):
                    break
                time.sleep(0.1)
            r  = redis.Redis(unix_socket_path=self.redis_socket)
            r.set('capsul_connection_count', 1)
        else:
            r  = redis.Redis(unix_socket_path=self.redis_socket)
            r.incr('capsul_connection_count')


    def release_server(self):
        if os.path.exists(self.redis_socket):
            r  = redis.Redis(unix_socket_path=self.redis_socket)
            capsul_connection_count = r.decr('capsul_connection_count')
            if capsul_connection_count == 0:
                # Kill the redis server
                with open(self.redis_pid_file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)

    def __enter__(self):
        self.claim_server()
        self.redis = redis.Redis(unix_socket_path=self.redis_socket, decode_responses=True)
        return self

    def __exit__(self, *args):
        self.redis = None
        self.release_server()
    
    def save(self):
        self.redis.save()
    
    @property
    def status(self):
        return self.redis.get('status')

    @status.setter
    def status(self, status):
        self.redis.set('status', status)

    @property
    def error(self):
        return self.redis.get('error')

    @error.setter
    def error(self, error):
        self.redis.set('error', error)

    @property
    def error_detail(self):
        return self.redis.get('error_detail')

    @error_detail.setter
    def error_detail(self, error_detail):
        self.redis.set('error_detail', error_detail)

    @property
    def execution_context(self):
        s = self.redis.get('execution_context')
        if s is not None:
            return ExecutionContext(config=json.loads(s))

    @execution_context.setter
    def execution_context(self, execution_context):
        self.redis.set('execution_context', json_dumps(execution_context.json()))
    
    @property
    def executable(self):
        s = self.redis.get('executable')
        if s is not None:
            if s.startswith('!'):
                j = json_decode(json.loads(s[1:]))
            else:
                j = json.loads(s)
            return Capsul.executable(j)

    @executable.setter
    def executable(self, executable):
        j = executable.json()
        try:
            s = json_dumps(j)
        except TypeError:
            s = '!' + json_dumps(json_encode(j))
        self.redis.set('executable', s)
    
    @property
    def start_time(self):
        s = self.redis.get('start_time')
        if s is not None:
            return dateutil.parser.parse(s)

    @start_time.setter
    def start_time(self, value):
        self.redis.set('start_time', value.isoformat())

    @property
    def end_time(self):
        s = self.redis.get('end_time')
        if s is not None:
            return dateutil.parser.parse(s)

    @end_time.setter
    def end_time(self, value):
        self.redis.set('end_time', value.isoformat())

    def save_workflow(self, workflow):
        self.redis.delete('waiting')
        self.redis.delete('ready')
        self.redis.delete('ongoing')
        self.redis.delete('done')
        self.redis.delete('failed')
        for job_uuid, job in workflow.jobs.items():
            self.set_job(job_uuid, job)
            if job['wait_for']:
                self.redis.sadd('waiting', job_uuid)
            else:
                self.redis.sadd('ready', job_uuid)
        self.workflow_parameters = workflow.parameters

    def set_job(self, job_uuid, job):
        start_time = job.get('start_time')
        end_time = job.get('end_time')
        if start_time or end_time:
            job = job.copy()
            if start_time:
                job['start_time'] = json_encode(start_time)
            if end_time:
                job['end_time'] = json_encode(end_time)
        job['uuid'] = job_uuid
        self.redis.hset('job', job_uuid, json_dumps(job))

    @property
    def workflow_parameters(self):
        s = self.redis.get('workflow_parameters')
        if s is not None:
            if s.startswith('!'):
                j = json_decode(json.loads(s[1:]))
            else:
                j = json.loads(s)
            return DictWithProxy.from_json(j)
        return None
    
    @workflow_parameters.setter
    def workflow_parameters(self, parameters):
        j = parameters.json()
        try:
            s = json_dumps(j)
        except TypeError:
            s = '!' + json_dumps(json_encode(j))
        self.redis.set('workflow_parameters', s)

    def jobs(self):
        return (self.job(i) for i in self.redis.hkeys('job'))

    def job(self, job_uuid):
        s = self.redis.hget('job', job_uuid)
        if s is not None:
            job = json.loads(s)
            start_time = job.get('start_time')
            if start_time:
                job['start_time'] = json_decode(start_time)
            end_time = job.get('end_time')
            if end_time:
                job['end_time'] = json_decode(end_time)
            return job

    @property
    def waiting(self):
        return self.redis.smembers('waiting')

    @property
    def ready(self):
        return self.redis.smembers('ready')

    @property
    def ongoing(self):
        return self.redis.smembers('ongoing')

    @property
    def done(self):
        return self.redis.smembers('done')

    @property
    def failed(self):
        return self.redis.smembers('failed')
   
    def move_to_ready(self, job_uuid):
        self.redis.srem('waiting', job_uuid)
        self.redis.sadd('ready', job_uuid)

    def move_to_ongoing(self, job_uuid):
        job = self.job(job_uuid)
        job['start_time'] = datetime.datetime.now()
        self.set_job(job_uuid, job)
        self.redis.srem('ready', job_uuid)
        self.redis.sadd('ongoing', job_uuid)

    def move_to_done(self, job_uuid, returncode, stdout, stderr):
        self.redis.srem('ongoing', job_uuid)
        job = self.job(job_uuid)
        job['returncode'] = returncode
        job['stdout'] = stdout
        job['stderr'] = stderr
        job['end_time'] = datetime.datetime.now()
        self.set_job(job_uuid, job)
        if returncode:
            self.redis.sadd('failed', job_uuid)
            stack = [job_uuid]
            while stack:
                uuid = stack.pop(0)
                job = self.job(uuid)
                job['returncode'] = 'Not started because de dependent job failed'
                self.set_job(uuid, job)
                self.redis.srem('waiting', uuid)
                self.redis.sadd('failed', uuid)
                stack.extend(job.get('waited_by', []))
        else:
            self.redis.sadd('done', job_uuid)
            for waiting_uuid in job.get('waited_by', []):
                waiting_job = self.job(waiting_uuid)
                for waited in waiting_job.get('wait_for', []):
                    if not self.redis.sismember('done', waited):
                        break
                else:
                    self.redis.srem('waiting', waiting_uuid)
                    self.redis.sadd('ready', waiting_uuid)
        if self.redis.scard('ongoing') or self.redis.scard('ready'):
            return False
        else:
            if self.redis.scard('failed'):
                self.status = 'error'
                self.error = 'Some jobs failed'
            return True
