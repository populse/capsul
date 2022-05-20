# -*- coding: utf-8 -*-

from datetime import datetime
import json
from uuid import uuid4
from typing import Union

from populse_db import Database
from soma.controller import Controller, OpenKeyDictController
from soma.api import DictWithProxy

from .application import Capsul, executable
from .dataset import Dataset
from .pipeline.pipeline import Process, Pipeline
from .pipeline.process_iteration import ProcessIteration

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
            jobs.add_field('process', dict)
            jobs.add_field('parameters_location', list[str])

            session.add_collection('workflow', 'uuid')
            workflow = session['workflow']
            workflow.add_field('parameters', dict[str, list])
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

    def save_workflow(self, workflow):
        for job_uuid, job in workflow.jobs.items():
            self.session['jobs'][job_uuid] = job
        self.session['workflow'][''] = {}
        self.workflow_parameters = workflow.parameters

    @property
    def workflow_parameters(self):
        row = self.session['workflow'].document('', fields=['parameters'], as_list=True)
        if row is not None:
            return DictWithProxy.from_json(row[0])
        return None
    
    @workflow_parameters.setter
    def workflow_parameters(self, parameters):
        self.session['workflow'].update_document('', {'parameters': parameters.json()})

    def jobs(self):
        return self.session['jobs'].documents()

class CapsulWorkflow(Controller):
    parameters: DictWithProxy
    jobs: dict[str, list]
    chronology: dict[str, list[str]]

    def __init__(self, executable):
        super().__init__()
        self.parameters = DictWithProxy()
        self.jobs = {}
        jobs_per_process = {}
        process_chronology = {}
        processes_proxies = {}
        job_parameters = self._create_jobs(
            executable,
            jobs_per_process,
            processes_proxies,
            process_chronology,
            executable,
            executable,
            [])
        self.parameters.content.update(job_parameters.content)

        # Set jobs chronology based on processes chronology
        for after_process, before_processes in process_chronology.items():
            for after_job in jobs_per_process[after_process]:
                for before_process in before_processes:
                    for before_job in jobs_per_process[before_process]:
                        self.jobs[after_job]['wait_for'].append(before_job)

    def _create_jobs(self,
                     executable,
                     jobs_per_process,
                     processes_proxies,
                     process_chronology,
                     process,
                     parent_executable,
                     parameters_location):
        parameters = self.parameters
        for index in parameters_location:
            if index.isnumeric():
                index = int(index)
            parameters = parameters[index]
        if isinstance(process, Pipeline):
            pipeline_parameters = DictWithProxy(_proxy_values=parameters.proxy_values)
            nodes_parameters = DictWithProxy(_proxy_values=parameters.proxy_values)
            for node_name, node in process.nodes.items():
                if node is process or not node.activated or not isinstance(node, Process):
                    continue
                parameters[node_name] = {}
                job_parameters = self._create_jobs(
                    executable,
                    jobs_per_process,
                    processes_proxies,
                    process_chronology,
                    node,
                    node,
                    parameters_location + [node_name])
                nodes_parameters.content[node_name] = job_parameters.content
            for field in process.user_fields():
                for dest_node, plug_name in executable.get_linked_items(process, 
                                                                        field.name,
                                                                        in_sub_pipelines=False):
                    pipeline_parameters.content[field.name] = nodes_parameters.content[dest_node.name][plug_name]
                    break
            return pipeline_parameters
        elif isinstance(process, ProcessIteration):
            parameters['_iterations'] = []
            iteration_parameters = DictWithProxy(_proxy_values=parameters.proxy_values)
            iteration_index = 0
            for inner_process in process.iterate_over_process_parmeters():
                parameters['_iterations'].append({})
                job_parameters = self._create_jobs(
                    executable,
                    jobs_per_process,
                    processes_proxies,
                    process_chronology,
                    inner_process,
                    process, 
                    parameters_location + ['_iterations', str(iteration_index)])
                for k, v in job_parameters.content.items():
                    if k in process.iterative_parameters:
                        iteration_parameters.content.setdefault(k, []).append(v)
                    else:
                        iteration_parameters.content.setdefault(k, v)
                iteration_index += 1
            if isinstance(executable, Pipeline):
                for field in process.user_fields():
                    if field.is_output():
                        for dest_node, plug_name in executable.get_linked_items(process, field.name):
                            process_chronology.setdefault(dest_node.uuid, set()).add(process.uuid)
            return iteration_parameters
        elif isinstance(process, Process):
            job_uuid = str(uuid4())
            self.jobs[job_uuid] = {
                'command': ['python', '-m', 'capsul.run', 'process', job_uuid],
                'wait_for': [],
                'process': process.json(include_parameters=False),
                'parameters_location': parameters_location
            }
            jobs_per_process.setdefault(parent_executable.uuid, set()).add(job_uuid)
            for field in process.user_fields():
                value = getattr(process, field.name, None)
                proxy = parameters.proxy(executable.json_value(value))
                parameters[field.name] = proxy
                if field.is_output() and isinstance(executable, Pipeline):
                    for dest_node, plug_name in executable.get_linked_items(process, field.name):
                        process_chronology.setdefault(dest_node.uuid, set()).add(process.uuid)
            return parameters
