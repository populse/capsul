# -*- coding: utf-8 -*-

import datetime
import json
import os
import sys
import traceback

from capsul.api import Capsul

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise ValueError('This command must be called with a single parameter containing a capsul executable filename')
    executable_file = sys.argv[1]
    executable_info = json.load(open(executable_file))
    capsul = Capsul()
    executable = capsul.executable(executable_info['definition'])
    executable.import_json(executable_info['parameters'])
    
    try:
        executable_info['status'] = 'running'
        executable_info['start_time'] = datetime.datetime.now().isoformat()
        executable_info['pid'] = os.getpid()
        json.dump(executable_info, open(executable_file, 'w'))

        executable.before_execute(context=None)
        executable.execute(context=None)
        executable.after_execute(context=None)
    except Exception as e:
        executable_info['error'] = f'{e}'
        executable_info['error_detail'] = f'{traceback.format_exc()}'
    finally:
        executable_info['status'] = 'ended'
        executable_info['end_time'] = datetime.datetime.now().isoformat()
        executable_info.pop('pid', None)
        executable_info['parameters'] = executable.json()
        json.dump(executable_info, open(executable_file, 'w'))
