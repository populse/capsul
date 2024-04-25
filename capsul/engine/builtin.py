import json
import math
import os
import shutil
import signal
import sys
import tempfile
import threading
import time
from datetime import datetime

from capsul.database import ConnectionError, ResponseError, engine_database
from capsul.run import run_job


class PollingThread(threading.Thread):
    def __init__(self, database, engine_id):
        super().__init__()
        self.lock = threading.RLock()
        self.database = database
        self.engine_id = engine_id
        self.stop_me = False
        self.current_execution = None
        self.current_job = None
        self.job_pid = None
        self.poll_interval = 5.0
        self.stop_poll_interval = 0.1

    def run(self):
        while True:
            with self.lock:
                if self.stop_me:
                    return
                engine_id = self.engine_id
                execution_id = self.current_execution
                job_id = self.current_job
                job_pid = self.job_pid
            if job_id is not None and execution_id is not None and job_pid is not None:
                # poll the database
                kill_job = self.database.job_kill_requested(
                    engine_id, execution_id, job_id
                )
                if kill_job:
                    os.kill(job_pid, signal.SIGTERM)
                    os.kill(job_pid, signal.SIGKILL)

            n = int(math.ceil(self.poll_interval / self.stop_poll_interval))
            for i in range(n):
                time.sleep(self.stop_poll_interval)
                with self.lock:
                    if self.stop_me:
                        return

    def set_pid(self, pid):
        with self.lock:
            self.job_pid = pid


def worker_loop(db_config, engine_id):
    try:
        with engine_database(db_config) as database:
            worker_id = database.worker_started(engine_id)
            poll_thread = PollingThread(database, engine_id)
            poll_thread.start()
            # print(f"!worker {worker_id}! started", engine_id)
            try:
                execution_id, job_uuid = database.pop_job(
                    engine_id, start_time=datetime.now()
                )
                while job_uuid is not None:
                    if not job_uuid:
                        # Empty string means no job available yet
                        time.sleep(0.2)
                        # print(f"!worker {worker_id}! wait", (execution_id, job_uuid))
                    elif job_uuid == "start_execution":
                        # print(f"!worker {worker_id}! start", execution_id)
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
                        # print(f"!worker {worker_id}! end", execution_id)
                        tmp = database.end_execution(engine_id, execution_id)
                        if tmp and os.path.exists(tmp):
                            shutil.rmtree(tmp)
                    else:
                        with poll_thread.lock:
                            poll_thread.current_execution = execution_id
                            poll_thread.current_job = job_uuid
                        return_code, stdout, stderr = run_job(
                            database,
                            engine_id,
                            execution_id,
                            job_uuid,
                            same_python=False,
                            debug=False,
                        )
                        with poll_thread.lock:
                            poll_thread.job_pid = None
                        # print(
                        #     f"!worker {worker_id}! job",
                        #     execution_id,
                        #     job_uuid,
                        #     database.job_finished,
                        # )
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
                # print(f"!worker {worker_id}! ended")
                with poll_thread.lock:
                    poll_thread.stop_me = True
                poll_thread.join()
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
        worker_loop(db_config, engine_id)

        # import cProfile
        # import tempfile
        # f = tempfile.mktemp(prefix='worker_profile_', dir='/tmp')
        # print('!!!', f)
        # cProfile.run('worker_loop(db_config, engine_id)', f)
