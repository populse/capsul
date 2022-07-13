# -*- coding: utf-8 -*-
from datetime import datetime
import dateutil.parser
import importlib
from pprint import pprint
from urllib.parse import urlsplit, urlunsplit
import sys
import time

from populse_db.database import json_encode, json_decode

from soma.api import DictWithProxy, undefined

from ..application import Capsul
from ..execution_context import ExecutionContext
from ..pipeline.pipeline import Process, Pipeline

database_classes = {
    'sqlite': 'capsul.database.populse_db:Populse_dbExecutionDatabase',
    'redis+socket': 'capsul.database.redis:RedisExecutionDatabase',
}

def execution_database(database_url):
    url = urlsplit(database_url)
    class_string = database_classes.get(url.scheme)
    if class_string is None:
        raise ValueError(f'Invalid database URL {database_url}: scheme {url.scheme} is not supported')
    module_name, class_name = class_string.rsplit(':', 1)
    module = importlib.import_module(module_name)
    database_class = getattr(module, class_name)
    return database_class(url)


class ExecutionDatabase:
    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        return urlunsplit(self._url)

    def new_execution(self, executable, execution_context, workflow, start_time):
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
            start_time=self._time_to_json(start_time),
            executable_json=executable_json,
            execution_context_json=execution_context_json,
            workflow_parameters_json=workflow_parameters_json,
            jobs=jobs,
            ready=ready,
            waiting=waiting,
        )
        return execution_id

    def _execution_context_from_json(self, execution_context_json):
        return ExecutionContext(config=execution_context_json)

    def execution_context(self, execution_id):
        j = self.execution_context_json(execution_id)
        if j is not None:
            return self._execution_context_from_json(j)

    def _executable_from_json(self, executable_json):
        return Capsul.executable(json_decode(executable_json))
    
    def executable(self, execution_id):
        j = self.executable_json(execution_id)
        if j is not None:
            return self._executable_from_json(j)

    def _workflow_parameters_from_json(self, workflow_parameters_json):
        return DictWithProxy.from_json(json_decode(workflow_parameters_json))
    
    def workflow_parameters(self, execution_id):
        j = self.workflow_parameters_json(execution_id)
        if j:
            return self._workflow_parameters_from_json(j)

    def set_workflow_parameters(self, execution_id, workflow_parameters):
        self.set_workflow_parameters_json(execution_id, json_encode(workflow_parameters.json()))

    @staticmethod
    def _time_from_json(time_json):
        return dateutil.parser.parse(time_json)

    @staticmethod
    def _time_to_json(time):
        return time.isoformat()
    
    def start_time(self, execution_id):
        j = self.start_time_json(execution_id)
        if j:
            return self._time_from_json(j)
        return None

    def end_time(self, execution_id):
        j = self.end_time_json(execution_id)
        if j:
            return self._time_from_json(j)
        return None

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

    def jobs(self, execution_id):
        return [self._job_from_json(i) for i in self.jobs_json(execution_id)]

    def job(self, execution_id, job_uuid):
        j = self.job_json(execution_id, job_uuid)
        if j:
            return self._job_from_json(j)
        return None

    def execution_report(self, execution_id):
        report = self.execution_report_json(execution_id)
        for n in ('executable', 'execution_context', 'workflow_parameters'):
            convert = getattr(self, f'_{n}_from_json')
            report[n] = convert(report[n])
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
        print('executable:', report['executable'].definition, file=file)
        print('status:', report['status'], file=file)
        print('start time:', report['start_time'], file=file)
        print('end time:', report['end_time'], file=file)
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
            command = ' '.join(f"'{i}'" for i in job.get('command', []))
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
            print('command:', command, file=file)
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

    def wait(self, execution_id, timeout=None):
        start = time.time()
        status = self.status(execution_id)
        if status == 'ready':
            for i in range(50):
                time.sleep(0.1)
                status = self.status(execution_id)
                if status != 'ready':
                    break
            else:
                raise SystemError('workers are too slow to start execution')
        status = self.status(execution_id)
        while status == 'running':
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError('Process execution timeout')
            time.sleep(0.1)
            status = self.status(execution_id)

    def raise_for_status(self, execution_id):
        error = self.error(execution_id)
        if error:
            self.print_execution_report(self.execution_report(execution_id), file=sys.stderr)
            raise RuntimeError(error)

    def update_executable(self, executable, execution_id):
        parameters = self.workflow_parameters(execution_id)
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

    def start_next_job(self, execution_id, start_time):
        return self.start_next_job_json(execution_id, self._time_to_json(start_time))
    
    def job_finished(self, execution_id, job_uuid, end_time, returncode, stdout, stderr):
        return self.job_finished_json(execution_id, job_uuid, self._time_to_json(end_time), returncode, stdout, stderr)
