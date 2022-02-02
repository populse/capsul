# -*- coding: utf-8 -*-

import datetime
import json
import os
import sys
import traceback

from capsul.api import Capsul, ExecutionContext

if __name__ == '__main__':
    # Really detach the process from the parent.
    # Whthout this fork, performing Capsul tests shows warning
    # about child processes not properly wait for.
    pid = os.fork()
    if pid == 0:
        os.setsid()
        if len(sys.argv) != 2:
            raise ValueError('This command must be called with a single parameter containing a capsul execution file')
        execution_file = sys.argv[1]
        with open(execution_file) as f:
            execution_info = json.load(f)
        capsul = Capsul()
        executable = capsul.executable(execution_info['executable']['definition'])
        executable.import_json(execution_info['executable']['parameters'])
        
        try:
            execution_info['status'] = 'running'
            execution_info['start_time'] = datetime.datetime.now().isoformat()
            execution_info['pid'] = os.getpid()
            json.dump(execution_info, open(execution_info, 'w'))

            context = ExecutionContext(execution_info)
            executable.before_execute(context)
            executable.execute(context)
            executable.after_execute(context)
        except Exception as e:
            execution_info['error'] = f'{e}'
            execution_info['error_detail'] = f'{traceback.format_exc()}'
        finally:
            execution_info['status'] = 'ended'
            execution_info['end_time'] = datetime.datetime.now().isoformat()
            execution_info.pop('pid', None)
            execution_info['executable']['parameters'] = executable.json()['parameters']
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)
