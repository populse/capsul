# -*- coding: utf-8 -*-

import os
import sys

from soma.undefined import undefined

from .application import Capsul
from .database import execution_database

debug = False

def filename_from_url(url):
    return url.split('://', 1)[-1]

if __name__ == '__main__':
    tmp = os.environ.get('CAPSUL_TMP')
    if not tmp:
        print('Capsul cannot run command because CAPSUL_TMP is not defined: '
              f'command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(tmp):
        print('Capsul cannot run command because temporary directory does not exist: '
              f'tmp="{tmp}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print('Capsul cannot run command because parameters are missing: '
              f'tmp="{tmp}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)

    database = execution_database(tmp)
    with database as db:
        execution_context = db.execution_context
        execution_context.dataset.tmp = {
            'path': tmp
        }
    command = sys.argv[1]
    args = sys.argv[2:]
    invalid_parameters = False
    if command == 'process':
        if len(args) == 1:
            job_uuid = args[0]
            with database as db:
                job = db.job(job_uuid)
            if job is None:
                raise ValueError(f'No such job: {job_uuid}')
            process_json = job['process']
            parameters_location = job['parameters_location']
            process = Capsul.executable(process_json)
            if debug:
                print(f'---- init {process.definition} {parameters_location} ----')
            with database as db:
                workflow_parameters = db.workflow_parameters
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
            with database as db:
                for field in process.user_fields():
                    if field.output:
                        value = getattr(process, field.name, undefined)
                        if value is not undefined:
                            if workflow_parameters is None:
                                workflow_parameters = db.workflow_parameters
                                parameters = workflow_parameters
                                for index in parameters_location:
                                    if index.isnumeric():
                                        index = int(index)
                                    parameters = parameters[index]
                            parameters[field.name] = value
                if workflow_parameters is not None:
                    db.workflow_parameters = workflow_parameters
        else:
            invalid_parameters = True  
    else:
        invalid_parameters = True

    if invalid_parameters:
        print('Capsul cannot run command because parameters are invalid: '
            f'tmp="{tmp}", command={sys.argv}',
            file=sys.stderr)
        sys.exit(1)
