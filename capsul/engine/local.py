# -*- coding: utf-8 -*-
from datetime import datetime
import os
import subprocess
import sys
import traceback


from ..database import execution_database
from . import Engine

      
class LocalEngine(Engine): 
    database_type = 'populse_db'

    def _start(self, execution_id):
        r = subprocess.run(
            [sys.executable, '-m', 'capsul.engine.local', execution_id],
            capture_output=False, check=True
        )
        
    def _dispose(self, execution_id):
        pass

    
if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise ValueError('This command must be called with a single '
            'parameter containing a capsul execution temporary directory')
    execution_id = sys.argv[1]
    if not os.path.isdir(execution_id):
        raise ValueError(f'"{execution_id} is not an existing directory')

    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly wait for.
    if sys.platform.startswith('win'):
        pid = 0
    else:
        pid = os.fork()
    if pid == 0:
        if not sys.platform.startswith('win'):
            os.setsid()
        tmp = execution_id
        database = execution_database(execution_id)
        try:
            # create environment variables for jobs
            env = os.environ.copy()
            env.update({
                'CAPSUL_TMP': tmp,
            })


            with database as db:
                db.start_time = datetime.now()
                db.status = 'running'
                stack  = list(db.ready)

            while stack:
                job_uuid = stack.pop()
                with database as db:
                    job = db.job(job_uuid)
                    db.move_to_ongoing(job_uuid)
                command = job['command']
                if command is not None:
                    result = subprocess.run(command, env=env, capture_output=True)
                    returncode = result.returncode
                    stdout = result.stdout.decode()
                    stderr = result.stderr.decode()
                else:
                    returncode = stdout = stderr = None
                with database as db:
                    all_done = db.move_to_done(job_uuid, returncode, stdout, stderr)

                if all_done:
                    break
                else:
                    with database as db:
                        stack.extend(db.ready)
        except Exception as e:
            with database as db:
                db.error = f'Local engine loop failure: {e}'
                db.error_detail = f'{traceback.format_exc()}'
        finally:
            with database as db:
                db.status = 'ended'
                db.end_time = datetime.now()
