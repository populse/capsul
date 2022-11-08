# -*- coding: utf-8 -*-

import contextlib
import io
import json
import os
import subprocess
import sys
import traceback

from soma.undefined import undefined

from .application import Capsul
from .database import engine_database


def run_job(database, engine_id, execution_id, job_uuid, same_python=False, debug=False):
    if same_python:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                execute_job(database, engine_id, execution_id, job_uuid, debug=debug)
                returncode = 0
            except Exception as e:
                print(traceback.format_exc(), file=stderr)
                returncode = 1
        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
    else:
        env = os.environ.copy()
        env['CAPSUL_WORKER_DATABASE'] = json.dumps(database.config)
        if debug:
            env['CAPSUL_DEBUG'] = '1'
        result = subprocess.run(['python', '-m', 'capsul.run', engine_id, job_uuid], env=env, capture_output=True)
        returncode = result.returncode
        stdout = result.stdout.decode()
        stderr = result.stderr.decode()
    return returncode, stdout, stderr



def execute_job(database, engine_id, execution_id, job_uuid, debug=False):
    execution_context = database.execution_context(engine_id, execution_id)
    execution_context.dataset.tmp = {
        'path': database.tmp(engine_id, execution_id),
    }
    job = database.job(engine_id, execution_id, job_uuid)
    if job is None:
        raise ValueError(f'No such job: {job_uuid}')
    process_json = job['process']
    parameters_location = job['parameters_location']
    process = Capsul.executable(process_json)
    if debug:
        print(f'---- init {process.definition} {parameters_location} ----')
    workflow_parameters = database.workflow_parameters(engine_id, execution_id)
    parameters = workflow_parameters
    for index in parameters_location:
        if index.isnumeric():
            index = int(index)
        parameters = parameters[index]
    if debug:
        from pprint import pprint
        pprint(parameters.no_proxy())
        print(f'----')
    for field in process.user_fields():
        if field.name in parameters and parameters[field.name] is not None:
            value = parameters.no_proxy(parameters[field.name])
            setattr(process, field.name, value)
    execution_context.executable = process
    process.resolve_paths(execution_context)
    if debug:
        print(f'---- start {process.definition} ----')
        for field in process.user_fields():
            if not field.output:
                value = getattr(process, field.name, undefined)
                if value is not undefined:
                    print ('   ', field.name, '=', value)
    process.before_execute(execution_context)
    result = process.execute(execution_context)
    process.after_execute(result, execution_context)
    if debug:
        print(f'---- stop {process.definition} ----')
        for field in process.user_fields():
            if field.output:
                value = getattr(process, field.name, undefined)
                if value is not undefined:
                    print ('   ', field.name, '=', value)
    output_values = {}
    for field in process.user_fields():
        if field.output:
            value = getattr(process, field.name, undefined)
            if value is not undefined:
                output_values[field.name] = value
    if output_values is not None:
        database.update_workflow_parameters(engine_id, execution_id, parameters_location, output_values)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Wrong number of paramaters, 2 expected:'
              f'command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    engine_id = sys.argv[1]
    job_uuid = sys.argv[2]
    db_config = os.environ.get('CAPSUL_WORKER_DATABASE')
    if not db_config:
        print('Capsul cannot run job because CAPSUL_WORKER_DATABASE is not defined: '
              f'command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    db_config = json.loads(db_config)
    debug = 'CAPSUL_DEBUG' in os.environ
    with engine_database(db_config) as database:
        execute_job(database, engine_id, job_uuid, debug=debug)
