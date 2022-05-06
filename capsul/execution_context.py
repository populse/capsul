# -*- coding: utf-8 -*-

from datetime import datetime
from uuid import uuid4

from populse_db import Database
from soma.controller import Controller, OpenKeyDictController

from .application import Capsul
from .dataset import Dataset


class ExecutionContext(Controller):
    python_modules: list[str]
    dataset: OpenKeyDictController[Dataset]

    def __init__(self, config=None, executable=None):
        if config:
            python_modules = config.get('python_modules', ())
            for m in python_modules:
                __import__(m)
        super().__init__()
        self.dataset = OpenKeyDictController[Dataset]()
        if config is not None:
            self.import_dict(config)
        self.executable = executable

class ExecutionDatabase:
    def __init__(self, path):
        self.db = Database(path)
        self.collection = None
    
    def __enter__(self):
        session = self.session = self.db.__enter__()
        if not session.has_collection('status'):
            session.add_collection('status')
            status = session['status']
            status.add_field('status', str)
            status.add_field('execution_context', dict)
            status.add_field('start_time', datetime)
            status.add_field('end_time', datetime)
            # status.add_field('debug_messages', list[str])
            status.add_field('error', str)
            status.add_field('error_detail', str)
            status.add_field('executable', dict)
            status[''] = {}

            session.add_collection('jobs', 'uuid')
            jobs = session['jobs']
            jobs.add_field('command', list[str])
            jobs.add_field('wait_for', list[str])
            # status.add_field('start_time', datetime)
            # status.add_field('end_time', datetime)
            # status.add_field('exit_status', int)

            session.add_collection('processes', 'uuid')
            processes = session['processes']
            processes.add_field('full_name', str)
            processes.add_field('json', dict)
            processes.add_field('jobs', list[str])
            processes.add_field('output_parameters', dict)
        return self
    
    def __exit__(self, *args):
        self.db.__exit__(*args)
        self.session = None
        
    @property
    def status(self):
        row = self.session['status'].document('', fields=['status'], as_list=True)
        if row is not None:
            return row[0]

    @status.setter
    def status(self, status):
        self.session['status'].update_document('', {'status': status})

    @property
    def execution_context(self):
        row = self.session['status'].document('', fields=['execution_context'], as_list=True)
        if row is not None:
            return ExecutionContext(config=row[0])

    @execution_context.setter
    def execution_context(self, execution_context):
        self.session['status'].update_document('', {'execution_context': execution_context.json()})
    
    @property
    def executable(self):
        row = self.session['status'].document('', fields=['executable'], as_list=True)
        if row is not None:
            return Capsul.executable(row[0])

    @executable.setter
    def executable(self, executable):
        self.session['status'].update_document('', {'executable': executable.json()})
    
    @property
    def start_time(self):
        row = self.session['status'].document('', fields=['start_time'], as_list=True)
        if row is not None:
            return row[0]

    @start_time.setter
    def start_time(self, value):
        self.session['status'].update_document('', {'start_time': value})

    def process(self, process_uuid):
        row = self.session['processes'].document(process_uuid, fields=['json'], as_list=True)
        if row is not None:
            return Capsul.executable(row[0])
    
    def update_process(self, process_uuid, **kwargs):
        self.session['processes'].update_document(process_uuid,
            kwargs)
    
    def add_process(self, uuid, process, jobs):
        if jobs is not None and not isinstance(jobs, list):
            jobs = list(jobs)
        self.session['processes'][uuid] = {
            'full_name': process.full_name,
            'json': process.json(),
            'jobs': jobs,
        }
    
    def add_process_job(self, process_uuid, iteration_index=None):
        job_uuid = str(uuid4())
        command = ['python', '-m', 'capsul.run', 'process', process_uuid, str(iteration_index)]
        self.session['jobs'][job_uuid] = {
            'command': command,
        }
        return job_uuid
    
    def add_job_chronology(self, before_job, after_job):
        row = self.session['jobs'].document(after_job, fields=['wait_for'], as_list=True)
        if row is None:
            raise ValueError(f'No job with uuid {after_job}')
        wait_for = row[0] or []
        wait_for.append(before_job)
        self.session['jobs'].update_document(after_job, {'wait_for': wait_for})

    def jobs(self):
        return self.session['jobs'].documents()
