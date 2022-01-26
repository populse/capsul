import json
import shutil
import subprocess
import sys
import tempfile



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
        with tempfile.NamedTemporaryFile(dir=self.tmp,suffix='.capsul', mode='w') as f:
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
