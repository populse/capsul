# -*- coding: utf-8 -*-

import os
import sys

from soma.undefined import undefined

from .application import Capsul
from .database import execution_database

debug = False

if __name__ == '__main__':
    tmp = os.environ.get('CAPSUL_TMP')
    if not tmp:
        print('Capsul cannot run job because CAPSUL_TMP is not defined: '
              f'command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(tmp):
        print('Capsul cannot run job because temporary directory does not exist: '
              f'tmp="{tmp}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print('Capsul cannot run command because parameters are missing: '
              f'tmp="{tmp}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    database_url = os.environ.get('CAPSUL_DATABASE')
    if not database_url:
        print('Capsul cannot run job because CAPSUL_DATABASE is not defined: '
              f'command={sys.argv}',
              file=sys.stderr)
    execution_id = os.environ.get('CAPSUL_EXECUTION_ID')
    if not execution_id:
        print('Capsul cannot run job because CAPSUL_EXECUTION_ID is not defined: '
              f'command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    database = execution_database(database_url)
    try:
        execution_context = database.execution_context(execution_id)
        execution_context.dataset.tmp = {
            'path': tmp
        }
        command = sys.argv[1]
        args = sys.argv[2:]
        invalid_parameters = False
        if command == 'process':
            if len(args) == 1:
                job_uuid = args[0]
                job = database.job(execution_id, job_uuid)
                if job is None:
                    raise ValueError(f'No such job: {job_uuid}')
                process_json = job['process']
                parameters_location = job['parameters_location']
                process = Capsul.executable(process_json)
                if debug:
                    print(f'---- init {process.definition} {parameters_location} ----')
                workflow_parameters = database.workflow_parameters(execution_id)
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
                workflow_parameters = None
                for field in process.user_fields():
                    if field.output:
                        value = getattr(process, field.name, undefined)
                        if value is not undefined:
                            if workflow_parameters is None:
                                workflow_parameters = database.workflow_parameters(execution_id)
                                parameters = workflow_parameters
                                for index in parameters_location:
                                    if index.isnumeric():
                                        index = int(index)
                                    parameters = parameters[index]
                            parameters[field.name] = value
                if workflow_parameters is not None:
                    database.set_workflow_parameters(execution_id, workflow_parameters)
            else:
                invalid_parameters = True  
        else:
            invalid_parameters = True
    finally:
        database.close()
    
    if invalid_parameters:
        print('Capsul cannot run command because parameters are invalid: '
            f'tmp="{tmp}", command={sys.argv}',
            file=sys.stderr)
        sys.exit(1)
