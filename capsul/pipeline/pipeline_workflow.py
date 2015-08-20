#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

"""Capsul Pipeline conversion into soma-workflow workflow.

A single available function:
workflow = workflow_from_pipeline(pipeline)
"""
import os
import socket

import soma_workflow.client as swclient

from capsul.pipeline import Pipeline, Switch
from capsul.pipeline import pipeline_tools
from capsul.process import Process
from capsul.utils.topological_sort import Graph
from traits.api import Directory, Undefined, File, Str, Any
from soma.sorted_dictionary import OrderedDict


def workflow_from_pipeline(pipeline, study_config={}, disabled_nodes=None,
                           jobs_priority=0, create_directories=True):
    """ Create a soma-workflow workflow from a Capsul Pipeline

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        a CAPSUL pipeline
    study_config: StudyConfig (optional), or dict
        holds information about file transfers and shared resource paths.
        If not specified, no translation/transfers will be used.
    disabled_nodes: sequence of pipeline nodes (Node instances) (optional)
        such nodes will be disabled on-the-fly in the pipeline, file transfers
        will be adapted accordingly (outputs may become inputs in the resulting
        workflow), and temporary files will be checked. If a disabled node was
        to produce a temporary files which is still used in an enabled node,
        then a ValueError exception will be raised.
        If disabled_nodes is not passed, they will possibly be taken from the
        pipeline (if available) using disabled steps:
        see Pipeline.define_steps()
    jobs_priority: int (optional, default: 0)
        set this priority on soma-workflow jobs.
    create_directories: bool (optional, default: True)
        if set, needed output directories (which will contain output files)
        will be created in a first job, which all other ones depend on.

    Returns
    -------
    workflow: Workflow
        a soma-workflow workflow
    """

    class TempFile(unicode):
        # class needed temporary to identify temporary paths in the pipeline.
        # must inerit a string type since it is used as a trait value
        pass

    def _files_group(path, merged_formats):
        bname = os.path.basename(path)
        l0 = len(path) - len(bname)
        p0 = 0
        paths = [path]
        while True:
            p = bname.find('.', p0)
            if p < 0:
                break
            ext = bname[p:]
            p0 = p + 1
            format_def = merged_formats.get(ext)
            if format_def:
                path0 = path[:l0 + p]
                paths += [path0 + e[0] for e in format_def]
                break
        paths.append(path + '.minf')
        return paths

    def _translated_path(path, shared_map, shared_paths, trait=None):
        if path is None or path is Undefined \
                or not shared_paths \
                or (trait is not None
                    and not isinstance(trait.trait_type, File) \
                    and not isinstance(trait.trait_type, Directory)):
            return None # not a path
        item = shared_map.get(path)
        if item is not None:
            # already in map
            return item

        for base_dir, (namespace, uuid) in shared_paths.iteritems():
            if path.startswith(base_dir + os.sep):
                rel_path = path[len(base_dir)+1:]
                #uuid = path
                item = swclient.SharedResourcePath(
                    rel_path, namespace, uuid=uuid)
                shared_map[path] = item
                return item
        return None

    def build_job(process, temp_map={}, shared_map={}, transfers=[{}, {}],
                  shared_paths={}, forbidden_temp=set(), name='', priority=0,
                  step_name=''):
        """ Create a soma-workflow Job from a Capsul Process

        Parameters
        ----------
        process: Process (mandatory)
            a CAPSUL process instance
        temp_map: dict (optional)
            temporary paths map.
        shared_map: dict (optional)
            file shared translated paths, global pipeline dict.
            This dict is updated when needed during the process.
        shared_paths: dict (optional)
            holds information about shared resource paths base dirs for
            soma-workflow.
            If not specified, no translation will be used.
        name: string (optional)
            job name. If empty, use the process name.
        priority: int (optional)
            priority assigned to the job
        step_name: str (optional)
            the step name will be stored in the job user_storage variable

        Returns
        -------
        job: Job
            a soma-workflow Job instance that will execute the CAPSUL process
        """
        def _replace_in_list(rlist, temp_map):
            for i, item in enumerate(rlist):
                if item in temp_map:
                    value = temp_map[item]
                    rlist[i] = value
                elif isinstance(item, list) or isinstance(item, tuple):
                    deeperlist = list(item)
                    _replace_in_list(deeperlist, temp_map)
                    rlist[i] = deeperlist

        def _replace_transfers(rlist, process, itransfers, otransfers):
            param_name = None
            i = 3
            for item in rlist[3:]:
                if param_name is None:
                    param_name = item
                else:
                    transfer = itransfers.get(param_name)
                    if transfer is None:
                        transfer = otransfers.get(param_name)
                    if transfer is not None:
                        value = transfer[0]
                        if isinstance(item, list) or isinstance(item, tuple):
                            # TODO: handle lists of files [transfers]
                            #deeperlist = list(item)
                            #_replace_in_list(deeperlist, transfers)
                            #rlist[i] = deeperlist
                            print '*** LIST! ***'
                        else:
                            rlist[i] = value
                    param_name = None
                i += 1

        # Get the process command line
        process_cmdline = process.get_commandline()
        job_name = name
        if not job_name:
            job_name = process.name

        # check for special modified paths in parameters
        input_replaced_paths = []
        output_replaced_paths = []
        for param_name, parameter in process.user_traits().iteritems():
            if param_name not in ('nodes_activation', 'selection_changed'):
                value = getattr(process, param_name)
                if isinstance(value, TempFile):
                    if parameter.output:
                        output_replaced_paths.append(temp_map[value])
                    else:
                        if value in forbidden_temp:
                            raise ValueError(
                                'Temporary value used cannot be generated in '
                                'the workflkow: %s.%s'
                                % (job_name, param_name))
                        input_replaced_paths.append(temp_map[value])
                else:
                    _translated_path(value, shared_map, shared_paths,
                                     parameter)

        # and replace in commandline
        iproc_transfers = transfers[0].get(process, {})
        oproc_transfers = transfers[1].get(process, {})
        #proc_transfers = dict(iproc_transfers)
        #proc_transfers.update(oproc_transfers)
        _replace_in_list(process_cmdline, temp_map)
        _replace_in_list(process_cmdline, shared_map)
        _replace_transfers(
            process_cmdline, process, iproc_transfers, oproc_transfers)

        # Return the soma-workflow job
        job = swclient.Job(
            name=job_name,
            command=process_cmdline,
            referenced_input_files
                =input_replaced_paths \
                    + [x[0] for x in iproc_transfers.values()],
            referenced_output_files
                =output_replaced_paths \
                    + [x[0] for x in oproc_transfers.values()],
            priority=priority)
        if step_name:
            job.user_storage = step_name
        return job

    def build_group(name, jobs):
        """ Create a group of jobs

        Parameters
        ----------
        name: str (mandatory)
            the group name
        jobs: list of Job (mandatory)
            the jobs we want to insert in the group

        Returns
        -------
        group: Group
            the soma-workflow Group instance
        """
        return swclient.Group(jobs, name=name)

    def get_jobs(group, groups):
        gqueue = list(group.elements)
        jobs = []
        while gqueue:
            group_or_job = gqueue.pop(0)
            if group_or_job in groups:
                gqueue += group_or_job.elements
            else:
                jobs.append(group_or_job)
        return jobs

    def assign_temporary_filenames(pipeline):
        ''' Find and temporarily assign necessary temporary file names'''
        temp_filenames = pipeline.find_empty_parameters()
        temp_map = {}
        count = 0
        for node, plug_name, optional in temp_filenames:
            if hasattr(node, 'process'):
                process = node.process
            else:
                process = node
            trait = process.user_traits()[plug_name]
            is_directory = isinstance(trait.trait_type, Directory)
            if trait.allowed_extensions:
                suffix = trait.allowed_extensions[0]
            else:
                suffix = ''
            swf_tmp = swclient.TemporaryPath(is_directory=is_directory,
                suffix=suffix)
            tmp_file = TempFile('%d' % count)
            count += 1
            temp_map[tmp_file] = (swf_tmp, node, plug_name, optional)
            # set a TempFile value to identify the params / value
            setattr(process, plug_name, tmp_file)
        return temp_map

    def restore_empty_filenames(temporary_map):
      ''' Set back Undefined values to temporarily assigned file names (using
      assign_temporary_filenames()
      '''
      for tmp_file, item in temporary_map.iteritems():
          node, plug_name = item[1:3]
          if hasattr(node, 'process'):
              process = node.process
          else:
              process = node
          setattr(process, plug_name, Undefined)

    def _get_swf_paths(study_config):
        computing_resource = getattr(
            study_config, 'somaworkflow_computing_resource', None)
        if computing_resource is None:
            return [], {}
        resources_conf = getattr(
            study_config, 'somaworkflow_computing_resources_config', None)
        if resources_conf is None:
            return [], {}
        resource_conf = getattr(resources_conf, computing_resource, None)
        if resource_conf is None:
            return [], {}
        return (resource_conf.transfer_paths,
                resource_conf.path_translations.export_to_dict())

    def _propagate_transfer(node, param, path, output, transfers,
                            transfer_item):
        todo_plugs = [(node, param, output)]
        done_plugs = set()
        while todo_plugs:
            node, param, output = todo_plugs.pop()
            plug = node.plugs[param]
            is_pipeline = False
            if plug is None or not plug.enabled or not plug.activated \
                    or plug in done_plugs:
                continue
            done_plugs.add(plug)
            if isinstance(node, Switch):
                if output:
                    # propagate to active input
                    other_param = node.switch + '_switch_' + param
                    #plug = node.plugs[input_param]
                else:
                    other_param = param[len(node.switch + '_switch_'):]
                    #other_plug = node.plugs[other_param]
                todo_plugs.append((node, other_param, not output))
            else:
                process = node.process
                if hasattr(process, 'nodes'):
                    is_pipeline = True
                    #plug = process.nodes[''].plugs.get(param)
                else:
                    # process: replace its param
                    # check trait type (must be File or Directory, not Any)
                    trait = process.user_traits()[param]
                    #plug = node.plugs[param]
                    if isinstance(trait.trait_type, File) \
                            or isinstance(trait.trait_type, Directory):
                        transfers[bool(trait.output)].setdefault(process, {})[
                            param] = (transfer_item, path)
                    #output = not output # invert IO status

            #if plug is None or not plug.enabled or not plug.activated \
                    #or plug in done_plugs:
                #continue
            if output:
                links = plug.links_to
            else:
                links = plug.links_from
            for proc_name, param_name, node, other_plug, act in links:
                if not node.activated or not node.enabled \
                        or not other_plug.activated or not other_plug.enabled \
                        or other_plug in done_plugs:
                    continue
                todo_plugs.append((node, param_name, not output))
            if is_pipeline:
                # in a pipeline node, go both directions
                if output:
                    links = plug.links_from
                else:
                    links = plug.links_to
                for proc_name, param_name, node, plug, act in links:
                    if not node.activated or not node.enabled \
                            or not plug.activated or not plug.enabled \
                            or plug in done_plugs:
                        continue
                    todo_plugs.append((node, param_name, output))

    def _get_transfers(pipeline, transfer_paths, merged_formats):
        """ Create and list FileTransfer objects needed in the pipeline.

        Parameters
        ----------
        pipeline: Pipeline
            pipeline to build workflow for
        transfer_paths: list
            paths basedirs for translations from soma-worflow config

        Returns
        -------
        [in_transfers, out_transfers]
        each of which is a dict: { Process: proc_dict }
            proc_dict is a dict: { file_path : FileTransfer object }
        FileTransfer objects are reused when referring to the same path
        used from different processes within the pipeline.
        """
        in_transfers = {}
        out_transfers = {}
        transfers = [in_transfers, out_transfers]
        todo_nodes = [pipeline.pipeline_node]
        while todo_nodes:
            node = todo_nodes.pop(0)
            if hasattr(node, 'process'):
                process = node.process
            else:
                process = node
            for param, trait in process.user_traits().iteritems():
                if isinstance(trait.trait_type, File) \
                        or isinstance(trait.trait_type, Directory) \
                        or type(trait.trait_type) is Any:
                    # is value in paths
                    path = getattr(process, param)
                    if path is None or path is Undefined:
                        continue
                    output = bool(trait.output)
                    existing_transfers = transfers[output].get(process, {})
                    existing_transfer = existing_transfers.get(param)
                    if existing_transfer:
                        continue
                    for tpath in transfer_paths:
                        if path.startswith(os.path.join(tpath, '')):
                            transfer_item = swclient.FileTransfer(
                                is_input=not output,
                                client_path=path,
                                client_paths=_files_group(path,
                                                          merged_formats))
                            _propagate_transfer(node, param,
                                                path, not output, transfers,
                                                transfer_item)
                            break
            if hasattr(process, 'nodes'):
                todo_nodes += [sub_node
                               for name, sub_node in process.nodes.iteritems()
                               if name != ''
                                  and not isinstance(sub_node, Switch)]
        return transfers

    def _expand_nodes(nodes):
        '''Expands the nodes list or set to leaf nodes by replacing pipeline
        nodes by their children list.

        Returns
        -------
        set of leaf nodes.
        '''
        nodes_list = list(nodes)
        expanded_nodes = set()
        while nodes_list:
            node = nodes_list.pop(0)
            if not hasattr(node, 'process'):
                continue # switch or something
            if isinstance(node.process, Pipeline):
                nodes_list.extend([p for p in node.process.nodes.itervalues()
                                   if p is not node])
            else:
                expanded_nodes.add(node)
        return expanded_nodes

    def _handle_disable_nodes(pipeline, temp_map, transfers, disabled_nodes):
        '''Take into account disabled nodes by changing FileTransfer outputs
        for such nodes to inputs, and recording output temporary files, so as
        to ensure that missing temporary outputs will not be used later in
        the workflow.

        disabled_nodes should be a list, or preferably a set, of leaf process
        nodes. Use _expand_nodes() if needed before calling
        _handle_disable_nodes().
        '''
        move_to_input = {}
        remove_temp = set()
        for node in disabled_nodes:
            if not hasattr(node, 'process'):
                continue # switch or something else
            process = node.process
            otrans = transfers[1].get(process, None)
            for param, trait in process.user_traits().iteritems():
                if trait.output and (isinstance(trait.trait_type, File) \
                        or isinstance(trait.trait_type, Directory) \
                        or type(trait.trait_type) is Any):
                    path = getattr(process, param)
                    if otrans is not None:
                        transfer, path2 = otrans.get(param, (None, None))
                    else:
                        transfer = None
                    if transfer is not None:
                        print 'transfered output path:', path, \
                            'from: %s.%s changes to input.' \
                            % (node.name, param)
                        move_to_input[path] = transfer
                        transfer.initial_status \
                            = swclient.constants.FILES_ON_CLIENT
                    elif path in temp_map:
                        print 'temp path in: %s.%s will not be produced.' \
                            % (node.name, param)
                        remove_temp.add(path)
        return move_to_input, remove_temp

    def workflow_from_graph(graph, temp_map={}, shared_map={},
                            transfers=[{}, {}], shared_paths={},
                            disabled_nodes=set(), forbidden_temp=set(),
                            jobs_priority=0, steps={}, current_step=''):
        """ Convert a CAPSUL graph to a soma-workflow workflow

        Parameters
        ----------
        graph: Graph (mandatory)
            a CAPSUL graph
        temp_map: dict (optional)
            temporary files to replace by soma_workflow TemporaryPath objects
        shared_map: dict (optional)
            shared translated paths maps (global to pipeline).
            This dict is updated when needed during the process.
        transfers: list of 2 dicts (optional)
            File transfers dicts (input / ouput), indexed by process, then by
            file path.
        shared_paths: dict (optional)
            holds information about shared resource paths from soma-worflow
            section in study config.
            If not specified, no translation will be used.
        jobs_priority: int (optional, default: 0)
            set this priority on soma-workflow jobs.
        steps: dict (optional)
            node name -> step name dict
        current_step: str (optional)
            the parent node step name

        Returns
        -------
        workflow: Workflow
            the corresponding soma-workflow workflow
        """
        jobs = {}
        groups = {}
        root_jobs = {}
        dependencies = set()
        group_nodes = {}

        ordered_nodes = graph.topological_sort()
        proc_keys = dict([(node[1] if isinstance(node[1], Graph)
                              else node[1][0].process, i)
                           for i, node in enumerate(ordered_nodes)])

        # Go through all graph nodes
        for node_name, node in graph._nodes.iteritems():
            # If the the node meta is a Graph store it
            if isinstance(node.meta, Graph):
                group_nodes[node_name] = node
            # Otherwise convert all the processes in meta as jobs
            else:
                sub_jobs = {}
                for pipeline_node in node.meta:
                    process = pipeline_node.process
                    if (not isinstance(process, Pipeline) and
                            isinstance(process, Process) and
                            pipeline_node not in disabled_nodes):
                        job = build_job(process, temp_map, shared_map,
                                        transfers, shared_paths,
                                        forbidden_temp=forbidden_temp,
                                        name=pipeline_node.name,
                                        priority=jobs_priority,
                                        step_name=current_step or
                                            steps.get(pipeline_node.name))
                        sub_jobs[process] = job
                        root_jobs[process] = job
                       #node.job = job
                jobs.update(sub_jobs)

        # Recurence on graph node
        for node_name, node in group_nodes.iteritems():
            wf_graph = node.meta
            step_name = current_step or steps.get(node_name, '')
            (sub_jobs, sub_deps, sub_groups, sub_root_jobs) \
                = workflow_from_graph(
                    wf_graph, temp_map, shared_map, transfers,
                    shared_paths, disabled_nodes, jobs_priority=jobs_priority,
                    steps=steps, current_step=step_name)
            group = build_group(node_name, sub_root_jobs.values())
            groups[node.meta] = group
            root_jobs[node.meta] = group
            jobs.update(sub_jobs)
            groups.update(sub_groups)
            dependencies.update(sub_deps)

        # Add dependencies between a source job and destination jobs
        for node_name, node in graph._nodes.iteritems():
            # Source job
            if isinstance(node.meta, list):
                if node.meta[0].process in jobs:
                    sjob = jobs[node.meta[0].process]
                else:
                    continue # disabled node
            else:
                sjob = groups[node.meta]
            # Destination jobs
            for dnode in node.links_to:
                if isinstance(dnode.meta, list):
                    if dnode.meta[0].process in jobs:
                        djob = jobs[dnode.meta[0].process]
                    else:
                        continue # disabled node
                else:
                    djob = groups[dnode.meta]
                dependencies.add((sjob, djob))

        # sort root jobs/groups
        root_jobs_list = [(proc_keys[p], p, j)
                          for p, j in root_jobs.iteritems()]
        root_jobs_list.sort()
        root_jobs = OrderedDict([x[1:] for x in root_jobs_list])
        return jobs, dependencies, groups, root_jobs

    def _create_directories_job(pipeline, shared_map={}, shared_paths={},
                                priority=0, transfer_paths=[]):
        def _is_transfer(d, transfer_paths):
            for path in transfer_paths:
                if d.startswith(os.path.join(path, '')):
                    return True
            return False

        directories = [d
                       for d in pipeline_tools.get_output_directories(
                          pipeline)[1]
                       if not _is_transfer(d, transfer_paths)]
        if len(directories) == 0:
            return None # no dirs to create.
        paths = []
        # check for path translations
        for path in directories:
            new_path = _translated_path(path, shared_map, shared_paths)
            paths.append(new_path or path)
        # FIXME: maybe use a python command to avoid the shell command mkdir
        cmdline = ['mkdir', '-p'] + paths
        job = swclient.Job(
            name='output directories creation',
            command=cmdline,
            priority=priority)
        return job

    # TODO: handle formats in a separate, centralized place
    # formats: {name: ext_props}
    #     ext_props: {ext: [dependent_exts]}
    #     dependent_exts: (ext, mandatory)
    formats = {
        'NIFTI-1': {'.nii': [], '.img': [('.hdr', True)], '.nii.gz': []},
        'GIS': {'.ima': [('.dim', True)]},
        'GIFTI': {'.gii': []},
        'MESH': {'.mesh': []},
        'ARG': {'.arg': [('.data', False)]},
    }
    # transform it to an ext-based dict
    # merged_formats: {ext: [dependent_exts]}
    # (formats names are lost here)
    merged_formats = {}
    for format, values in formats.iteritems():
        merged_formats.update(values)

    temp_map = assign_temporary_filenames(pipeline)
    temp_subst_list = [(x1, x2[0]) for x1, x2 in temp_map.iteritems()]
    temp_subst_map = dict(temp_subst_list)
    shared_map = {}
    swf_paths = _get_swf_paths(study_config)
    transfers = _get_transfers(pipeline, swf_paths[0], merged_formats)
    #print 'disabling nodes:', disabled_nodes
    # get complete list of disabled leaf nodes
    if disabled_nodes is None:
        disabled_nodes = pipeline.disabled_pipeline_steps_nodes()
    disabled_nodes = _expand_nodes(disabled_nodes)
    move_to_input, remove_temp = _handle_disable_nodes(
        pipeline, temp_subst_map, transfers, disabled_nodes)
    #print 'changed transfers:', move_to_input
    #print 'removed temp:', remove_temp
    #print 'temp_map:', temp_map
    #print 'SWF transfers:', swf_paths[0]
    #print 'shared paths:', swf_paths[1]

    if create_directories:
        # create job
        dirs_job = _create_directories_job(
            pipeline, shared_map=shared_map, shared_paths=swf_paths[1],
            transfer_paths=swf_paths[0])

    # build steps map
    steps = {}
    if hasattr(pipeline, 'pipeline_steps'):
        for step_name, step \
                in pipeline.pipeline_steps.user_traits().iteritems():
            nodes = step.nodes
            steps.update(dict([(node, step_name) for node in nodes]))

    # Get a graph
    try:
        graph = pipeline.workflow_graph()
        (jobs, dependencies, groups, root_jobs) = workflow_from_graph(
                  graph, temp_subst_map, shared_map, transfers, swf_paths[1],
                  disabled_nodes=disabled_nodes, forbidden_temp=remove_temp,
                  steps=steps)
    finally:
        restore_empty_filenames(temp_map)

    all_jobs = jobs.values()
    root_jobs = root_jobs.values()

    # if directories have to be created, all other primary jobs will depend
    # on this first one
    if create_directories and dirs_job is not None:
        dependend_jobs = set()
        for dependency in dependencies:
            dependend_jobs.add(dependency[1])
        new_deps = [(dirs_job, job) for job in all_jobs
                    if job not in dependend_jobs]
        dependencies.update(new_deps)
        all_jobs.insert(0, dirs_job)
        root_jobs.insert(0, dirs_job)

    workflow = swclient.Workflow(jobs=all_jobs,
        dependencies=dependencies,
        root_group=root_jobs,
        name=pipeline.name)

    return workflow


def local_workflow_run(workflow_name, workflow):
    """ Create a soma-workflow controller and submit a workflow

    Parameters
    ----------
    workflow_name: str (mandatory)
        the name of the workflow
    workflow: Workflow (mandatory)
        the soma-workflow workflow
    """
    localhost = socket.gethostname()
    controller = swclient.WorkflowController(localhost)
    wf_id = controller.submit_workflow(workflow=workflow, name=workflow_name)
    swclient.Helper.wait_workflow(wf_id, controller)
    return controller, wf_id
