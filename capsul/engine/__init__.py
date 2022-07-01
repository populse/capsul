from datetime import datetime
import importlib
import os
import shutil
import tempfile
import time

from soma.controller import Controller
from soma.undefined import undefined

from ..execution_context import CapsulWorkflow, ExecutionContext
from ..pipeline.process_iteration import ProcessIteration
from ..api import Pipeline, Process
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset


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

    def database(self, execution_id):
        raise NotImplementedError(
            'database must be implemented in Engine subclasses.')

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
        execution_id = tempfile.mkdtemp(prefix='capsul_local_engine_')
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
            # print('----')
            # pprint(workflow.jobs)
            database = self.database(execution_id)
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
        with self.database(execution_id) as db:
            status = db.status
        return status
    
    def engine_output(self, execution_id):
        with self.database(execution_id) as db:
            engine_output = db.engine_output
        return engine_output

    def error(self, execution_id):
        with self.database(execution_id) as db:
            error = db.error
        return error
    
    def error_detail(self, execution_id):
        with self.database(execution_id) as db:
            error_detail = db.error_detail
        return error_detail

    def wait(self, execution_id, timeout=None):
        start = time.time()
        status = self.status(execution_id)
        if status == 'submited':
            for i in range(50):
                time.sleep(0.1)
                status = self.status(execution_id)
                if status != 'submited':
                    break
            else:
                raise SystemError('executable too slow to start')
        status = self.status(execution_id)
        while status == 'running':
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError('Process execution timeout')
            time.sleep(0.1)
            status = self.status(execution_id)

    def raise_for_status(self, execution_id):
        output = self.engine_output(execution_id)
        if output is not None:
            output = output.strip()
        if output:
            print('----- local engine output -----')
            print(output)
            print('-------------------------------')
        # from pprint import pprint
        # with self.database(execution_id) as db:
        #     print('!waiting!', list(db.waiting))
        #     print('!ready!', list(db.ready))
        #     print('!ongoing!', list(db.ongoing))
        #     print('!done!', list(db.done))
        #     print('!failed!', list(db.failed))
        #     for job in db.jobs():
        #         pprint(job)
        #         print('-'*60)
        error = self.error(execution_id)
        if error:
            detail = self.error_detail(execution_id)
            if detail:
                raise RuntimeError(f'{error}\n\n{detail}')
            else:
                raise RuntimeError(error)

    def update_executable(self, executable, execution_id):
        with self.database(execution_id) as db:
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
            self.update_executable(executable, execution_id)
        finally:
            self.dispose(execution_id)
        return status

    def dispose(self, execution_id):
        self._dispose(execution_id)
        database = self.database(execution_id)
        database.release_server()
        if os.path.exists(execution_id):
            shutil.rmtree(execution_id)

    def _dispose(self, execution_id):
        raise NotImplementedError(
            '_dispose must be implemented in Engine subclasses.')
