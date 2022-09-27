# -*- coding: utf-8 -*-
from datetime import datetime
import importlib
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
        workers_type = self.config.workers_type
        try:
            workers_module = importlib.import_module(
                f'capsul.engine.{workers_type}')
        except ImportError:
            raise ValueError(f'engine type {workers_type} is not known.')
        self.workers_class = getattr(workers_module, f'{workers_type.capitalize()}Workers')

    def __enter__(self):
        self.database = execution_database(self.config.database_url)
        self.workers = self.workers_class(self.label, self.config, self.database)
        return self.workers

    def __exit__(self, exception_type, exception_value, exception_traceback):
        del self.workers
        self.database.close()
        del self.database
    
    def execution_context(self, executable):
        return execution_context(self.label, self.config, executable)


class Workers(Controller):
    def __init__(self, engine_label, engine_config, database):
        self.engine_label = engine_label
        self.engine_config = engine_config
        self.database = database

    def start(self, executable, **kwargs):
        for name, value in kwargs.items():
            setattr(executable, name, value)
        econtext = execution_context(self.engine_label, self.engine_config, executable)
        workflow = CapsulWorkflow(executable)
        # from pprint import pprint
        # print('!start!', flush=True)
        # pprint(workflow.jobs)
        # pprint(workflow.parameters.proxy_values)
        # pprint(workflow.parameters.content)
        # pprint(workflow.parameters.no_proxy())
        # print('----')
        # pprint(workflow.jobs)
        execution_id = self.database.new_execution(executable, econtext, workflow, start_time=datetime.now())
        self._start(execution_id)
        return execution_id

    def _start(self, execution_id):
        raise NotImplementedError(
            '_start must be implemented in Workers subclasses.')

    def debug_info(self, execution_id):
        raise NotImplementedError(
            'debug_info must be implemented in Workers subclasses.')

    def status(self, execution_id):
        return self.database.status(execution_id)
    
    def wait(self, *args, **kwargs):
        self.database.wait(*args, **kwargs)

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

    def run(self, executable, timeout=None, print_report=False, **kwargs):
        execution_id = self.start(executable, **kwargs)
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
    
