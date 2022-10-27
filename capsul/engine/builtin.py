# -*- coding: utf-8 -*-
from datetime import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

from capsul.database import execution_database
from capsul.run import run_job

          
if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('This command must be called with two '
            'parameters: a database URL and a workers_id')
    database_url = sys.argv[1]
    workers_id = sys.argv[2]
    database = execution_database(database_url)
    try:
        if database.workers_status(workers_id) is None:
            raise RuntimeError(f'Engine cannot find workers in database: {workers_id}')
    finally:
        database.close()

    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly waited for.
    pid = os.fork()
    if pid == 0:
        os.setsid()
        database = execution_database(database_url)
        try:
            database.workers_started(workers_id)
            execution_id = database.wait_for_execution(workers_id)
            while execution_id:
                tmp = database.create_tmp(execution_id)
                try:
                    # env = os.environ.copy()
                    # env['CAPSUL_DATABASE'] = database_url
                    # env['CAPSUL_EXECUTION_ID'] = execution_id
                    job = database.start_one_job(execution_id, start_time=datetime.now())
                    while job is not None:
                        if not job['disabled']:
                            returncode, stdout, stderr = run_job(
                                database_url,
                                execution_id,
                                job['uuid'],
                                same_python=True,
                                debug=True,
                            )
                            # result = subprocess.run(['python', '-m', 'capsul.run', job['uuid']], env=env, capture_output=True)
                            # returncode = result.returncode
                            # stdout = result.stdout.decode()
                            # stderr = result.stderr.decode()
                        #     import contextlib
                        #     import io
                        #     from capsul.run import run
                        #     stdout = io.StringIO()
                        #     stderr = io.StringIO()
                        #     with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        #         try:
                        #             run(database_url, execution_id, job['uuid'])
                        #             returncode = 0
                        #         except Exception as e:
                        #             print(traceback.format_exc(), file=stderr)
                        #             returncode = 1
                        #     stdout = stdout.getvalue()
                        #     stderr = stderr.getvalue()
                        # else:
                        #     returncode = stdout = stderr = None
                        all_done = database.job_finished(execution_id, job['uuid'], 
                            end_time=datetime.now(),
                            returncode=returncode,
                            stdout=stdout,
                            stderr=stderr)
                        if all_done:
                            break
                        job = database.start_one_job(execution_id, start_time=datetime.now())
                except Exception as e:
                    database.set_error(execution_id,
                        error=f'Builtin engine loop failure: {e}',
                        error_detail=f'{traceback.format_exc()}'
                    )
                    raise
                execution_id = database.wait_for_execution(workers_id)
        finally:
            database.close()
