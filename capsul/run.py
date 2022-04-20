# -*- coding: utf-8 -*-

import datetime
import json
import os
import shutil
import sys
import tempfile
import traceback

from capsul.api import Capsul, Pipeline
from .pipeline.process_iteration import ProcessIteration
from .execution_context import ExecutionContext
import capsul.debug as capsul_debug


if __name__ == '__main__':
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
        if len(sys.argv) != 2:
            raise ValueError('This command must be called with a single parameter containing a capsul execution file')
        execution_file = sys.argv[1]
        with open(execution_file) as f:
            execution_info = json.load(f)
        capsul_debug.debug_messages = []
        capsul = Capsul()
        executable = None
        tmp = tempfile.mkdtemp()
        try:
            executable = capsul.executable(execution_info['executable'])
            executable.import_json(execution_info['executable']['parameters'])
            execution_info['status'] = 'running'
            execution_info['start_time'] = datetime.datetime.now().isoformat()
            execution_info['pid'] = os.getpid()
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)

            context = ExecutionContext(
                config=execution_info['execution_context'], 
                executable=executable)
            context.dataset['tmp'] = tmp

            if isinstance(executable, Pipeline):
                nodes = executable.all_nodes()
            else:
                nodes = [executable]
            for node in nodes:
                if not node.activated:
                    continue
                for field in node.fields():
                    if field.is_path():
                        value = getattr(node, field.name, None)
                        if value and value.startswith('!'):
                            try:
                                final_value = eval(f"f'{value[1:]}'", context.__dict__, context.__dict__)
                            except Exception:
                                final_value = value
                            setattr(node, field.name, final_value)
            executable.before_execute(context)
            if isinstance(executable, Pipeline):
                for node in reversed(executable.workflow_ordered_nodes()):
                    if isinstance(node, ProcessIteration):
                        for process in node.iterate_over_process_parmeters():
                            process.before_execute(context)
                            process.execute(context)
                            process.after_execute(context)
                    else:
                        node.before_execute(context)
                        node.execute(context)
                        node.after_execute(context)
            else:
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
            if executable is not None:
                execution_info['executable']['parameters'] = executable.json()['parameters']
            execution_info['debug_messages'] = capsul_debug.debug_messages
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)
