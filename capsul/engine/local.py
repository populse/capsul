import json
import shutil
import subprocess
import sys
import tempfile
import time



class LocalEngine:
    def __init__(self):
        self.tmp = None
        self.enter_count = 0

    def __enter__(self):
        if self.enter_count == 0:
            self.tmp = tempfile.mkdtemp(prefix='capsul_local_engine')
        self.enter_count += 1
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.enter_count -= 1
        if self.enter_count == 0:
            shutil.rmtree(self.tmp)

    def start(self, executable):
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
        return json.load(open(execution_id))
    
    def wait(self, execution_id):
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
        error = status.get('error')
        if error:
            detail = status.get('error_detail')
            if detail:
                raise RuntimeError(f'{error}\n\n{detail}')
            else:
                raise RuntimeError(error)