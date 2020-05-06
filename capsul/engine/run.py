# -*- coding: utf-8 -*-

'''
Implementation of :class:`~capsul.engine.CapsulEngine` processing methods.
They have been moved to this file for clarity.

Running is always using `Soma-Workflow <https://github.com/populse/soma-workflow/>.
'''
from __future__ import absolute_import
from __future__ import print_function

from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import ProcessNode
from traits.api import Undefined


def start(engine, process, history=False):
    '''
    Asynchronously start the exectution of a process in the connected
    computing environment. Returns a string that is an identifier of the
    process execution and can be used to get the status of the
    execution or wait for its termination.

    TODO:
    if history is True, an entry of the process execution is stored in
    the database. The content of this entry is to be defined but it will
    contain the process parameters (to restart the process) and will be
    updated on process termination (for instance to store execution time
    if possible).
    '''
    missing = process.get_missing_mandatory_parameters()
    if len(missing) != 0:
        ptype = 'process'
        if isinstance(process, Pipeline):
            ptype = 'pipeline'
        raise ValueError('In %s %s: missing mandatory parameters: %s'
                          % (ptype, process.name,
                            ', '.join(missing)))

    # Use soma worflow to execute the pipeline or porcess in parallel
    # on the local machine

    # Create soma workflow pipeline
    from capsul.pipeline.pipeline_workflow import workflow_from_pipeline
    import soma_workflow.client as swclient

    workflow = workflow_from_pipeline(process)

    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    resource_id = swm.get_resource_id()
    queue = None
    if hasattr(engine.study_config.somaworkflow_computing_resources_config,
               resource_id):
        res_conf = getattr(
            engine.study_config.somaworkflow_computing_resources_config,
            resource_id)
        queue = res_conf.queue
        if queue is Undefined:
            queue = None
    workflow_name = process.name
    wf_id = controller.submit_workflow(workflow=workflow, name=workflow_name,
                                       queue=queue)
    swclient.Helper.transfer_input_files(wf_id, controller)

    return wf_id, workflow.pipeline()


def wait(engine, execution_id, timeout=-1, pipeline=None):
    '''
    Wait for the end of a process execution (either normal termination,
    interruption or error).
    '''
    import soma_workflow.client as swclient
    from soma_workflow import constants

    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    wf_id = execution_id

    controller.wait_workflow(wf_id, timeout=timeout)
    workflow_status = controller.workflow_status(wf_id)
    if workflow_status != constants.WORKFLOW_DONE:
        # not finished
        return False

    # get output values
    if pipeline:
        proc_map = {}
        todo = [pipeline]
        while todo:
            process = todo.pop(0)
            if isinstance(process, Pipeline):
                todo += [n.process for n in process.nodes.values()
                         if n is not process.pipeline_node
                             and isinstance(n, ProcessNode)]
            else:
                proc_map[id(process)] = process

        eng_wf = controller.workflow(wf_id)
        for job in eng_wf.jobs:
            if job.has_outputs:
                out_params = controller.get_job_output_params(
                    eng_wf.job_mapping[job].job_id)
                if out_params:
                    process = proc_map.get(job.process_hash)
                    if process is None:
                        # iteration or non-process job
                        continue
                    for param in list(out_params.keys()):
                        if process.trait(param) is None:
                            del out_params[param]
                    process.import_from_dict(out_params)

    # TODO: should we transfer if the WF fails ?
    swclient.Helper.transfer_output_files(wf_id, controller)
    return True


def interrupt(engine, execution_id):
    '''
    Try to stop the execution of a process. Does not wait for the process
    to be terminated.
    '''
    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    controller.stop_workflow(execution_id)


def status(engine, execution_id):
    '''
    Return a simple value with the status of an execution (queued,
    running, terminated, error, etc.)
    '''
    from soma_workflow import constants

    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    workflow_status = controller.workflow_status(execution_id)
    if workflow_status == constants.WORKFLOW_DONE:
        # finished, but in which state ?
        elements_status = controller.workflow_elements_status(execution_id)
        failed_jobs = [element for element in elements_status[0]
                       if element[1] == constants.FAILED
                       or (element[1] == constants.DONE and
                           (element[3][0]
                            not in (constants.FINISHED_REGULARLY, None)
                            or element[3][1] != 0))]
        if len(failed_jobs) != 0:
            workflow_status = 'workflow_failed'

    return workflow_status


def detailed_information(engine, execution_id):
    '''
    Return complete (and possibly big) information about a process
    execution.
    '''
    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    elements_status = controller.workflow_elements_status(execution_id)

    return elements_status


