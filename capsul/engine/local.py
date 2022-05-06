from datetime import datetime
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from uuid import uuid4

from soma.undefined import undefined

from ..api import Pipeline, Process
from ..pipeline.process_iteration import ProcessIteration
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..execution_context import ExecutionContext, ExecutionDatabase

        
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
        set_temporary_file_names = getattr(executable, 'set_temporary_file_names', None)
        if set_temporary_file_names is not None:
            set_temporary_file_names()
        db_file = tempfile.NamedTemporaryFile(prefix='capsul_local_engine_', delete=False)
        try:
            for name, value in kwargs.items():
                setattr(executable, name, value)
            execution_context = self.execution_context(executable)
            with ExecutionDatabase(db_file.name) as db:
                db.execution_context = execution_context
                db.executable = executable
                db.start_time =  datetime.now()
                self.create_jobs(executable, db)
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
            for p in db.session['processes']:
                output_parameters = p.get('output_parameters')
                if output_parameters:
                    if isinstance(executable, Pipeline):
                        full_name = p['full_name']
                        stack = full_name.split('.')
                        node = executable
                        while stack:
                            node = node.nodes[stack.pop(0)]
                        for n, v in output_parameters.items():
                            setattr(node, n ,v)
                            executable.dispatch_value(node, n, v)
                    else:
                        for n, v in output_parameters.items():
                            setattr(executable, n, v)
    
    def run(self, executable, timeout=None, **kwargs):
        execution_id = self.start(executable, **kwargs)
        try:
            self.wait(execution_id, timeout=timeout)
            status = self.status(execution_id, keys=['error', 'error_detail', 'debug_messages', 'output_parameters'])
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

    def create_jobs(self, executable, execution_database):
        nodes = set()
        chronology = {}
        if isinstance(executable, Pipeline):
            # Retrieve the complete list of active process nodes (going
            # into sub-pipelines)
            stack = [node for name, node in executable.nodes.items() if name]
            while stack:
                node = stack.pop(0)
                if not node.activated:
                    continue
                if isinstance(node, Pipeline):
                    stack.extend(node for name, node in node.nodes.items() if name)
                elif isinstance(node, Process):
                    nodes.add(node)
            
            # Build nodes chronology (dependencies between nodes). chronology 
            # is a dict whose keys are nodes and corresponding value is a set
            # of nodes that must be executed before.
            for first_node in nodes:
                for field in first_node.fields():
                    if field.is_output():
                        for second_node, plug_name in executable.get_linked_items(first_node, field.name):
                            chronology.setdefault(second_node, set()).add(first_node)
        else:
            nodes.add(executable)
            
        # Creates the jobs for each process node
        jobs_per_node = {}
        for node in nodes:
            process_uuid = str(uuid4())
            if isinstance(node, ProcessIteration):
                size = node.iteration_size()
                if size:
                    list_outputs = []
                    for field in node.user_fields():
                        if field.is_output() and field.name in node.iterative_parameters:
                            list_outputs.append(field.name)
                            value = getattr(node, field.name, None)
                            if value is None:
                                setattr(node, field.name, [field.target_field.valid_value()] * size)
                            elif len(value) < size:
                                value += [field.target_field.valid_value()] * (size - len(value))
                    iteration_index = 0
                    for process in node.iterate_over_process_parmeters():
                        job_uuid = execution_database.add_process_job(
                            process_uuid=process_uuid,
                            iteration_index=iteration_index)
                        jobs_per_node.setdefault(node, set()).add(job_uuid)
                        iteration_index += 1                        
            else:
                job_uuid = execution_database.add_process_job(
                    process_uuid=process_uuid,
                    iteration_index=None)
                jobs_per_node.setdefault(node, set()).add(job_uuid)
            process_uuid = execution_database.add_process(process_uuid, node, jobs_per_node[node])

        # Set jobs chronology based on nodes chronology
        for after_node, before_nodes in chronology.items():
            for after_job in jobs_per_node[after_node]:
                for before_node in before_nodes:
                    for before_job in jobs_per_node[before_node]:
                        execution_database.add_job_chronology(before_job, after_job)
        
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
