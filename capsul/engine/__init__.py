# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
import subprocess
import sys

from soma.controller import Controller

from ..execution_context import CapsulWorkflow, ExecutionContext
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..database import engine_database


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

class Engine:

    def __init__(self, label, config, databases_config):
        super().__init__()
        self.label = label
        self.config = config
        self.database_config = databases_config[self.config.database]
        self.database = engine_database(self.database_config)
        self.nested_context = 0

    def __enter__(self):
        if self.nested_context == 0:
            # Connect to the database
            self.database.__enter__()
            # Connect to the engine in the database. Adds the engine in
            # the database if it does not exist.
            self.engine_id = self.database.get_or_create_engine(self)
        self.nested_context += 1
        return self

    def engine_status(self):
        result = {
            'label': self.label,
        }
        result['database_connected'] = self.database.is_connected
        if result['database_connected']:
            result['database_ready'] = True
            database = self.database
        else:
            result['database_ready'] = self.database.is_ready
            if result['database_ready']:
                database = engine_database(self.database_config)
            else:
                database = None
        if database:
            with database:
                engine_id = result['engine_id'] = database.engine_id(self.label)
                if engine_id:
                    result['workers_count'] = database.workers_count(engine_id)
                    result['connections'] = database.engine_connections(engine_id)
        return result


    def start_workers(self):
        requested = self.config.start_workers.get('count', 0)
        start_count = max(0, requested - self.database.workers_count(self.engine_id))
        if start_count:
            for i in range(start_count):
                workers_command = self.database.workers_command(self.engine_id)
                try:
                    subprocess.run(
                        workers_command,
                        capture_output=False,
                        check=True,
                    )
                except Exception as e:
                    quote = lambda x: f"'{x}'"
                    raise RuntimeError(f'Command failed: {" ".join(quote(i) for i in workers_command)}') from e
        
       
    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.nested_context -= 1
        if self.nested_context == 0:
            if 'CAPSUL_DEBUG' not in os.environ:
                self.database.dispose_engine(self.engine_id)
            self.database.__exit__(exception_type, exception_value, exception_traceback)
            del self.engine_id
    
    def execution_context(self, executable):
        return execution_context(self.label, self.config, executable)

    def start(self, executable, debug=False, **kwargs):
        # Starts workers if necessary
        self.start_workers()
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
        execution_id = self.database.new_execution(executable, self.engine_id, econtext, workflow, start_time=datetime.now())
        return execution_id


    def executions_summary(self):
        with self:
            return self.database.executions_summary(self.engine_id)
    

    def status(self, execution_id):
        return self.database.status(self.engine_id, execution_id)
    

    def wait(self, execution_id, *args, **kwargs):
        self.database.wait(self.engine_id, execution_id, *args, **kwargs)


    def raise_for_status(self, *args, **kwargs):
        self.database.raise_for_status(self.engine_id, *args, **kwargs)


    def execution_report(self, *args, **kwargs):
        return self.database.execution_report(self.engine_id, *args, **kwargs)


    def print_execution_report(self, engine_id, *args, **kwargs):
        self.database.print_execution_report(engine_id, *args, **kwargs)

    def update_executable(self, *args, **kwargs):
        self.database.update_executable(self.engine_id, *args, **kwargs)


    def dispose(self, *args, **kwargs):
        self.database.dispose(self.engine_id, *args, **kwargs)


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
            self.update_executable(execution_id, executable)
        finally:
            if 'CAPSUL_DEBUG' not in os.environ:
                self.dispose(execution_id)
        return status

class Workers(Controller):
    def __init__(self, engine_label, engine_config, database):
        self.engine_label = engine_label
        self.engine_config = engine_config
        self.database = database

    
