# -*- coding: utf-8 -*-
from datetime import datetime
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback

from celery import Celery

from soma.undefined import undefined

from ..api import Pipeline, Process
from ..database import execution_database
from ..execution_context import CapsulWorkflow
from . import Engine

capsul_tmp = os.environ.get('CAPSUL_TMP')
if capsul_tmp:
    celery_app = Celery('capsul.engine.celery', broker=f'redis+socket://{capsul_tmp}/redis.socket')

    @celery_app.task(ignore_result=True)
    def start_ready_processes():
        database = execution_database(capsul_tmp)
        with database as db:
            for ready_uuid in db.ready:
                execute_process.delay(ready_uuid)

    @celery_app.task(ignore_result=True)
    def initial_task():
        database = execution_database(capsul_tmp)
        database.claim_server()
        start_ready_processes()

    @celery_app.task(ignore_result=True)
    def final_task():
        celery_pid_file = f'{capsul_tmp}/capsul_celery_worker.pid'
        if os.path.exists(celery_pid_file):
            with open(celery_pid_file) as f:
                pid = int(f.read().strip())
        else:
            pid = None
        database = execution_database(capsul_tmp)
        database.release_server()
        if pid:
            os.kill(pid, signal.SIGTERM)


    @celery_app.task(ignore_result=True)
    def execute_process(job_uuid):
        database = execution_database(capsul_tmp)
        with database as db:
            job = db.job(job_uuid)
            db.move_to_ongoing(job_uuid)
        
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


