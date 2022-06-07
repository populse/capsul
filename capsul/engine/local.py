# -*- coding: utf-8 -*-
from datetime import datetime
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

from soma.controller import Controller
from soma.undefined import undefined

from capsul.application import Capsul

from ..api import Pipeline, Process
from ..pipeline.process_iteration import ProcessIteration
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..execution_context import ExecutionContext, ExecutionDatabase, CapsulWorkflow
      
class LocalEngine:
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
        for module_name, requirements in self.executable_requirements(executable).items():
            module_configs = getattr(self.config, module_name, {})
            if not isinstance(module_configs, Controller):
                raise ValueError(f'Unknown requirement: "{module_name}"')
            valid_configs = []
            for module_field in module_configs.fields():
                module_config = getattr(module_configs, module_field.name)
                if module_config.is_valid_config(requirements):
                    valid_configs.append(module_config)
            if not valid_configs:
                raise RuntimeError(
                    f'Execution environment "{self.label}" has no '
                    f'valid configuration for module {module_name}')
            if len(valid_configs) > 1:
                raise RuntimeError(
                    f'Execution environment "{self.label}" has '
                    f'{len(valid_configs)} possible configurations for '
                    f'module {module_name}')
            execution_context.add_field(module_name, type_=ModuleConfiguration)
            setattr(execution_context, module_name,  valid_configs[0])
        return execution_context

    def start(self, executable, **kwargs):
        db_file = tempfile.NamedTemporaryFile(prefix='capsul_local_engine_', delete=False)
        try:
            for name, value in kwargs.items():
                setattr(executable, name, value)
            execution_context = self.execution_context(executable)
            workflow = CapsulWorkflow(executable)
            # from pprint import pprint
            # print('!start!')
            # pprint(workflow.parameters.proxy_values)
            # pprint(workflow.parameters.content)
            # pprint(workflow.parameters.no_proxy())
            with ExecutionDatabase('sqlite:\\' + db_file.name) as db:
                db.execution_context = execution_context
                db.executable = executable
                db.save_workflow(workflow)
                db.start_time =  datetime.now()
                db.status = 'ready'
            p = subprocess.Popen(
                [sys.executable, '-m', 'capsul.engine.local', db_file.name],
            )
            p.wait()
            return db_file.name
        except Exception:
            db_file.close()
            os.remove(db_file.name)
            raise

    def status(self, execution_id, keys=['status', 'start_time']):
        if isinstance(keys, str):
            keys = [keys]
        with ExecutionDatabase(execution_id) as db:
            status = db.session['status'].document('', fields=keys)
        filename = execution_id + '.stdouterr'
        if os.path.exists(filename):
            with open(filename) as f:
                output = f.read()
            status['engine_output'] = output
        return status
    
    def wait(self, execution_id, timeout=None):
        start = time.time()
        status = self.status(execution_id, keys='status')
        if status['status'] == 'submited':
            for i in range(50):
                time.sleep(0.1)
                status = self.status(execution_id, keys='status')
                if status['status'] != 'submited':
                    break
            else:
                raise SystemError('executable too slow to start')
        status = self.status(execution_id, keys='status')
        while status['status'] == 'running':
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError('Process execution timeout')
            time.sleep(0.1)
            status = self.status(execution_id, keys='status')

    def raise_for_status(self, status):
        output = status.get('engine_output')
        if output is not None:
            output = output.strip()
        if output:
            print('----- local engine output -----')
            print(output)
            print('-------------------------------')
        error = status.get('error')
        if error:
            detail = status.get('error_detail')
            if detail:
                raise RuntimeError(f'{error}\n\n{detail}')
            else:
                raise RuntimeError(error)

    def update_executable(self, executable, execution_id):
        with ExecutionDatabase(execution_id) as db:
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
            while stack:
                node, parameters = stack.pop(0)
                for field in node.user_fields():
                    value = parameters.get(field.name, undefined)
                    if value is not undefined:
                        value = parameters.no_proxy(value)
                        if value is None:
                            value = undefined
                        # print('!update_executable!', node.full_name, field.name, '<-', value)
                        setattr(node, field.name, value)
                    # else:
                    #     print('!update_executable! ignore', node.full_name, field.name, value)
                if isinstance(node, Pipeline):
                    stack.extend((n, parameters[n.name]) for n in node.all_nodes() if n is not node and isinstance(n, Process))
        finally:
            if enable_parameter_links is not None:
                executable.enable_parameter_links = enable_parameter_links
    
    def run(self, executable, timeout=None, **kwargs):
        execution_id = self.start(executable, **kwargs)
        try:
            self.wait(execution_id, timeout=timeout)
            status = self.status(execution_id, keys=['status', 'error', 'error_detail', 'debug_messages', 'output_parameters'])
            self.print_debug_messages(status)
            self.raise_for_status(status)
            self.update_executable(executable, execution_id)
        finally:
            self.dispose(execution_id)
        return status

    def dispose(self, execution_id):
        std = f'{execution_id}.stdouterr'
        if os.path.exists(std):
            os.remove(std)
        if os.path.exists(execution_id):
            os.remove(execution_id)

    def print_debug_messages(self, status):
        for debug in status.get('debug_messages', []):
            print('!', *debug)

    
if __name__ == '__main__':
    import contextlib

    if len(sys.argv) != 2:
        raise ValueError('This command must be called with a single '
            'parameter containing a capsul execution database file name')
    output = open(sys.argv[1] + '.stdouterr', 'w')
    contextlib.redirect_stdout(output)
    contextlib.redirect_stderr(output)
    database = ExecutionDatabase(sys.argv[1])
    with database as db:
        db.status = 'submited'

    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly wait for.
    if sys.platform.startswith('win'):
        pid = 0
    else:
        pid = os.fork()
    if pid == 0:
        if not sys.platform.startswith('win'):
            os.setsid()
        # Create temporary directory
        tmp = tempfile.mkdtemp(prefix='capsul_local_engine_')
        db_update = {}
        try:
            # create environment variables for jobs
            env = os.environ.copy()
            env.update({
                'CAPSUL_DATABASE': sys.argv[1],
                'CAPSUL_TMP': tmp,
            })
            # Read jobs workflow
            with database as db:
                db.status = 'running'
                db.start_time = datetime.now()
                jobs = {}
                ready = set()
                waiting = set()
                done = set()
                for job in db.jobs():
                    jobs[job['uuid']] = job
                    if job['wait_for']:
                        waiting.add(job['uuid'])
                    else:
                        ready.add(job['uuid'])
            
            # Execute jobs sequentially
            while ready:
                job_uuid = ready.pop()
                job = jobs[job_uuid]
                command = job['command']
                if command is not None:
                    subprocess.check_call(command, env=env, stdout=sys.stdout, 
                        stderr=subprocess.STDOUT,)
                done.add(job_uuid)
                for waiting_uuid in list(waiting):
                    waiting_job = jobs[waiting_uuid]
                    if not any(i for i in waiting_job['wait_for'] if i not in done):
                        waiting.remove(waiting_uuid)
                        ready.add(waiting_uuid)
        except Exception as e:
            db_update['error'] = f'{e}'
            db_update['error_detail'] = f'{traceback.format_exc()}'
        finally:
            shutil.rmtree(tmp)
            db_update['status'] = 'ended'
            db_update['end_time'] = datetime.now()
            with database as db:
                db.session['status'].update_document('', db_update)
