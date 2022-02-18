# -*- coding: utf-8 -*-

import datetime
import json
import os
import sys
import traceback

from capsul.api import Capsul, ExecutionContext, Pipeline, Process


def pipeline_graph(pipeline):
    '''
    ready_nodes : dict(node: succesor nodes)
    waiting_nodes : dict(node: (predecessors count, successor nodes))
    '''
    predecessor_count = {}
    node_successors = {}
    for node_name, node in pipeline.nodes.items():
        if node_name == '':
            # Ignore pipeline node
            continue
        if isinstance(node, Process):
            predecessor_count.setdefault(node, 0)
            successors = set()
            for successor, _ in pipeline.get_linked_items(node):
                if successor not in successors:
                    predecessor_count[sucessor] = predecessor_count.get(successor, 0) + 1
                    node_successors.setdefault(node, set()).add(successor)
                    successors.add(successor)

    ready_nodes = {i: node_successors.get(i,set()) for i in predecessor_count if predecessor_count[i] == 0}
    waiting_nodes = {i: [predecessor_count[i], node_successors.get(i,set())] for i in predecessor_count if predecessor_count[i] != 0}
    return ready_nodes, waiting_nodes


def execute_pipeline(pipeline, context):
    ready_nodes, waiting_nodes = pipeline_graph(pipeline)
    while ready_nodes:
        process, successors = ready_nodes.popitem()
        process.before_execute(context)
        if isinstance(process, Pipeline):
            execute_pipeline(process, context)
        else:
            process.execute(context)
        process.after_execute(context)
        for successor in successors:
            predecessor_count, s = waiting_nodes[successor][0] - 1
            if predecessor_count == 0:
                ready_nodes[successor] = s
                del waiting_nodes[successor]
            else:
                waiting_nodes[successor][0] = predecessor_count

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
        
        try:
            execution_info['status'] = 'running'
            execution_info['start_time'] = datetime.datetime.now().isoformat()
            execution_info['pid'] = os.getpid()
            with open(execution_file, 'w') as f:
                json.dump(execution_info, f)

            context = ExecutionContext(execution_info)
            executable.before_execute(context)
            if isinstance(executable, Pipeline):
                execute_pipeline(executable, context)
            else:
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
