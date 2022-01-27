import json
import shutil
import subprocess
import sys
import tempfile
import time



class LocalEngine:
    def __init__(self):
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
    
    def start(self, executable):
        self.assert_connected()
        with tempfile.NamedTemporaryFile(dir=self.tmp,suffix='.capsul', mode='w', delete=False) as f:
            j = executable.json()
            j['status'] = 'submited'
            json.dump(j,f)
            f.flush()
            p = subprocess.Popen(
                [sys.executable, '-m', 'capsul.run', f.name],
                 stdout=open(f'{f.name}.stdout', 'wb'),
                 stderr=open(f'{f.name}.stderr', 'wb'),
            )
        return f.name

    def status(self, execution_id):
        self.assert_connected()
        return json.load(open(execution_id))
    
    def wait(self, execution_id):
        self.assert_connected()
        status = self.status(execution_id)
        if status['status'] == 'submited':
            for i in range(6):
                time.sleep(0.5)
                status = self.status(execution_id)
                if status['status'] != 'submited':
                    break
            else:
                raise SystemError('executable too slow to start')
        pid = status.get('pid')
        if pid:
            os.waitpid(pid)

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
        executable.import_json(status['parameters'])

    def run(self, executable):
        execution_id = self.start(executable)
        self.wait(execution_id)
        status = self.status(execution_id)
        self.raise_for_status(status)
        self.update_executable(executable, status)
        return executable