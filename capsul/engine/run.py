# -*- coding: utf-8 -*-

'''
Implementation of :class:`~capsul.engine.CapsulEngine` processing methods.
They have been moved to this file for clarity.

Running is always using `Soma-Workflow <https://github.com/populse/soma-workflow/>`_.
'''
from __future__ import absolute_import
from __future__ import print_function

from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import ProcessNode
from traits.api import Undefined
import six
import tempfile
import os
import io


class WorkflowExecutionError(Exception):
    '''
    Exception class raised when a workflow execution fails.
    It holds references to the
    :class:`~soma_workflow.client.WorkflowController` and the workflow id
    '''
    def __init__(self, controller, workflow_id, status=None,
                 workflow_kept=True, verbose=True):
        wk = ''
        wc = ''
        precisions = ''
        if workflow_kept:
            wk = 'not '
            wc = ' from soma_workflow and must be deleted manually'
        if workflow_kept:
            self.controller = controller
            self.workflow_id = workflow_id
        if verbose:
            import soma_workflow.client as swclient

            failed_jobs = swclient.Helper.list_failed_jobs(
                workflow_id, controller)
            precisions_list = ['\nFailed jobs: %s' % repr(failed_jobs)]
            from soma_workflow import constants as swc
            aborted_statuses = set(
                [swc.EXIT_UNDETERMINED,
                 swc.EXIT_ABORTED,
                 swc.FINISHED_TERM_SIG,
                 swc.FINISHED_UNCLEAR_CONDITIONS,
                 swc.USER_KILLED])
            aborted_jobs = swclient.Helper.list_failed_jobs(
                workflow_id, controller, include_statuses=aborted_statuses)
            aborted_jobs = [job for job in aborted_jobs
                            if job not in failed_jobs]
            precisions_list.append('Aborted/killed jobs: %s'
                                   % repr(aborted_jobs))
            tmp1 = tempfile.mkstemp(prefix='capsul_swf_job_stdout')
            tmp2 = tempfile.mkstemp(prefix='capsul_swf_job_stderr')
            os.close(tmp1[0])
            os.close(tmp2[0])
            fileio = io.StringIO()
            try:
                controller.log_failed_workflow(workflow_id, file=fileio)
                precisions_list.append(fileio.getvalue())

                #jobs = failed_jobs + aborted_jobs
                #cmds = controller.jobs(jobs)
                #workflow = controller.workflow(workflow_id)
                #for job_id in jobs:
                    #jinfo = cmds[job_id]
                    #if job_id in failed_jobs:
                        #has_run = True
                    #else:
                        #has_run = False
                    #status = controller.job_termination_status(job_id)
                    #controller.retrieve_job_stdouterr(job_id, tmp1[1], tmp2[1])
                    #with open(tmp1[1]) as f:
                        #stdout = f.read()
                    #with open(tmp2[1]) as f:
                        #stderr = f.read()
                    #full_job = [j for j in workflow.jobs
                                #if workflow.job_mapping[j].job_id == job_id][0]
                    #precisions_list += [
                        #'============================================',
                        #'---- failed job info ---',
                        #'* job: %d: %s' % (job_id, jinfo[0]),
                        #'* exit status: %s' % status[0],
                        #'* commandline:',
                        #jinfo[1],
                        #'* exit value: %s' % str(status[1]),
                        #'* term signal: %s' % str(status[2]),
                        #'---- env ----',
                        #repr(full_job.env),
                        #'---- configuration ----',
                        #repr(full_job.configuration),
                        #'---- stdout ----',
                        #stdout,
                        #'---- stderr ----',
                        #stderr,
                        ##'---- full host env ----',
                        ##repr(os.environ)
                    #]
            finally:
                if os.path.exists(tmp1[1]):
                    os.unlink(tmp1[1])
                if os.path.exists(tmp2[1]):
                    os.unlink(tmp2[1])
            precisions = '\n'.join(precisions_list)

        super(WorkflowExecutionError, self).__init__('Error during '
            'workflow execution. Status=%s.\n'
            'The workflow has %sbeen removed%s. %s'
            % (status, wk, wc, precisions))


