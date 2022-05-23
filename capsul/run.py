# -*- coding: utf-8 -*-

from datetime import datetime
import json
import os
import sys
from capsul.pipeline.process_iteration import ProcessIteration

from soma.undefined import undefined

from .application import Capsul
from . import execution_context

debug = False

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
    db_url = os.environ.get('CAPSUL_DATABASE')
    if not db_url:
        print('Capsul cannot run command because CAPSUL_DATABASE is not defined: '
              f'tmp="{tmp}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(db_url):
        print('Capsul cannot run command because database file does not exist: '
              f'tmp="{tmp}", database="{db_url}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print('Capsul cannot run command because parameters are missing: '
              f'tmp="{tmp}", database="{db_url}", command={sys.argv}',
              file=sys.stderr)
        sys.exit(1)

    database = execution_context.ExecutionDatabase(db_url)
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
                row = db.session['jobs'].document(job_uuid, fields=['process', 'parameters_location'], as_list=True)
            if row is None:
                raise ValueError(f'No such job: {job_uuid}')
            process_json, parameters_location = row
            process = Capsul.executable(process_json)
            with database as db:
                workflow_parameters = db.workflow_parameters
            parameters = workflow_parameters
            for index in parameters_location:
                if index.isnumeric():
                    index = int(index)
                parameters = parameters[index]
            for field in process.user_fields():
                if field.name in parameters and parameters[field.name] is not None:
                    setattr(process, field.name, parameters.no_proxy(parameters[field.name]))
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
            process.execute(execution_context)
            process.after_execute(execution_context)
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
            f'tmp="{tmp}", database="{db_url}", command={sys.argv}',
            file=sys.stderr)
        sys.exit(1)
