# -*- coding: utf-8 -*-

import time
import importlib
import os

from soma.controller import Controller

from ..execution_context import ExecutionContext
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

    def start(self, executable, **kwargs):
        raise NotImplementedError(
            'start must be implemented in Engine subclasses.')

    def status(self, execution_id, keys=['status', 'start_time']):
        raise NotImplementedError(
            'status must be implemented in Engine subclasses.')

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
        raise NotImplementedError(
            'update_executable must be implemented in Engine subclasses.')

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
