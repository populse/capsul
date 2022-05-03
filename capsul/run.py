# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import sys
import tempfile
import traceback

from soma.undefined import undefined

import capsul.debug as capsul_debug
from capsul.api import Capsul, Pipeline
from .pipeline.process_iteration import ProcessIteration
from .execution_context import ExecutionContext, ExecutionStatus


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
            raise ValueError('This command must be called with a single parameter containing a capsul execution status file')
        execution_status = ExecutionStatus(sys.argv[1])
        capsul_debug.debug_messages = []
        capsul = Capsul()
        executable = None
        tmp = tempfile.mkdtemp()
        final_status_update = {}
        try:
            with execution_status as status:
                executable = capsul.executable(status['executable'])
                executable.import_json(status['executable']['parameters'])
                execution_context = ExecutionContext(config=status['execution_context'], executable=executable)
                execution_context.dataset['tmp'] = {
                    'path': tmp
                }
                executable.resolve_paths(execution_context)
                status.update({
                    'status': 'running',
                    'start_time': datetime.datetime.now().isoformat(),
                    'pid': os.getpid(),
                })

            if isinstance(executable, Pipeline):
                nodes = executable.all_nodes()
            else:
                nodes = [executable]
            for node in nodes:
                if not node.activated:
                    continue
            executable.before_execute(execution_context)
            if isinstance(executable, Pipeline):
                for node in reversed(executable.workflow_ordered_nodes()):
                    if isinstance(node, ProcessIteration):
                        size = node.iteration_size()
                        if size:
                            list_outputs = []
                            for field in node.user_fields():
                                if field.is_output() and field.name in node.iterative_parameters:
                                    list_outputs.append(field.name)
                                    value = getattr(node, field.name, None)
                                    if value is None:
                                        setattr(node, field.name, [undefined] * size)
                                    elif len(value) < size:
                                        value += [undefined] * (size - len(value))
                            index = 0
                            for process in node.iterate_over_process_parmeters():
                                process.before_execute(execution_context)
                                process.execute(execution_context)
                                process.after_execute(execution_context)
                                for name in list_outputs:
                                    value = getattr(process, name, None)
                                    getattr(node, name)[index] = value
                                index += 1
                            for name in list_outputs:
                                executable.dispatch_value(node, name, getattr(node, name))
                                
                    else:
                        node.before_execute(execution_context)
                        node.execute(execution_context)
                        node.after_execute(execution_context)
                        for field in node.fields():
                            if field.is_output():
                                value = getattr(node, field.name, undefined)
                                executable.dispatch_value(node, field.name, value)
            else:
                executable.execute(execution_context)
            executable.after_execute(execution_context)
        except Exception as e:
            final_status_update['error'] = f'{e}'
            final_status_update['error_detail'] = f'{traceback.format_exc()}'
        finally:
            shutil.rmtree(tmp)
            final_status_update['status'] = 'ended'
            final_status_update['end_time'] = datetime.datetime.now().isoformat()
            final_status_update['pid'] = None
            output_parameters = {}
            if executable is not None:
                for field in executable.user_fields():
                    if field.is_output():
                        value = getattr(executable, field.name, undefined)
                        if value is not undefined:
                            output_parameters[field.name] = value
                final_status_update['output_parameters'] = output_parameters
            final_status_update['debug_messages'] = capsul_debug.debug_messages
            with execution_status as status:
                status.update(final_status_update)
