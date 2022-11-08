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

check_execution_delay = 0.5

database_url = os.environ.get('CAPSUL_DATABASE')
workers_id = os.environ.get('CAPSUL_WORKERS_ID')
if database_url:
    celery_app = Celery('capsul.engine.celery', broker=database_url)

    @celery_app.task(bind=True, ignore_result=True)
    def initial_task(self):
        global database_url
        global workers_id

        celery_app.control.revoke(self.request.id) # prevent this task from being executed again
        with execution_database(database_url) as database:
            database.workers_started(workers_id)
        celery_app.send_task('capsul.engine.celery.check_executions')



    @celery_app.task(bind=True, ignore_result=True)
    def check_executions(self):
        global database_url
        global workers_id

        celery_app.control.revoke(self.request.id) # prevent this task from being executed again
        try:
            with execution_database(database_url) as database:
                execution_id = database.get_execution(workers_id)
                if execution_id is None:
                    # Release special database connection
                    database.redis.hdel('capsul:connections', f'celery_workers_{workers_id}')
                    # send shutdown signal to all workers
                    celery_app.control.shutdown()
                    return
                elif execution_id:
                    # Create temporary directory for this execution
                    tmp = tempfile.mkdtemp(prefix='caspul_celery_')
                    try:
                        self.database.set_tmp(execution_id, tmp)
                        # Start tasks an execution task for each job that is ready
                        job = self.database.start_one_job(execution_id, start_time=datetime.now())
                        while job is not None:
                            celery_app.send_task('capsul.engine.celery.execute_process', args=(execution_id, job['uuid'],))
                            job = self.database.start_one_job(execution_id, start_time=datetime.now())
                    except Exception:
                        shutil.rmtree(tmp)
        finally:
            celery_app.send_task('capsul.engine.celery.check_execution', countdown=check_execution_delay)


    @celery_app.task(ignore_result=True)
    def execute_process(execution_id, job_uuid):
        global database_url
        global workers_id
        
        with execution_database(database_url) as database:
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



class CeleryWorkers(Workers):
    def _start(self, execution_id):
        if not isinstance(self.database, RedisExecutionDatabase):
            raise TypeError('Celery workers can only work with a Redis execution database')
        tmp = self.database.redis.get('capsul:redis_tmp')
        workers_pid_file = f'{tmp}/workers_{workers_id}.pid'
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
            celery_app.send_task('capsul.engine.celery.check_shutdown', countdown=check_execution_delay)
            # keep a special database connection to prevent the database to shutdown before Celery workers
            self.database.redis.hset('capsul:connections', workers_id, datetime.now().isoformat())
        else:
            celery_app = Celery('capsul.engine.celery', broker=self.database.url)
        tmp = tempfile.mkdtemp(prefix='capsul_celery_')
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


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('This command must be called with two '
            'parameters: a database URL and a workers_id')
    database_url = sys.argv[1]
    workers_id = sys.argv[2]
    with execution_database(database_url) as database:
        if not isinstance(database, RedisExecutionDatabase):
            raise TypeError('Celery workers can only work with a Redis execution database')
        if database.workers_status(workers_id) is None:
            raise RuntimeError(f'Engine cannot find workers in database: {workers_id}')

        # Put celery temporary files in the same temporary directory as redis database
        tmp = self.database.redis.get('capsul:redis_tmp')
        env = os.environ.copy()
        env.update({
            'CAPSUL_DATABASE': database_url,
            'CAPSUL_WORKERS_ID': workers_id,
        })
        cmd = [
            'celery',
            '-A', 'capsul.engine.celery',
            'multi', 'start',
            'capsul_celery_workers',
            f'--pidfile={tmp}/%n.pid',
            f'--logfile={tmp}/%n%I.log'
        ]
        subprocess.Popen(cmd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        celery_app = Celery('capsul.engine.celery', broker=database_url)
        # keep a special database connection to prevent the database to shutdown before Celery workers
        database.redis.hset('capsul:connections', 'celery_workers_{workers_id}', datetime.now().isoformat())
        celery_app.send_task('capsul.engine.celery.check_executions', countdown=check_execution_delay)
