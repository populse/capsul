# -*- coding: utf-8 -*-
from datetime import datetime
import os

from soma.api import DictWithProxy
from populse_db import Database

from ..api import Capsul
from ..config.configuration import ModuleConfiguration
from ..execution_context import ExecutionContext

class Populse_dbExecutionDatabase:
    def __init__(self, directory):
        directory = os.path.abspath(directory)
        self.database = Database(f'sqlite://{directory}/populse_db.sqlite')
    
    def claim_server(self):
        pass

    def release_server(self):
        pass

    def __enter__(self):
        self.session = self.database.__enter__()
        if not self.session.has_collection('global'):
            self.session.add_collection('global')
            g = self.session['global']
            g.add_field('status', str)
            g.add_field('error', str)
            g.add_field('error_detail', str)
            g.add_field('execution_context', dict)
            g.add_field('executable', dict)
            g.add_field('start_time', datetime)
            g.add_field('end_time', datetime)
            g.add_field('waiting', list[str])
            g.add_field('ready', list[str])
            g.add_field('ongoing', list[str])
            g.add_field('done', list[str])
            g.add_field('failed', list[str])
            g.add_field('workflow_parameters', dict[str, list])
            g[''] = {}

            self.session.add_collection('job', 'uuid')

        return self

    def __exit__(self, *args):
        self.database.__exit__(*args)
        del self.session
    
    def save(self):
        pass
    
    def get_global(self, name):
        row = self.session['global'].document('', fields=[name], as_list=True)
        if row is not None:
            return row[0]
        return None
    
    def set_global(self, name, value):
        self.session['global'].update_document('', {name: value})

    @property
    def status(self):
        return self.get_global('status')

    @status.setter
    def status(self, status):
        self.set_global('status', status)

    @property
    def error(self):
        return self.get_global('error')

    @error.setter
    def error(self, error):
        self.set_global('error', error)

    @property
    def error_detail(self):
        return self.get_global('error_detail')

    @error_detail.setter
    def error_detail(self, error_detail):
        self.set_global('error_detail', error_detail)

    @property
    def execution_context(self):
        j = self.get_global('execution_context')
        if j is not None:
            return ExecutionContext(config=j)

    @execution_context.setter
    def execution_context(self, execution_context):
        json_context = execution_context.json()
        for k in list(json_context):
            # replace module classes with long name, if they are not in the
            # standard location (capsul.config)
            m = getattr(execution_context, k)
            if isinstance(m, ModuleConfiguration) \
                    and m.__class__.__module__.split('.') \
                        != ['capsul', 'config', m.name]:
                cls_name = f'{m.__class__.__module__}.{m.__class__.__name__}'
                json_context[cls_name] = json_context[k]
                del json_context[k]
        self.set_global('execution_context', json_context)
    
    @property
    def executable(self):
        j = self.get_global('executable')
        if j is not None:
            return Capsul.executable(j)

    @executable.setter
    def executable(self, executable):
        j = executable.json()
        self.set_global('executable', j)
    
    @property
    def start_time(self):
        return self.get_global('start_time')

    @start_time.setter
    def start_time(self, start_time):
        self.set_global('start_time', start_time)

    @property
    def end_time(self):
        return self.get_global('end_time')

    @end_time.setter
    def end_time(self, end_time):
        self.set_global('end_time', end_time)

    def save_workflow(self, workflow):
        for i in ('waiting, ready', 'ongoing', 'done', 'failed'):
            self.set_global(i, [])
        waiting = []
        ready = []
        for job_uuid, job in workflow.jobs.items():
            self.set_job(job_uuid, job)
            if job['wait_for']:
                waiting.append(job_uuid)
            else:
                ready.append(job_uuid)
        self.set_global('waiting', waiting)
        self.set_global('ready', ready)
        self.workflow_parameters = workflow.parameters

    def set_job(self, job_uuid, job):
        self.session['job'][job_uuid] = job

    @property
    def workflow_parameters(self):
        j = self.get_global('workflow_parameters')
        if j:
            return DictWithProxy.from_json(j)
    
    @workflow_parameters.setter
    def workflow_parameters(self, parameters):
        self.set_global('workflow_parameters', parameters.json())

    def jobs(self):
        return self.session['job'].documents()

    def job(self, job_uuid):
        return self.session['job'][job_uuid]

    @property
    def waiting(self):
        return self.get_global('waiting')

    @property
    def ready(self):
        return self.get_global('ready')

    @property
    def ongoing(self):
        return self.get_global('ongoing')

    @property
    def done(self):
        return self.get_global('done')

    @property
    def failed(self):
        return self.get_global('failed')
   
    def move_to_ready(self, job_uuid):
        waiting = self.get_global('waiting')
        waiting.remove(job_uuid)
        self.set_global('waiting', waiting)
        ready = self.get_global('ready')
        ready.append(job_uuid)
        self.set_global('ready', ready)

    def move_to_ongoing(self, job_uuid):
        job = self.job(job_uuid)
        job['start_time'] = datetime.now()
        self.set_job(job_uuid, job)
        ready = self.get_global('ready')
        ready.remove(job_uuid)
        self.set_global('ready', ready)
        ongoing = self.get_global('ongoing')
        ongoing.append(job_uuid)
        self.set_global('ongoing', ongoing)

    def move_to_done(self, job_uuid, returncode, stdout, stderr):
        ongoing = self.get_global('ongoing')
        ongoing.remove(job_uuid)
        self.set_global('ongoing', ongoing)
        job = self.job(job_uuid)
        job['returncode'] = returncode
        job['stdout'] = stdout
        job['stderr'] = stderr
        job['end_time'] = datetime.now()
        self.set_job(job_uuid, job)
        if returncode:
            failed = self.get_global('failed')
            failed.append(job_uuid)
            self.set_global('failed', ongoing)
            stack = [job_uuid]
            while stack:
                uuid = stack.pop(0)
                job = self.job(uuid)
                job['returncode'] = 'Not started because de dependent job failed'
                self.set_job(uuid, job)
                waiting = self.get_global('waiting')
                waiting.remove(uuid)
                self.set_global('waiting', waiting)
                failed = self.get_global('failed')
                failed.append(uuid)
                self.set_global('failed', failed)
                stack.extend(job.get('waited_by', []))
        else:
            done = self.get_global('done')
            done.append(job_uuid)
            self.set_global('done', done)
            done = set(done)
            for waiting_uuid in job.get('waited_by', []):
                waiting_job = self.job(waiting_uuid)
                for waited in waiting_job.get('wait_for', []):
                    if waited not in done:
                        break
                else:
                    waiting = self.get_global('waiting')
                    waiting.remove(waiting_uuid)
                    self.set_global('waiting', waiting)
                    ready = self.get_global('ready')
                    ready.append(waiting_uuid)
                    self.set_global('ready', ready)
        if self.ongoing or self.ready:
            return False
        else:
            if self.failed:
                self.status = 'error'
                self.error = 'Some jobs failed'
            else:
                self.status = 'ended'
            return True
