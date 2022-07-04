# -*- coding: utf-8 -*-
from datetime import datetime
import importlib
import os
import shutil
import sys
import tempfile
import time
from capsul.database import create_execution_database

from soma.controller import Controller
from soma.undefined import undefined

from ..execution_context import CapsulWorkflow, ExecutionContext
from ..pipeline.process_iteration import ProcessIteration
from ..api import Pipeline, Process
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..database import create_execution_database, execution_database

class Engine:
    def __init__(self, label, config):
        self.label = label
        self.config = config

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        pass

    @staticmethod
    def module(module_name):
        return importlib.import_module(f'capsul.config.{module_name}')

    def executable_requirements(self, executable):
        result = {}
        if isinstance(executable, ProcessIteration):
            for process in executable.iterate_over_process_parmeters():
                if process.activated:
                    result.update(self.executable_requirements(process))
        elif isinstance(executable, Pipeline):
            for node in executable.all_nodes():
                if node is not executable and isinstance(node, Process) and node.activated:
                    result.update(self.executable_requirements(node))
        result.update(getattr(executable, 'requirements', {}))
        return result

    def execution_context(self, executable):
        execution_context = ExecutionContext(executable=executable)
        python_modules = getattr(self.config, 'python_modules', ())
        if python_modules:
            execution_context.python_modules = python_modules
        for name, cfg in getattr(self.config, 'dataset', {}).items():
            setattr(execution_context.dataset, name, Dataset(path=cfg.path, metadata_schema=cfg.metadata_schema))

        req_to_check = self.executable_requirements(executable)
        done_req = []  # record requirements to avoid loops
        valid_configs = {}
        needed_modules = set()

        while req_to_check:
            module_name, requirements = req_to_check.popitem()
            if (module_name, requirements) in done_req:
                continue
            done_req.append((module_name, requirements))
            needed_modules.add(module_name)

            module_configs = getattr(self.config, module_name, {})
            if not isinstance(module_configs, Controller):
                raise ValueError(f'Unknown requirement: "{module_name}"')
            for module_field in module_configs.fields():
                module_config = getattr(module_configs, module_field.name)
                added_req = module_config.is_valid_config(requirements)
                if added_req not in (False, None):
                    valid_configs.setdefault(
                        module_name, {})[module_field] = module_config
                    if isinstance(added_req, dict):
                        req_to_check.update(added_req)

        # now check we have only one module for each
        for module_name in needed_modules:
            valid_module_configs = valid_configs.get(module_name)
            if not valid_module_configs:
                raise RuntimeError(
                    f'Execution environment "{self.label}" has no '
                    f'valid configuration for module {module_name}')
            if len(valid_module_configs) > 1:
                raise RuntimeError(
                    f'Execution environment "{self.label}" has '
                    f'{len(valid_configs)} possible configurations for '
                    f'module {module_name}')
            # get the single remaining config
            valid_config = next(iter(valid_module_configs.values()))
            execution_context.add_field(module_name, type_=ModuleConfiguration)
            setattr(execution_context, module_name,  valid_config)
        return execution_context

    @staticmethod
    def filename_from_url(url):
        return url.split('://', 1)[-1]

    def start(self, executable, **kwargs):
        execution_id = tempfile.mkdtemp(prefix='capsul_local_engine_')
        try:
            create_execution_database(execution_id, self.database_type)
            for name, value in kwargs.items():
                setattr(executable, name, value)
            execution_context = self.execution_context(executable)
            workflow = CapsulWorkflow(executable)
            # from pprint import pprint
            # print('!start!')
            # pprint(workflow.parameters.proxy_values)
            # pprint(workflow.parameters.content)
            # pprint(workflow.parameters.no_proxy())
            # print('----')
            # pprint(workflow.jobs)
            database = execution_database(execution_id)
            database.claim_server()
            with database as db:
                db.execution_context = execution_context
                db.executable = executable
                db.save_workflow(workflow)
                db.start_time =  datetime.now()
                db.status = 'ready'
                db.save()

            self._start(execution_id)

            return execution_id
        except Exception:
            shutil.rmtree(execution_id)
            raise

    def _start(self, execution_id):
        raise NotImplementedError(
            '_start must be implemented in Engine subclasses.')

    def status(self, execution_id):
        with execution_database(execution_id) as db:
            status = db.status
        return status
    
    def error(self, execution_id):
        with execution_database(execution_id) as db:
            error = db.error
        return error
    
    def error_detail(self, execution_id):
        with execution_database(execution_id) as db:
            error_detail = db.error_detail
        return error_detail

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
                raise SystemError('executable too slow to start')
        status = self.status(execution_id)
        while status == 'running':
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError('Process execution timeout')
            time.sleep(0.1)
            status = self.status(execution_id)

    def print_execution_report(self, execution_id, file=sys.stderr):
        with execution_database(execution_id) as db:
            executable = db.executable
            status = db.status
            error = db.error
            error_detail = db.error_detail
            start_time = db.start_time
            end_time = db.end_time
            waiting = list(db.waiting)
            ready = set(db.ready)
            ongoing = set(db.ongoing)
            done = set(db.done)
            failed = set(db.failed)
            jobs = []
            for job in db.jobs():
                job_uuid = job['uuid']
                if job_uuid in done:
                    job['status'] = 'done'
                elif job_uuid in failed:
                    job['status'] = 'failed'
                elif job_uuid in ongoing:
                    job['status'] = 'ongoing'
                elif job_uuid in ready:
                    job['status'] = 'ready'
                elif job_uuid in waiting:
                    job['status'] = 'waiting'
                else:
                    job['status'] = 'unknown'
                jobs.append(job)

        print('====================\n'
              '| Execution report |\n'
              '====================\n', file=file)
        print('executable:', executable.definition, file=file)
        print('status:', status, file=file)
        print('start time:', start_time, file=file)
        print('end time:', end_time, file=file)
        if error:
            print('error:', error, file=file)
        if error_detail:
            print('-' * 50, file=file)
            print(error_detail, file=file)
            print('-' * 50, file=file)
        print('\n---------------\n'
              '| Jobs status |\n'
              '---------------\n', file=file)
        now = datetime.now()
        for job in sorted(jobs, key=lambda j: j.get('start_time', now)):
            process_definition = job.get('process', {}).get('definition')
            start_time = job.get('start_time')
            end_time = job.get('end_time')
            pipeline_node = '.'.join(i for i in job['parameters_location'] if i != 'nodes')
            returncode = job.get('returncode')
            status = job['status']
            command = ' '.join(f"'{i}'" for i in job['command'])
            stdout = job.get('stdout')
            stderr = job.get('stderr')

            print('=' * 50, file=file)
            print('process:', process_definition, file=file)
            print('pipeline node:', pipeline_node, file=file)
            print('status:', status, file=file)
            print('returncode:', returncode, file=file)
            print('start time:', start_time, file=file)
            print('end time:', end_time, file=file)
            print('command:', command, file=file)
            if stdout:
                print('---------- standard output ----------', file=file)
                print(stdout, file=file)
            if stderr:
                print('---------- error output ----------', file=file)
                print(stderr, file=file)

    def raise_for_status(self, execution_id):
        error = self.error(execution_id)
        if error:
            self.print_execution_report(execution_id)
            raise RuntimeError(error)

    def update_executable(self, executable, execution_id):
        with execution_database(execution_id) as db:
            parameters = db.workflow_parameters
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

    def run(self, executable, timeout=None, **kwargs):
        execution_id = self.start(executable, **kwargs)
        try:
            self.wait(execution_id, timeout=timeout)
            status = self.status(execution_id)
            self.raise_for_status(execution_id)
            # self.print_execution_report(execution_id)
            self.update_executable(executable, execution_id)
        finally:
            self.dispose(execution_id, retry=0.5)
        return status

    def dispose(self, execution_id, retry=0.5):
        self._dispose(execution_id)
        database = execution_database(execution_id)
        database.release_server()
        t0 = time.time()
        ok = False
        err = None
        while not ok and time.time() - t0 < retry:
            if os.path.exists(execution_id):
                try:
                    shutil.rmtree(execution_id)
                except PermissionError as e:
                    err = str(e)
                    time.sleep(0.02)
                    continue
            ok = True
        if not ok:
            raise PermissionError(err)
    def _dispose(self, execution_id):
        raise NotImplementedError(
            '_dispose must be implemented in Engine subclasses.')
