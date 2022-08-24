# -*- coding: utf-8 -*-
from datetime import datetime
from glob import glob
import os
import shutil
import signal
import subprocess

# Remove a warning message: see https://github.com/celery/kombu/issues/1339
import warnings
warnings.filterwarnings('ignore', 'SelectableGroups dict interface')
from celery import Celery

from ..database import execution_database
from ..database.redis import RedisExecutionDatabase
from . import Workers

shutdown_countdown = 10

capsul_tmp = os.environ.get('CAPSUL_TMP')
if capsul_tmp:
    celery_app = Celery('capsul.engine.celery', broker=f'redis+socket://{capsul_tmp}/redis.socket')

    @celery_app.task(bind=True, ignore_result=True)
    def check_shutdown(self):
        global capsul_tmp
        celery_app.control.revoke(self.id) # prevent this task from being executed again
        try:
            database = execution_database(capsul_tmp)
            executions_count = database.redis.llen('capsul_running_executions')
            #TODO: possible race condition here if a connection to the celery workers
            # is done right now
            if not executions_count:
                # Shutdown database
                capsul_tmp = database.capsul_tmp
                database.redis.shutdown()
                shutil.rmtree(capsul_tmp)
                celery_app.control.shutdown() # send shutdown signal to all workers
                return
        except Exception:
            pass
        celery_app.send_task('capsul.engine.celery.check_shutdown', countdown=shutdown_countdown)

    @celery_app.task(ignore_result=True)
    def start_ready_processes():
        database = execution_database(capsul_tmp)
        count = 0
        with database as db:
            for ready_uuid in db.ready:
                execute_process.delay(ready_uuid)
                count += 1
        print(f'start_ready_process {count}')
        return count

    @celery_app.task(ignore_result=True)
    def initial_task():
        print('initial_task')
        database = execution_database(capsul_tmp)
        database.claim_server()
        with database as db:
            db.status= 'running'
        started = start_ready_processes()
        print(f'started {started} initial tasks')
        if started == 0:
            final_task.delay()

    @celery_app.task(ignore_result=True)
    def final_task():
        print('final_task')
        celery_pid_file = f'{capsul_tmp}/capsul_celery_worker.pid'
        if os.path.exists(celery_pid_file):
            with open(celery_pid_file) as f:
                pid = int(f.read().strip())
        else:
            pid = None
        database = execution_database(capsul_tmp)
        with database as db:
            db.status= 'ended'
        database.release_server()
        if pid:
            os.kill(pid, signal.SIGTERM)


    @celery_app.task(ignore_result=True)
    def execute_process(job_uuid):
        print(f'execute_process {job_uuid}')
        database = execution_database(capsul_tmp)
        with database as db:
            job = db.job(job_uuid)
            db.move_to_ongoing(job_uuid, datetime.now())
        
        command = job['command']
        if command is not None:
            result = subprocess.run(command, capture_output=True)
            returncode = result.returncode
            stdout = result.stdout.decode()
            stderr = result.stderr.decode()
        else:
            returncode = stdout = stderr = None
        with database as db:
            all_done = db.move_to_done(job_uuid, returncode, stdout, stderr)

        if all_done:
            final_task.delay()
        else:
            start_ready_processes()


class CeleryWorkers(Workers):
    def _start(self, execution_id):
        if not isinstance(self.database, RedisExecutionDatabase):
            raise TypeError('Celery workers can only work with a Redis execution database')

        capsul_tmp = self.database.capsul_tmp
        workers_pid_file = f'{capsul_tmp}/capsul_celery_workers.pid'
        if not os.path.exist(workers_pid_file):
            self.database.redis.set('capsul_workers_pid_file', workers_pid_file)
            env = os.environ.copy()
            env.update({
                'CAPSUL_DATABASE': self.database.url,
                'CAPSUL_TMP': capsul_tmp,
            })
            cmd = [
                'celery',
                '-A', 'capsul.engine.celery',
                'multi', 'start',
                'capsul_celery_workers',
                f'--pidfile={capsul_tmp}/%n.pid',
                f'--logfile={capsul_tmp}/%n%I.log'
            ]
            subprocess.Popen(cmd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            celery_app = Celery('capsul.engine.celery', broker=self.database_url)
            celery_app.send_task('capsul.engine.celery.initial_task')
            celery_app.send_task('capsul.engine.celery.check_shutdown', countdown=shutdown_countdown)
        
 
    def _cleanup(self, execution_directory):
        pass
