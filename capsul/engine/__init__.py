# -*- coding: utf-8 -*-
from datetime import datetime
import os
import subprocess
import sys

from soma.controller import Controller

from ..execution_context import CapsulWorkflow, ExecutionContext
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..database import execution_database


def execution_context(engine_label, engine_config, executable):
    execution_context = ExecutionContext(executable=executable)
    python_modules = getattr(engine_config, 'python_modules', ())
    if python_modules:
        execution_context.python_modules = python_modules
    for name, cfg in getattr(engine_config, 'dataset', {}).items():
        setattr(execution_context.dataset, name, Dataset(path=cfg.path, metadata_schema=cfg.metadata_schema))

    req_to_check = execution_context.executable_requirements(executable)
    done_req = []  # record requirements to avoid loops
    valid_configs = {}
    needed_modules = set()

    while req_to_check:
        module_name, requirements = req_to_check.popitem()
        if (module_name, requirements) in done_req:
            continue
        done_req.append((module_name, requirements))
        needed_modules.add(module_name)

        module_configs = getattr(engine_config, module_name, {})
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
                f'Execution environment "{engine_label}" has no '
                f'valid configuration for module {module_name}')
        if len(valid_module_configs) > 1:
            raise RuntimeError(
                f'Execution environment "{engine_label}" has '
                f'{len(valid_configs)} possible configurations for '
                f'module {module_name}')
        # get the single remaining config
        valid_config = next(iter(valid_module_configs.values()))
        execution_context.add_field(module_name, type_=ModuleConfiguration)
        setattr(execution_context, module_name,  valid_config)
    return execution_context

class Engine(Controller):

    def __init__(self, label, config):
        super().__init__()
        self.label = label
        self.config = config

    def __enter__(self):
        self.database = execution_database(self.config.database_url)
        self.workers_id = self.database.new_workers(self)
        workers_command = []
        
        connection_type = getattr(self.config, 'connection_type', None)
        if connection_type == 'ssh':
            host = getattr(self.config, 'host', None)
            if not host:
                raise ValueError('Host is mandatory in configuration for a ssh connection')
            login = getattr(self.config, 'login', None)
            if login:
                host = f'{login}@{host}'
            workers_command += ['ssh', host]
        elif connection_type != None:
            raise ValueError(f'Unsuported engine connection type: {connection_type}')
        
        casa_dir = getattr(self.config, 'casa_dir', None)
        if casa_dir:
            workers_command.append(f'{casa_dir}/bin/bv')

        workers_command += ['python', '-m', f'capsul.engine.{self.config.workers_type}', 
            self.database.url, self.workers_id]
        env = os.environ.copy()
        env['CAPSUL_ENGINE_CONFIG'] = str(self.config.json())
        try:
            subprocess.run(
                workers_command,
                capture_output=False,
                check=True,
                env=env
            )
            self.database.wait_for_workers(self.workers_id, timeout=10)
        except Exception as e:
            quote = lambda x: f"'{x}'"
            raise RuntimeError(f'Command failed: {" ".join(quote(i) for i in workers_command)}') from e
        return self
       
    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.database.dispose_workers(self.workers_id)
        self.database.close()
        del self.database
    
    def execution_context(self, executable):
        return execution_context(self.label, self.config, executable)

    def start(self, executable, debug=False, **kwargs):
        for name, value in kwargs.items():
            setattr(executable, name, value)
        econtext = execution_context(self.label, self.config, executable)
        workflow = CapsulWorkflow(executable, debug=debug)
        # from pprint import pprint
        # print('!start!', flush=True)
        # pprint(workflow.jobs)
        # pprint(workflow.parameters.proxy_values)
        # pprint(workflow.parameters.content)
        # pprint(workflow.parameters.no_proxy())
        # print('----')
        # pprint(workflow.jobs)
        execution_id = self.database.new_execution(executable, self.workers_id, econtext, workflow, start_time=datetime.now())
        return execution_id


    def status(self, execution_id):
        return self.database.status(execution_id)
    

    def wait(self, execution_id, *args, **kwargs):
        self.database.wait(execution_id, *args, **kwargs)


    def raise_for_status(self, *args, **kwargs):
        self.database.raise_for_status(*args, **kwargs)


    def execution_report(self, *args, **kwargs):
        return self.database.execution_report(*args, **kwargs)


    def print_execution_report(self, *args, **kwargs):
        self.database.print_execution_report(*args, **kwargs)

    def update_executable(self, *args, **kwargs):
        self.database.update_executable(*args, **kwargs)


    def dispose(self, *args, **kwargs):
        self.database.dispose(*args, **kwargs)


    def run(self, executable, timeout=None, print_report=False, debug=False, **kwargs):
        execution_id = self.start(executable, debug=debug, **kwargs)
        try:
            try:
                self.wait(execution_id, timeout=timeout)
            except TimeoutError:
                self.print_execution_report(self.execution_report(execution_id), sys.stderr)
                raise
            status = self.status(execution_id)
            self.raise_for_status(execution_id)
            if print_report:
                self.print_execution_report(self.execution_report(execution_id), file=sys.stdout)
            self.update_executable(executable, execution_id)
        finally:
            self.dispose(execution_id)
        return status

class Workers(Controller):
    def __init__(self, engine_label, engine_config, database):
        self.engine_label = engine_label
        self.engine_config = engine_config
        self.database = database

    
