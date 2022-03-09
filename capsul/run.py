# -*- coding: utf-8 -*-

import datetime
import json
import os
import shutil
import sys
import tempfile
import traceback

from capsul.api import Capsul, ExecutionContext, Pipeline, Process


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
        executable = capsul.executable(execution_info['executable'])
        executable.import_json(execution_info['executable']['parameters'])
        tmp = tempfile.mkdtemp()
        try:
            execution_info['status'] = 'running'
            execution_info['start_time'] = datetime.datetime.now().isoformat()
            execution_info['pid'] = os.getpid()
            debug_messages = []
            execution_info['debug_messages'] = debug_messages
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)

            context = ExecutionContext(execution_info, tmp)

            if isinstance(executable, Pipeline):
                nodes = executable.all_nodes()
            else:
                nodes = [executable]
            for node in nodes:
                for field in node.fields():
                    if field.is_path():
                        value = getattr(node, field.name, None)
                        if value and value.startswith('!'):
                            final_value = eval(f"f'{{{value[1:]}}}'", context.__dict__, context.__dict__)
                            setattr(node, field.name, final_value)
            executable.before_execute(context)
            if isinstance(executable, Pipeline):
                debug_messages.append(f'execute pipeline {executable.definition}')
                debug_messages.append(f'  nodes -> {executable.workflow_ordered_nodes()}')
                for node in executable.workflow_ordered_nodes():
                    node.before_execute(context)
                    node.execute(context)
                    node.after_execute(context)
            else:
                debug_messages.append('execute process {executable.definition}')
                executable.execute(context)
            executable.after_execute(context)
        except Exception as e:
            execution_info['error'] = f'{e}'
            execution_info['error_detail'] = f'{traceback.format_exc()}'
        finally:
            shutil.rmtree(tmp)
            execution_info['status'] = 'ended'
            execution_info['end_time'] = datetime.datetime.now().isoformat()
            execution_info.pop('pid', None)
            execution_info['executable']['parameters'] = executable.json()['parameters']
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)
