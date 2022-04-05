# -*- coding: utf-8 -*-
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import time

from capsul.api import Pipeline, Process
from capsul.config import EngineConfiguration

class LocalEngine:
    def __init__(self, label, config=None):
        self.label = label
        if config is None:
            self.config = EngineConfiguration()
        elif isinstance(config, EngineConfiguration):
            self.config = config
        else:
            raise TypeError(
                'config must be an instance of EngineConfiguration')
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
        if isinstance(executable, Pipeline):
            for node in executable.all_nodes():
                if isinstance(node, Process) and node.activated:
                    result.update(getattr(node, 'requirements', {}))
        result.update(getattr(executable, 'requirements', {}))
        return result

    def modules_config(self, executable):
        result = {}
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
            result[module_name] = valid_configs[0].asdict()
        return result

    def start(self, executable, **kwargs):
        self.assert_connected()
        for name, value in kwargs.items():
            setattr(executable, name, value)
        capsul = {
            'status': 'submited',
            'executable': executable.json(),
            'config': {
                'modules': self.modules_config(executable)
            }
        }
        with tempfile.NamedTemporaryFile(dir=self.tmp,suffix='.capsul', mode='w', delete=False) as f:
            json.dump(capsul,f)
            f.flush()
            p = subprocess.Popen(
                [sys.executable, '-m', 'capsul.run', f.name],
                start_new_session=True,
                #stdin=subprocess.DEVNULL,
                #stdout=subprocess.DEVNULL,
                #stderr=subprocess.DEVNULL,
            )
            p.wait()
        return f.name

    def status(self, execution_id):
        self.assert_connected()
        with open(execution_id) as f:
            return json.load(f)
    
    def wait(self, execution_id):
        self.assert_connected()
        status = self.status(execution_id)
        if status['status'] == 'submited':
            for i in range(10):
                time.sleep(0.5)
                status = self.status(execution_id)
                if status['status'] != 'submited':
                    break
            else:
                raise SystemError('executable too slow to start')
        while status['status'] == 'running':
            time.sleep(0.5)
            status = self.status(execution_id)

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
        executable.import_json(status.get('executable', {}).get('parameters', {}))

    def run(self, executable, **kwargs):
        execution_id = self.start(executable, **kwargs)
        self.wait(execution_id)
        status = self.status(execution_id)
        self.print_debug_messages(status)
        self.raise_for_status(status)
        self.update_executable(executable, status)
        return execution_id

    def print_debug_messages(self, status):
        for debug in status.get('debug_messages', []):
            print('!', *debug)
