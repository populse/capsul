# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys

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
                output_parameters = {}
                output_parameters_list = {}
                if iteration_index is not None:
                    process.select_iteration_index(iteration_index)
                    run_process = process.process
                else:
                    run_process = process
                execution_context.executable = run_process
                run_process.resolve_paths(execution_context)
                run_process.before_execute(execution_context)
                run_process.execute(execution_context)
                run_process.after_execute(execution_context)
                for field in run_process.user_fields():
                    if field.is_output():
                        value = getattr(run_process, field.name, undefined)
                        if value is not undefined:
                            if iteration_index is not None and field.name in process.iterative_parameters:
                                output_parameters_list[field.name] = value
                            else:
                                output_parameters[field.name] = value
            finally:
                process_update['end_time'] = datetime.now()        
                with database as db:
                    if iteration_index is not None:
                        row = db.session['processes'].document(process_uuid, fields=['output_parameters'], as_list=True)
                        if row and row[0]:
                            op = row[0]
                        else:
                            op = {}
                        for p, v in output_parameters_list.items():
                            l = op.get(p, getattr(process, p))
                            l[iteration_index] = v
                            output_parameters[p] = l
                    if output_parameters:
                        process_update['output_parameters'] = output_parameters
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
