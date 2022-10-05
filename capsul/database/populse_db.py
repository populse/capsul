# -*- coding: utf-8 -*-
import os
from uuid import uuid4

from populse_db import Database

from . import ExecutionDatabase

class Populse_dbExecutionDatabase(ExecutionDatabase):
    def __init__(self, url):
        super().__init__(url)
        if url.query or url.fragment:
            raise ValueError(f'Invalid URL: {self.url}')
        self.sqlite_file = f'{url.netloc}{url.path}'
        self.database = Database(f'sqlite://{self.sqlite_file}')
        with self.database as session:
            if not session.has_collection('execution'):
                session.add_collection('global')
                session['global'].add_field('capsul_connection_count', int)
                session['global'][''] = {
                    'capsul_connection_count': 1,
                }
                session.add_collection('execution')
                execution = session['execution']
                execution.add_field('label', str)
                execution.add_field('status', str)
                execution.add_field('error', str)
                execution.add_field('error_detail', str)
                execution.add_field('execution_context', dict)
                execution.add_field('executable', dict)
                execution.add_field('start_time', str)
                execution.add_field('end_time', str)
                execution.add_field('waiting', list[str])
                execution.add_field('ready', list[str])
                execution.add_field('ongoing', list[str])
                execution.add_field('done', list[str])
                execution.add_field('failed', list[str])
                execution.add_field('workflow_parameters', dict)
                execution.add_field('dispose', bool)
                execution.add_field('tmp', str)

                session.add_collection('job', ('execution_id', 'uuid'))
            else:
                connection_count = session['global']['']['capsul_connection_count'] + 1
                session['global'][''] = {'capsul_connection_count': connection_count}
    
    def close(self):
        with self.database as session:
            connection_count = session['global']['']['capsul_connection_count']
            if connection_count > 0:
               connection_count -= 1
               session['global'][''] = {'capsul_connection_count': connection_count}
               delete_database = (connection_count == 0)
            else:
                delete_database = False
        
        del self.database
        if delete_database:
            os.remove(self.sqlite_file)
    
    def _get(self, execution_id, name):
        with self.database as session:
            row = session['execution'].document(execution_id, fields=[name], as_list=True)
            if row is not None:
                return row[0]
            return None
    
    def _set(self, execution_id, name, value):
        with self.database as session:
            session['execution'].update_document(execution_id, {name: value})

    def store_execution(self,
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
        execution = {
            'label': label,
            'status': 'ready',
            'start_time': start_time,
            'executable': executable_json,
            'execution_context': execution_context_json,
            'workflow_parameters': workflow_parameters_json,
            'ready': ready,
            'waiting': waiting,
            'ongoing': [],
            'done': [],
            'failed': [],
            'dispose': False,
        }
        if not ready:
            execution['status']  = 'ended'
            execution['end_time'] = start_time
        with self.database as session:
            session['execution'][execution_id] = execution
            for job in jobs:
                session['job'][(execution_id, job['uuid'])] = job
        return execution_id
    
    def status(self, execution_id):
        return self._get(execution_id, 'status')

    def error(self, execution_id):
        return self._get(execution_id, 'error')

    def error_detail(self, execution_id):
        return self._get(execution_id, 'error_detail')

    def set_error(self, execution_id, error, error_detail=None):
        with self.database as session:
            session['execution'].update_document(execution_id, {
                'error': error,
                'error_detail': error_detail
            })
    
    def execution_context_json(self, execution_id):
        return self._get(execution_id, 'execution_context')

    def executable_json(self, execution_id):
        return self._get(execution_id, 'executable')
    
    def workflow_parameters_json(self, execution_id):
        return self._get(execution_id, 'workflow_parameters')

    def set_workflow_parameters_json(self, execution_id, workflow_parameters_json):
        with self.database as session:
            session['execution'].update_document(
                execution_id,
                {
                    'workflow_parameters': workflow_parameters_json
                }
            )

    def update_workflow_parameters_json(self, execution_id, parameters_location, output_values):
        workflow_parameters = self.workflow_parameters(execution_id)
        parameters = workflow_parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        for k, v in output_values.items():
            parameters[k] = v
        self.set_workflow_parameters(execution_id, workflow_parameters)

    def start_time_json(self, execution_id):
        return self._get(execution_id, 'start_time')

    def end_time_json(self, execution_id):
        return self._get(execution_id, 'end_time')

    def jobs_json(self, execution_id):
        with self.database as session:
            yield from session['job'].filter(f'{{execution_id}}=="{execution_id}"')

    def job_json(self, execution_id, job_uuid):
        with self.database as session:
            result = session['job'][(execution_id, job_uuid)]
            return result

    def ready(self ,execution_id):
        return self._get(execution_id, 'ready')

    def waiting(self ,execution_id):
        return self._get(execution_id, 'waiting')

    def ongoing(self ,execution_id):
        return self._get(execution_id, 'ongoing')

    def done(self ,execution_id):
        return self._get(execution_id, 'done')

    def failed(self ,execution_id):
        return self._get(execution_id, 'failed')
   
    def start_one_job_json(self, execution_id, start_time):
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
    
    def job_finished_json(self, execution_id, job_uuid, end_time, returncode, stdout, stderr):
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
                    execution['error'] = 'Some jobs failed'
                execution['status'] = 'ended'
                execution['end_time'] = end_time
                result = True
            session['execution'].update_document(execution_id, execution)
            return result

    def execution_report_json(self, execution_id):
        with self.database as session:
            result = dict(
                label = self.label(execution_id),
                execution_context = self.execution_context_json(execution_id),
                status = self.status(execution_id),
                error = self.error(execution_id),
                error_detail = self.error_detail(execution_id),
                start_time = self.start_time_json(execution_id),
                end_time = self.end_time_json(execution_id),
                waiting = self.waiting(execution_id),
                ready = self.ready(execution_id),
                ongoing = self.ongoing(execution_id),
                done = self.done(execution_id),
                failed = self.failed(execution_id),
                jobs = list(self.jobs_json(execution_id)),
                workflow_parameters = self.workflow_parameters_json(execution_id),
                engine_debug = {}
            )
        return result
        
    def dispose(self, execution_id):
        with self.database as session:
            if self.status(execution_id) == 'ended':
                session['job'].delete(f'{{execution_id}}=="{execution_id}"')
                del session['execution'][execution_id]
            else:
                session['execution'].update_document(execution_id, {'dispose': True})
        
    def set_tmp(self, execution_id, tmp):
        self._set(execution_id, 'tmp', tmp)

    def tmp(self, execution_id):
        return self._get(execution_id, 'tmp')

    def label(self, execution_id):
        return self._get(execution_id, 'label')
