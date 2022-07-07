# -*- coding: utf-8 -*-
from datetime import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

from capsul.database import execution_database


from . import Workers

      
class BuiltinWorkers(Workers): 
    def _start(self, execution_id):
        subprocess.run(
            [sys.executable, '-m', 'capsul.engine.builtin', self.database.url, execution_id],
            capture_output=False, check=True
        )
        
    def close(self):
        pass

    def _debug_info(self, execution_id):
        return {}
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('This command must be called with two '
            'parameters: a database URL and an execution_id')
    database_url = sys.argv[1]
    execution_id = sys.argv[2]

    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly waited for.
    if sys.platform.startswith('win'):
        pid = 0
    else:
        pid = os.fork()
    if pid == 0:
        if not sys.platform.startswith('win'):
            os.setsid()
        tmp = tempfile.mkdtemp(prefix='caspul_builtin_')
        try:
            database = execution_database(database_url)
            try:
                env = os.environ.copy()
                env['CAPSUL_DATABASE'] = database_url
                env['CAPSUL_TMP'] = tmp
                env['CAPSUL_EXECUTION_ID'] = execution_id
                job = database.start_next_job(execution_id, start_time=datetime.now())
                while job is not None:
                    command = job['command']
                    if command is not None:
                        result = subprocess.run(command, env=env, capture_output=True)
                        returncode = result.returncode
                        stdout = result.stdout.decode()
                        stderr = result.stderr.decode()
                    else:
                        returncode = stdout = stderr = None
                    command = job['command']
                    all_done = database.job_finished(execution_id, job['uuid'], 
                        end_time=datetime.now(),
                        returncode=returncode,
                        stdout=stdout,
                        stderr=stderr)
                    if all_done:
                        break
                    job = database.start_next_job(execution_id, start_time=datetime.now())
            except Exception as e:
                database.set_error(execution_id,
                    error=f'Builtin engine loop failure: {e}',
                    error_detail=f'{traceback.format_exc()}'
                )
                raise
        finally:
            shutil.rmtree(tmp)