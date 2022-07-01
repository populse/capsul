# -*- coding: utf-8 -*-
from datetime import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

from soma.undefined import undefined

from ..api import Pipeline, Process
from ..execution_context import ExecutionDatabase, CapsulWorkflow
from . import Engine

      
class LocalEngine(Engine):
    
    def start(self, executable, **kwargs):
        db_file = tempfile.NamedTemporaryFile(prefix='capsul_local_engine_', delete=False)
        try:
            for name, value in kwargs.items():
                setattr(executable, name, value)
            execution_context = self.execution_context(executable)
            workflow = CapsulWorkflow(executable)
            # from pprint import pprint
            # print('!start!')
            # pprint(workflow.parameters.proxy_values)
            # pprint(workflow.parameters.content)
            # pprint(workflow.parameters.no_proxy())
            # print('----')
            # pprint(workflow.jobs)
            with ExecutionDatabase(f'sqlite://{db_file.name}') as db:
                db.execution_context = execution_context
                db.executable = executable
                db.save_workflow(workflow)
                db.start_time =  datetime.now()
                db.status = 'ready'
            p = subprocess.Popen(
                [sys.executable, '-m', 'capsul.engine.local',
                 f'sqlite://{db_file.name}'],
            )
            p.wait()
            return db_file.name
        except Exception:
            db_file.close()
            os.remove(db_file.name)
            raise

    def status(self, execution_id, keys=['status', 'start_time']):
        if isinstance(keys, str):
            keys = [keys]
        with ExecutionDatabase(execution_id) as db:
            status = db.session['status'].document('', fields=keys)
        filename = execution_id + '.stdouterr'
        if os.path.exists(filename):
            with open(filename) as f:
                output = f.read()
            status['engine_output'] = output
        return status
    
    def update_executable(self, executable, execution_id):
        with ExecutionDatabase(execution_id) as db:
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
                        # print('!update_executable!', node.full_name, field.name, '<-', value)
                        setattr(node, field.name, value)
                    # else:
                    #     print('!update_executable! ignore', node.full_name, field.name, value)
                if isinstance(node, Pipeline):
                    stack.extend((n, parameters['nodes'][n.name]) for n in node.nodes.values() if n is not node and isinstance(n, Process) and n.activated)
        finally:
            if enable_parameter_links is not None:
                executable.enable_parameter_links = enable_parameter_links
    
    
if __name__ == '__main__':
    import contextlib

    if len(sys.argv) != 2:
        raise ValueError('This command must be called with a single '
            'parameter containing a capsul execution database file name')
    output = open(sys.argv[1] + '.stdouterr', 'w')
    contextlib.redirect_stdout(output)
    contextlib.redirect_stderr(output)
    database = ExecutionDatabase(sys.argv[1])
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
        tmp = tempfile.mkdtemp(prefix='capsul_local_engine_')
        db_update = {}
        try:
            # create environment variables for jobs
            env = os.environ.copy()
            env.update({
                'CAPSUL_DATABASE': sys.argv[1],
                'CAPSUL_TMP': tmp,
            })
            # Read jobs workflow
            with database as db:
                db.status = 'running'
                db.start_time = datetime.now()
                jobs = {}
                ready = set()
                waiting = set()
                done = set()
                for job in db.jobs():
                    jobs[job['uuid']] = job
                    if job['wait_for']:
                        waiting.add(job['uuid'])
                    else:
                        ready.add(job['uuid'])
            
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
            db_update['error'] = f'{e}'
            db_update['error_detail'] = f'{traceback.format_exc()}'
        finally:
            shutil.rmtree(tmp)
            db_update['status'] = 'ended'
            db_update['end_time'] = datetime.now()
            with database as db:
                db.session['status'].update_document('', db_update)
