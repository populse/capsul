# -*- coding: utf-8 -*-
from datetime import datetime
from glob import glob
import os
import shutil
import subprocess
import tempfile
import sys

# Remove a warning message: see https://github.com/celery/kombu/issues/1339
import warnings
warnings.filterwarnings('ignore', 'SelectableGroups dict interface')
from celery import Celery

from ..database import execution_database
from ..database.redis import RedisExecutionDatabase
from . import Workers

shutdown_countdown = 30

database_url = os.environ.get('CAPSUL_DATABASE')
if database_url:
    celery_app = Celery('capsul.engine.celery', broker=database_url)

    @celery_app.task(bind=True, ignore_result=True)
    def check_shutdown(self):
        print('!check_shutdown!')
        global database_url
        celery_app.control.revoke(self.request.id) # prevent this task from being executed again
        try:
            database = execution_database(database_url)
            try:
                executions_count = database.redis.llen('capsul_ongoing_executions')
                print(f'!executions_count! {executions_count}')
                #TODO: possible race condition here if a connection to the celery workers
                # is done right now
                if not executions_count:
                    # Release special database connection
                    print('!shutting down celery!')
                    database.redis.hdel('capsul_connections', 'celery_workers_connection')
                    celery_app.control.shutdown() # send shutdown signal to all workers
                    return
            finally:
                database.close()
        except Exception:
            pass
        celery_app.send_task('capsul.engine.celery.check_shutdown', countdown=shutdown_countdown)



    @celery_app.task(ignore_result=True)
    def execute_process(execution_id, job_uuid):
        global database_url
        
        database = execution_database(database_url)
        try:
            job = database.job(execution_id, job_uuid)
            print(f"execute_process {job.get('process', {}).get('definition')} (execution_id={execution_id}, job {job_uuid})")
            command = job['command']
            if command is not None:
                env = os.environ.copy()
                env['CAPSUL_DATABASE'] = database_url
                env['CAPSUL_EXECUTION_ID'] = execution_id
                result = subprocess.run(command, env=env, capture_output=True)
                returncode = result.returncode
                stdout = result.stdout.decode()
                stderr = result.stderr.decode()
            else:
                returncode = stdout = stderr = None
            database.job_finished(execution_id, job['uuid'], 
                end_time=datetime.now(),
                returncode=returncode,
                stdout=stdout,
                stderr=stderr)
            job = database.start_one_job(execution_id, start_time=datetime.now())
            while job is not None:
                # print(f"  push job {job.get('process', {}).get('definition')} (job {job_uuid})")
                celery_app.send_task('capsul.engine.celery.execute_process', args=(execution_id, job['uuid'],))
                job = database.start_one_job(execution_id, start_time=datetime.now())
        finally:
            database.close()


class CeleryWorkers(Workers):
    def _start(self, execution_id):
        if not isinstance(self.database, RedisExecutionDatabase):
            raise TypeError('Celery workers can only work with a Redis execution database')
        tmp = self.database.redis.get('capsul_redis_tmp')
        workers_pid_file = f'{tmp}/capsul_celery_workers.pid'
        if not os.path.exists(workers_pid_file):
            env = os.environ.copy()
            env.update({
                'CAPSUL_DATABASE': self.database.url,
            })
            cmd = [
                sys.executable, '-m', 'celery',
                '-A', 'capsul.engine.celery',
                'multi', 'start',
                'capsul_celery_workers',
                f'--pidfile={tmp}/%n.pid',
                f'--logfile={tmp}/%n%I.log'
            ]
            subprocess.Popen(cmd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            celery_app = Celery('capsul.engine.celery', broker=self.database.url)
            celery_app.send_task('capsul.engine.celery.check_shutdown', countdown=shutdown_countdown)
            # keep a special database connection to prevent the database to shutdown before Celery workers
            self.database.redis.hset('capsul_connections', 'celery_workers_connection', datetime.now().isoformat())
        else:
            celery_app = Celery('capsul.engine.celery', broker=self.database.url)
        tmp = tempfile.mkdtemp(prefix='caspul_celery_')
        try:
            self.database.set_tmp(execution_id, tmp)
            job = self.database.start_one_job(execution_id, start_time=datetime.now())
            while job is not None:
                celery_app.send_task('capsul.engine.celery.execute_process', args=(execution_id, job['uuid'],))
                job = self.database.start_one_job(execution_id, start_time=datetime.now())
        except Exception:
            shutil.rmtree(tmp)

 
    def _cleanup(self, execution_directory):
        pass

    def _debug_info(self, execution_id):
        #TODO: return the workers log
        return {}
