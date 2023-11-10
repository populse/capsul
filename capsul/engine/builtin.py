from datetime import datetime
import json
import os
import shutil
import sys
import time
import tempfile

from capsul.database import engine_database, ResponseError, ConnectionError
from capsul.run import run_job


def worflow_loop(db_config, engine_id):
    try:
        with engine_database(db_config) as database:
            worker_id = database.worker_started(engine_id)
            # print(f'!worker {worker_id}! started', engine_id)
            try:
                execution_id, job_uuid = database.pop_job(
                    engine_id, start_time=datetime.now()
                )
                while job_uuid is not None:
                    if not job_uuid:
                        # Empty string means no job available yet
                        time.sleep(0.2)
                    elif job_uuid == "start_execution":
                        # print(f'!worker {worker_id}! start', execution_id)
                        # This part is done before the processing of any job
                        tmp = os.path.join(
                            tempfile.gettempdir(), f"capsul_execution_{execution_id}"
                        )
                        os.mkdir(tmp)
                        try:
                            database.start_execution(engine_id, execution_id, tmp)
                        except Exception:
                            os.rmdir(tmp)
                    elif job_uuid == "end_execution":
                        # print(f'!worker {worker_id}! end', execution_id)
                        tmp = database.end_execution(engine_id, execution_id)
                        if tmp and os.path.exists(tmp):
                            shutil.rmtree(tmp)
                    else:
                        return_code, stdout, stderr = run_job(
                            database,
                            engine_id,
                            execution_id,
                            job_uuid,
                            same_python=True,
                            debug=False,
                        )
                        # print(f'!worker {worker_id}! job', execution_id, job_uuid, database.job_finished)
                        database.job_finished(
                            engine_id,
                            execution_id,
                            job_uuid,
                            end_time=datetime.now(),
                            return_code=return_code,
                            stdout=stdout,
                            stderr=stderr,
                        )
                    execution_id, job_uuid = database.pop_job(
                        engine_id, start_time=datetime.now()
                    )
            finally:
                # print(f'!worker {worker_id}! ended' )
                database.worker_ended(engine_id, worker_id)
    except (ResponseError, ConnectionError, TimeoutError):
        print("server has probably shutdown. Exiting.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError(
            "This command must be called with two "
            "parameters: an engine id and a database configuration"
        )
    engine_id = sys.argv[1]
    db_config = json.loads(sys.argv[2])
    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly waited for.
    pid = os.fork()
    if pid == 0:
        os.setsid()
        worflow_loop(db_config, engine_id)

        # import cProfile
        # import tempfile
        # f = tempfile.mktemp(prefix='worker_profile_', dir='/tmp')
        # print('!!!', f)
        # cProfile.run('worflow_loop(db_config, engine_id)', f)
