# -*- coding: utf-8 -*-
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from soma.controller import Controller, OpenKeyDictController, Directory
from populse_db import Database

from ..api import Pipeline, Process
from ..pipeline.process_iteration import ProcessIteration
from ..config.configuration import ModuleConfiguration
from ..dataset import Dataset
from ..execution_context import ExecutionContext, ExecutionStatus

        
class LocalEngine:
    def __init__(self, label, config):
        self.label = label
        self.config = config
        self.tmp = None
        self._with_count = 0

    @property
    def connected(self):
        return self.tmp is not None
    
    def connect(self):
        if self.tmp is None:
            self.tmp = tempfile.mkdtemp(prefix='capsul_local_engine')
        # Returnig self is necessary to allow the following statement:
        # with capsul.connect() as capsul_engine:
        return self

    def disconnect(self):
        if self.tmp is not None:
            shutil.rmtree(self.tmp)
            self.tmp = None
    
    def __enter__(self):
        if self._with_count == 0:
            self.connect()
        self._with_count += 1
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._with_count -= 1
        if self._with_count == 0:
            self.disconnect()

    def assert_connected(self):
        if not self.connected:
            raise RuntimeError('Capsul engine must be connected to perform this action')

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
        self.assert_connected()
        for name, value in kwargs.items():
            setattr(executable, name, value)
        execution_context = self.execution_context(executable)
        with tempfile.NamedTemporaryFile(dir=self.tmp,suffix='.capsul', mode='w', delete=False) as f:
            with ExecutionStatus(f.name) as status:
                status.update({
                    'status': 'submited',
                    'executable': executable.json(),
                    'execution_context': execution_context.json(),
                })
            p = subprocess.Popen(
                [sys.executable, '-m', 'capsul.run', f.name],
                start_new_session=True,
                #stdin=subprocess.DEVNULL,
                #stdout=subprocess.DEVNULL,
                #stderr=subprocess.DEVNULL,
            )
            p.wait()
        return f.name

    def status(self, execution_id, keys=None):
        if isinstance(keys, str):
            keys = [keys]
        self.assert_connected()
        with ExecutionStatus(execution_id) as status:
            return status.as_dict(keys)
    
    def wait(self, execution_id):
        self.assert_connected()
        status = self.status(execution_id, keys='status')
        if status['status'] == 'submited':
            for i in range(10):
                time.sleep(0.5)
                status = self.status(execution_id, keys='status')
                if status['status'] != 'submited':
                    break
            else:
                raise SystemError('executable too slow to start')
        while status['status'] == 'running':
            time.sleep(0.5)
            status = self.status(execution_id, keys='status')

    def raise_for_status(self, status):
        self.assert_connected()
        error = status.get('error')
        if error:
            detail = status.get('error_detail')
            if detail:
                raise RuntimeError(f'{error}\n\n{detail}')
            else:
                raise RuntimeError(error)

    def update_executable(self, executable, status):
        executable.import_json(status.get('output_parameters', {}))

    def run(self, executable, **kwargs):
        execution_id = self.start(executable, **kwargs)
        self.wait(execution_id)
        status = self.status(execution_id, keys=['error', 'error_details', 'debug_messages', 'output_parameters'])
        self.print_debug_messages(status)
        self.raise_for_status(status)
        self.update_executable(executable, status)
        return execution_id

    def print_debug_messages(self, status):
        for debug in status.get('debug_messages', []):
            print('!', *debug)
