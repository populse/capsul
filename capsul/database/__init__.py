# -*- coding: utf-8 -*-
from datetime import datetime
import dateutil.parser
import importlib
import json
from pprint import pprint
import re
import sys
import time

from populse_db.database import json_encode, json_decode

from soma.api import DictWithProxy, undefined

from ..application import Capsul
from ..execution_context import ExecutionContext
from ..pipeline.pipeline import Process, Pipeline

database_classes = {
    'sqlite': 'capsul.database.populse_db:Populse_dbExecutionDatabase',
    'redis': 'capsul.database.redis:RedisExecutionDatabase',
    'redis+socket': 'capsul.database.redis:RedisExecutionDatabase',
}

class URL:
    pattern = re.compile(
        r'^(?P<scheme>[^:]+)://'
        r'(?:(?P<login>[^:]+)(?::(?P<password>[^@]+))?@)?'
        r'(?:(?P<host>[\w\.]+)(?::(?P<port>\d+))?)?'
        r'(?P<path>[^;?#]*)'
        r'(?:;(?P<parameters>[^?#]+))?'
        r'(?:\?(?P<query>[^#]+))?'
        r'(?:#(?P<fragment>.+))?$'
        )

    def __init__(self, string):
        m = self.pattern.match(string)
        if not m:
            raise ValueError(f'Invalid URL: {string}')
        for k, v in m.groupdict().items():
            setattr(self, k, v)
    
    def __str__(self):
        if self.login:
            if self.password:
                login = f'{self.login}:{self.password}@'
            else:
                login = f'{self.login}@'
        else:
            login = ''
        if self.host:
            if self.port:
                host = f'{self.host}:{self.port}'
            else:
                host = self.host
        else:
            host = ''
        if self.path:
            path = self.path
        else:
            path = ''
        if self.parameters:
            parameters = f';{parameters}'
        else:
            parameters = ''
        if self.query:
            query = f'?{query}'
        else:
            query = ''
        if self.fragment:
            fragment = f'#{fragment}'
        else:
            fragment = ''
        return f'{self.scheme}://{login}{host}{path}{parameters}{query}{fragment}'