class CeleryEngine(Engine):
    database_type = 'redis'    
    
    def start(self, executable, **kwargs):
        capsul_tmp = tempfile.mkdtemp(prefix='capsul_local_engine_')
        try:
            for name, value in kwargs.items():
                setattr(executable, name, value)
            execution_context = self.execution_context(executable)
            workflow = CapsulWorkflow(executable)
            # create environment variables for jobs
            env = os.environ.copy()
            env.update({
                'CAPSUL_TMP': capsul_tmp,
            })
            # from pprint import pprint
            # print('!start!')
            # pprint(workflow.parameters.proxy_values)
            # pprint(workflow.parameters.content)
            # pprint(workflow.parameters.no_proxy())
            # print('----')
            # pprint(workflow.jobs)
            database = create_execution_database(capsul_tmp, 'redis')
            database.claim_server()
            with database as db:
                db.execution_context = execution_context
                db.executable = executable
                db.save_workflow(workflow)

            celery_dir = capsul_tmp
            cmd = [
                'celery',
                '-A', 'capsul.engine.celery',
                'multi', 'start',
                'capsul_celery_worker',
                f'--pidfile={celery_dir}/%n.pid',
                f'--logfile={celery_dir}/%n%I.log'
            ]
            subprocess.Popen(cmd, env=env, start_new_session=True)

            celery_app = Celery('capsul.engine.celery', broker=f'redis+socket://{capsul_tmp}/redis.socket')
            celery_app.send_task('start_ready_processes')
            return capsul_tmp
        except Exception:
            shutil.rmtree(capsul_tmp)
            raise

    def status(self, execution_id):
        with execution_database(execution_id) as db:
            status = db.status
        return status
    
    def error(self, execution_id):
        with execution_database(execution_id) as db:
            error = db.error
        return error
    
    def error_detail(self, execution_id):
        with execution_database(execution_id) as db:
            error_detail = db.error_detail
        return error_detail
    
    def update_executable(self, executable, execution_id):
        with execution_database(execution_id) as db:
            parameters = db.workflow_parameters
        # print('!update_executable!')
        # from pprint import pprint
        # pprint(parameters.proxy_values)
        # pprint(parameters.content)
        # pprint(parameters.no_proxy())
        if isinstance(executable, Pipeline):
            enable_parameter_links = executable.enable_parameter_links
            executable.enable_parameter_links = False
        else:
            enable_parameter_links = None
        try:
            stack = [(executable, parameters)]
            # print('!update_executable! stack', executable.full_name)
            # pprint(parameters.content)
            while stack:
                node, parameters = stack.pop(0)
                for field in node.user_fields():
                    value = parameters.get(field.name, undefined)
                    if value is not undefined:
                        value = parameters.no_proxy(value)
                        if value is None:
                            value = undefined
                        # print('!update_executable!', node.full_name, field.name, '<-', repr(value))
                        setattr(node, field.name, value)
                    # else:
                    #     print('!update_executable! ignore', node.full_name, field.name, repr(value))
                if isinstance(node, Pipeline):
                    stack.extend((n, parameters['nodes'][n.name]) for n in node.nodes.values() if n is not node and isinstance(n, Process) and n.activated)
        finally:
            if enable_parameter_links is not None:
                executable.enable_parameter_links = enable_parameter_links
    
    def dispose(self, execution_id):
        with open(self.redis_pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        database = execution_database(execution_id)
        database.release_server()
        if os.path.exists(execution_id):
            shutil.rmtree(execution_id)

    
if __name__ == '__main__':
    import contextlib

    if len(sys.argv) != 2:
        raise ValueError('This command must be called with a single '
            'parameter containing a capsul execution temporary directory')
    execution_id = sys.argv[1]
    if not os.path.isdir(execution_id):
        raise ValueError(f'"{execution_id} is not an existing directory')
    output = open(f'{execution_id}/stdouterr', 'w')
    contextlib.redirect_stdout(output)
    contextlib.redirect_stderr(output)
    database = execution_database(execution_id)
    with database as db:
        db.status = 'submited'

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
        # Create temporary directory
        tmp = execution_id
        try:
            
            # Execute jobs sequentially
            while ready:
                job_uuid = ready.pop()
                job = jobs[job_uuid]
                command = job['command']
                if command is not None:
                    subprocess.check_call(command, env=env, stdout=sys.stdout, 
                        stderr=subprocess.STDOUT,)
                done.add(job_uuid)
                for waiting_uuid in list(waiting):
                    waiting_job = jobs[waiting_uuid]
                    if not any(i for i in waiting_job['wait_for'] if i not in done):
                        waiting.remove(waiting_uuid)
                        ready.add(waiting_uuid)
        except Exception as e:
            with database as db:
                db.error = f'{e}'
                db.error_detail = f'{traceback.format_exc()}'
        finally:
            with database as db:
                db.status = 'ended'
                db.end_time = datetime.now()







































import os
import shutil
import subprocess
import tempfile
import time
import sys


from populse_db import Database


    

if __name__ == '__main__':
    tmp = tempfile.mkdtemp()
    celery_dir = f'/tmp/celery'
    redis = None
    try:
        cmd = [
            'redis-server'
        ]
        redis = subprocess.Popen(cmd)

        database_file = '/tmp/test.sqlite'
        os.environ['CAPSUL_DATABASE'] = database_file
        celery = f'{os.environ["HOME"]}/.local/bin/celery'
        cmd = [
            celery,
            '-A', 'capsul.engine.celery',
            'multi', 'start',
            'capsul_celery_worker',
            f'--pidfile={celery_dir}/%n.pid',
            f'--logfile={celery_dir}/%n%I.log'
        ]
        subprocess.check_call(cmd, env=os.environ)
        if os.path.exists(database_file):
            os.remove(database_file)
        database = Database(database_file)
        with database as session:
            session.add_collection('waiting')
            session.add_collection('ready')
            session.add_collection('ongoing')
            session.add_collection('done')

            session['waiting']['begin'] = {}
            all = set()
            for i in range(10):
                job_i = f'{i}'
                session['waiting'][job_i] = {
                    'waiting_for': ['begin']
                }
                all.add(job_i)
                # for j in range(10):
                #     job_j = f'{i}.{j}'
                #     session['waiting'][job_j] = {
                #         'waiting_for': [job_i]
                #     }
                #     all.add(job_j)
            session['waiting']['end'] = {
                'waiting_for': list(all)
            }
            
        start_ready_jobs()
        time.sleep(5)
    finally:
        cmd = [
            celery,
            '-A', 'capsul.engine.celery',
            'multi', 'stopwait',
            'capsul_celery_worker',
            f'--pidfile={celery_dir}/%n.pid',
            f'--logfile={celery_dir}/%n%I.log'
        ]
        subprocess.check_call(cmd)
        if redis:
            redis.terminate()
            redis.wait(5)
            if redis.returncode is None:
                redis.kill()
                redis.wait(5)
        shutil.rmtree(tmp)