def start(engine, process, workflow=None, history=True, get_pipeline=False, **kwargs):
    '''
    Asynchronously start the execution of a process or pipeline in the
    connected computing environment. Returns an identifier of
    the process execution and can be used to get the status of the
    execution or wait for its termination.

    TODO:
    if history is True, an entry of the process execution is stored in
    the database. The content of this entry is to be defined but it will
    contain the process parameters (to restart the process) and will be
    updated on process termination (for instance to store execution time
    if possible).

    Parameters
    ----------
    engine: CapsulEngine
    process: Process or Pipeline instance
    workflow: Workflow instance (optional - if already defined before call)
    history: bool (optional)
        TODO: not implemented yet.
    get_pipeline: bool (optional)
        if True, start() will return a tuple (execution_id, pipeline). The
        pipeline is normally the input pipeline (process) if it is actually
        a pipeline. But if the input process is a "single process", it will
        be inserted into a small pipeline for execution. This pipeline will
        be the one actually run, and may be passed to :meth:`wait` to set
        output parameters.

    Returns
    -------
    execution_id: int
        execution identifier (actually a soma-workflow id)
    pipeline: Pipeline instance (optional)
        only returned if get_pipeline is True.
    '''

    # set parameters values
    for k, v in six.iteritems(kwargs):
        setattr(process, k, v)

    missing = process.get_missing_mandatory_parameters()
    if len(missing) != 0:
        ptype = 'process'
        if isinstance(process, Pipeline):
            ptype = 'pipeline'
        raise ValueError('In %s %s: missing mandatory parameters: %s'
                          % (ptype, process.name,
                            ', '.join(missing)))

    # Use soma workflow to execute the pipeline or process in parallel
    # on the local machine

    # Create soma workflow pipeline
    from capsul.pipeline.pipeline_workflow import workflow_from_pipeline
    import soma_workflow.client as swclient

    swf_config = engine.settings.select_configurations(
        'global', {'somaworkflow': 'config_id=="somaworkflow"'})
    swm = engine.study_config.modules['SomaWorkflowConfig']
    swm.connect_resource(engine.connected_to())
    controller = swm.get_workflow_controller()
    resource_id = swm.get_resource_id()

    resource_config_d = engine.settings.select_configurations(
        resource_id, {'somaworkflow': 'config_id=="somaworkflow"'})
    resource_config = resource_config_d.get(
        'capsul.engine.module.somaworkflow', {})
    has_resource_config = ('capsul.engine.module.somaworkflow'
        in resource_config_d)

    if has_resource_config:
        environment = resource_id
    else:
        environment = 'global'

    if workflow is None:
        workflow = workflow_from_pipeline(process, environment=environment)

    queue = getattr(resource_config, 'queue', None)
    #if hasattr(engine.study_config.somaworkflow_computing_resources_config,
               #resource_id):
        #res_conf = getattr(
            #engine.study_config.somaworkflow_computing_resources_config,
            #resource_id)
        #queue = res_conf.queue
        #if queue is Undefined:
            #queue = None
    workflow_name = process.name
    wf_id = controller.submit_workflow(workflow=workflow, name=workflow_name,
                                       queue=queue)
    swclient.Helper.transfer_input_files(wf_id, controller)

    if get_pipeline:
        return wf_id, workflow.pipeline()
    # else forget the pipeline
    return wf_id


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
        return workflow_status

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
                    try:
                        process.import_from_dict(out_params)
                    except Exception as e:
                        print('error while importing outputs in', process.name)
                        print('outputs:', out_params)
                        print(e)

    # TODO: should we transfer if the WF fails ?
    swclient.Helper.transfer_output_files(wf_id, controller)
    return status(engine, execution_id)


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


def dispose(engine, execution_id, conditional=False):
    '''
    Update the database with the current state of a process execution and
    free the resources used in the computing resource (i.e. remove the
    workflow from SomaWorkflow).

    If ``conditional`` is set to True, then dispose is only done if the
    configuration does not specify to keep succeeded / failed workflows.
    '''
    keep = False
    if conditional:
        if not engine.study_config.somaworkflow_keep_succeeded_workflows:
            keep = False
            if engine.study_config.somaworkflow_keep_failed_workflows:
                # must see it it failed or not
                from soma_workflow import constants

                status = engine.status(execution_id)
                if status != constants.WORKFLOW_DONE:
                    keep = True
    if not keep:
        swm = engine.study_config.modules['SomaWorkflowConfig']
        swm.connect_resource(engine.connected_to())
        controller = swm.get_workflow_controller()
        controller.delete_workflow(execution_id)
        # TODO: update engine DB


def call(engine, process, history=True, **kwargs):
    eid, pipeline = engine.start(process, workflow=None, history=history, get_pipeline=True,
                                 **kwargs)
    status = engine.wait(eid, pipeline=pipeline)
    engine.dispose(eid, conditional=True)
    return status


def check_call(engine, process, history=True, **kwargs):
    eid, pipeline = engine.start(process, workflow=None, history=history, get_pipeline=True,
                                 **kwargs)
    status = engine.wait(eid, pipeline=pipeline)
    try:
        engine.raise_for_status(status, eid)
    finally:
        engine.dispose(eid, conditional=True)


def raise_for_status(engine, status, execution_id=None):
    '''
    Raise an exception if a process execution failed
    '''
    from soma_workflow import constants

    if status != constants.WORKFLOW_DONE:
        swm = engine.study_config.modules['SomaWorkflowConfig']
        swm.connect_resource(engine.connected_to())
        controller = swm.get_workflow_controller()
        raise WorkflowExecutionError(
            controller, execution_id, status,
            engine.study_config.somaworkflow_keep_failed_workflows)