def engine_database(config):
    class_string = database_classes.get(config['type'])
    if class_string is None:
        raise ValueError(f'Invalid database type: {config["type"]}')
    module_name, class_name = class_string.rsplit(':', 1)
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
            self._path = self.config.get('path')
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
        db_config = self.worker_database_config(self.engine_id)
        db_config = json.dumps(db_config, separators=(',',':'))
        workers_command = []
        config = self.engine_config(engine_id)
        config = config.get('start_workers')
        if not config:
            raise RuntimeError('No configuration defined to start workers')
        ssh = config.get('ssh')
        if ssh:
            host = ssh.get('host')
            if not host:
                raise ValueError('Host is mandatory in configuration for a ssh connection')
            login = ssh.get('login')
            if login:
                host = f'{login}@{host}'
            workers_command += ['ssh', '-o', 'StrictHostKeyChecking=no', '-f', host]
            db_config = db_config.replace('"',r'\"').replace(',', r'\,')
        
        casa_dir = config.get('casa_dir')
        if casa_dir:
            workers_command.append(f'{casa_dir}/bin/bv')

        workers_command += ['python', '-m', f'capsul.engine.builtin', engine_id, db_config]
        return workers_command
    
    def new_execution(self, executable, engine_id, execution_context, workflow, start_time):
        executable_json = json_encode(executable.json(include_parameters=False))
        execution_context_json = execution_context.json()
        workflow_parameters_json = json_encode(workflow.parameters.json())
        ready = []
        waiting = []
        jobs = [self._job_to_json(job.copy()) for job in workflow.jobs.values()]
        for job in jobs:
            if job['wait_for']:
                waiting.append(job['uuid'])
            else:
                ready.append(job['uuid'])
        execution_id = self.store_execution(
            engine_id,
            label=executable.label,
            start_time=self._time_to_json(start_time),
            executable_json=executable_json,
            execution_context_json=execution_context_json,
            workflow_parameters_json=workflow_parameters_json,
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
    
    def workflow_parameters(self, engine_id, execution_id):
        j = self.workflow_parameters_json(engine_id, execution_id)
        if j:
            return DictWithProxy.from_json(json_decode(j))


    def set_workflow_parameters(self, engine_id, execution_id, workflow_parameters):
        self.set_workflow_parameters_json(engine_id, execution_id, json_encode(workflow_parameters.json()))


    def update_workflow_parameters(self, engine_id, execution_id, parameters_location, output_values):
        self.update_workflow_parameters_json(engine_id, execution_id, parameters_location, json_encode(output_values))


    @staticmethod
    def _time_from_json(time_json):
        return dateutil.parser.parse(time_json)

    @staticmethod
    def _time_to_json(time):
        return time.isoformat()
    

    def _job_from_json(self, job):
        for k in ('start_time', 'end_time'):
            t = job.get(k)
            if t:
                job[k] = self._time_from_json(t)
        return job


    def _job_to_json(self, job):
        for k in ('start_time', 'end_time'):
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
        report['engine_id'] = engine_id
        report['execution_id'] = execution_id
        execution_context = report['execution_context']
        if execution_context is not None:
            execution_context = ExecutionContext(config=execution_context)
        report['execution_context'] = execution_context
        workflow_parameters = report['workflow_parameters']
        if workflow_parameters is not None:
            workflow_parameters = DictWithProxy.from_json(workflow_parameters)
        report['workflow_parameters'] = workflow_parameters        
        for n in ('start_time', 'end_time'):
            j = report.get(n)
            if j:
                report[n] = self._time_from_json(j)
        
        for job in report['jobs']:
            self._job_from_json(job)
            if job['uuid'] in report['done']:
                job['status'] = 'done'
            elif job['uuid'] in report['failed']:
                job['status'] = 'failed'
            elif job['uuid'] in report['ongoing']:
                job['status'] = 'ongoing'
            elif job['uuid'] in report['ready']:
                job['status'] = 'ready'
            elif job['uuid'] in report['waiting']:
                job['status'] = 'waiting'
            else:
                job['status'] = 'unknown'
        return report
    
    def print_execution_report(self, report, file=sys.stdout):
        print('====================\n'
              '| Execution report |\n'
              '====================\n', file=file)
        print('label:', report['label'], file=file)
        print('status:', report['status'], file=file)
        print('start time:', report['start_time'], file=file)
        print('end time:', report['end_time'], file=file)
        print('execution_id:', report['execution_id'], file=file)
        print('execution context:', file=file)
        pprint(report['execution_context'].asdict(), stream=file)
        if report['error']:
            print('error:', report['error'], file=file)
        if report['error_detail']:
            print('-' * 50, file=file)
            print(report['error_detail'], file=file)
            print('-' * 50, file=file)
        print('\n---------------\n'
              '| Jobs status |\n'
              '---------------\n', file=file)
        print('waiting:', report['waiting'])
        print('ready:', report['ready'])
        print('ongoing:', report['ongoing'])
        print('done:', report['done'])
        print('failed:', report['failed'])
        now = datetime.now()
        for job in sorted(report['jobs'], key=lambda j: (j.get('start_time') if j.get('start_time') else now)):
            job_uuid = job['uuid']
            process_definition = job.get('process', {}).get('definition')
            start_time = job.get('start_time')
            end_time = job.get('end_time')
            pipeline_node = '.'.join(i for i in job.get('parameters_location', '') if i != 'nodes')
            returncode = job.get('returncode')
            status = job['status']
            disabled = job['disabled']
            stdout = job.get('stdout')
            stderr = job.get('stderr')
            parameters = report['workflow_parameters']
            if parameters:
                for index in job.get('parameters_location', []):
                    if index.isnumeric():
                        index = int(index)
                    parameters = parameters[index]
            wait_for = job.get('wait_for', [])
            waited_by = job.get('waited_by', [])

            print('=' * 50, file=file)
            print('job uuid:', job_uuid, file=file)
            print('process:', process_definition, file=file)
            print('pipeline node:', pipeline_node, file=file)
            print('status:', status, file=file)
            print('returncode:', returncode, file=file)
            print('start time:', start_time, file=file)
            print('end time:', end_time, file=file)
            print('disabled:', disabled, file=file)
            print('wait for:', wait_for, file=file)
            print('waited_by:', waited_by, file=file)
            if parameters:
                print('parameters:', file=file)
                pprint(parameters.no_proxy(), stream=file)
            else:
                print('parameters: none', file=file)
            if stdout:
                print('---------- standard output ----------', file=file)
                print(stdout, file=file)
            if stderr:
                print('---------- error output ----------', file=file)
                print(stderr, file=file)

        if report['engine_debug']:
            print('\n----------------\n'
                '| Engine debug |\n'
                '----------------\n', file=file)
            for k, v in report['engine_debug'].items():
                print(k, file=file)
                print('-' * len(k), file=file)
                print(v, file=file)
                print(file=file)

    def wait(self, engine_id, execution_id, timeout=None):
        start = time.time()
        status = self.status(engine_id, execution_id)
        if status == 'ready':
            for i in range(100):
                time.sleep(0.2)
                status = self.status(engine_id, execution_id)
                if status != 'ready':
                    break
            else:
                self.print_execution_report(self.execution_report(engine_id, execution_id), file=sys.stderr)
                raise SystemError(f'workers are too slow to start execution ({datetime.now()})')
        status = self.status(engine_id, execution_id)
        while status != 'ended':
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError('Process execution timeout')
            time.sleep(0.1)
            status = self.status(engine_id, execution_id)

    def raise_for_status(self, engine_id, execution_id):
        error = self.error(engine_id, execution_id)
        if error:
            self.print_execution_report(self.execution_report(engine_id, execution_id), file=sys.stderr)
            raise RuntimeError(error)

    def update_executable(self, engine_id, execution_id, executable):
        parameters = self.workflow_parameters(engine_id, execution_id)
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
                for field in node.user_fields():
                    value = parameters.get(field.name, undefined)
                    if value is not undefined:
                        value = parameters.no_proxy(value)
                        if value is None:
                            value = undefined
                        # print('!update_executable!', node.full_name, field.name, '<-', repr(value))
                        setattr(node, field.name, value)
                    # else:
                    #     print('!update_executable! ignore', node.full_name, field.name, repr(value))
                if isinstance(node, Pipeline):
                    stack.extend((n, parameters['nodes'][n.name]) for n in node.nodes.values() if n is not node and isinstance(n, Process) and n.activated)
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


    def get_or_create_engine(self, engine):
        '''
        If engine with given label is in the database, simply return its
        engine_id. Otherwise, create a new engine in the database and return
        its engine_id.
        '''
        raise NotImplementedError


    def engine_config(self, engine_id):
        '''
        Return the configuration dict stored for an engine
        '''
        raise NotImplementedError


    def workers_count(self, engine_id):
        '''
        Return the number of workers that are running.
        '''
        raise NotImplementedError


    def worker_database_config(self, engine_id):
        '''
        Return database connection settings for workers. This
        connection may be different than the client connection
        if the database implementation create engine specific
        internal access with restricted access rights.
        '''
        raise NotImplementedError


    def worker_started(self, engine_id):
        '''
        Register a new worker that had been started for this engine and
        return an identifier for it.
        '''
        raise NotImplementedError


    def worker_ended(self, engine_id, worker_id):
        '''
        Remove a worker from the list of workers for this engine.
        '''
        raise NotImplementedError


    def dispose_engine(self, engine_id):
        '''
        Tell Capsul that this engine will not be used anymore by any client.
        The ressource it uses must be freed as soon as possible. If no 
        execution is running, engine is destroyed. Otherwise, workers will
        process ongoing executions and cleanup when done.
        '''
        raise NotImplementedError


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
        raise NotImplementedError


    def execution_context(self, engine_id, execution_id):
        j = self.execution_context_json(engine_id, execution_id)
        if j is not None:
            return ExecutionContext(config=j)


    def execution_context_json(self, engine_id, execution_id):
        raise NotImplementedError


    def pop_job(self, engine_id, start_time):
        '''
        Convert its parameters to JSON and calls pop_job_json()
        '''
        return self.pop_job_json(engine_id, self._time_to_json(start_time))
    


    def pop_job_json(self, engine_id, start_time):
        raise NotImplementedError


    def job_finished(self, engine_id, execution_id, job_uuid, end_time, returncode, stdout, stderr):
        '''
        Convert its parameters to JSON and calls job_finished_json()
        '''
        self.job_finished_json(engine_id, execution_id, job_uuid, 
            self._time_to_json(end_time), returncode, stdout, stderr)


    def job_finished_json(self, engine_id, execution_id, job_uuid, end_time, returncode, stdout, stderr):
        raise NotImplementedError



    def status(self, engine_id, execution_id):
        raise NotImplementedError

        
    def workflow_parameters_json(self, engine_id, execution_id):
        raise NotImplementedError


    def set_workflow_parameters_json(self, engine_id, execution_id, workflow_parameters_json):
        raise NotImplementedError


    def update_workflow_parameters_json(self, engine_id, execution_id, parameters_location, output_values):
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
