# -*- coding: utf-8 -*-

from datetime import datetime
import os
import shutil
import sys
import traceback

from soma.undefined import undefined

import capsul.debug as capsul_debug
from . import execution_context


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
    capsul_debug.debug_messages = []
    db_update = {}
    try:
        invalid_parameters = False
        if command == 'process':
            if len(args) == 2:
                process_uuid, iteration_index = args
                iteration_index = (None if iteration_index == 'None' else int(iteration_index))
                with database as db:
                    process = db.process(process_uuid)
                    db.update_process(process_uuid, start_time=datetime.now())
                process_update = {}
                try:
                    if iteration_index is not None:
                        process.select_iteration_index(iteration_index)
                    execution_context.executable = process
                    process.resolve_paths(execution_context)
                    process.before_execute(execution_context)
                    process.execute(execution_context)
                    process.after_execute(execution_context)
                    output_parameters = {}
                    for field in process.user_fields():
                        if field.is_output():
                            value = getattr(process, field.name, undefined)
                            if value is not undefined:
                                output_parameters[field.name] = value
                    if output_parameters:
                        process_update['output_parameters'] = output_parameters
                finally:
                    process_update['end_time'] = datetime.now()        
                    with database as db:
                        process = db.process(process_uuid)
                        db.update_process(process_uuid, **process_update)
            else:
                invalid_parameters = True  
        else:
            invalid_parameters = True

        if invalid_parameters:
            print('Capsul cannot run command because parameters are invalid: '
                f'tmp="{tmp}", database="{db_url}", command={sys.argv}',
                file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        db_update['error'] = f'{e}'
        db_update['error_detail'] = f'{traceback.format_exc()}'
    finally:
        db_update['status'] = 'ended'
        db_update['end_time'] = datetime.now()
        with database as db:
            db.session['status'].update_document('', db_update)
