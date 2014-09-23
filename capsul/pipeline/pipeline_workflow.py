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
from socket import getfqdn

import soma_workflow.client as swclient

from capsul.pipeline import Pipeline, Switch
from capsul.process import Process
from capsul.pipeline.topological_sort import Graph
from traits.api import Directory, Undefined, File, Str


def workflow_from_pipeline(pipeline, study_config={}):
    """ Create a soma-workflow workflow from a Capsul Pipeline

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        a CAPSUL pipeline
    study_config: StudyConfig (optional), or dict
        holds information about file transfers and shared resource paths.
        If not specified, no translation/transfers will be used.

    Returns
    -------
    workflow: Workflow
        a soma-workflow workflow
    """

    class TempFile(unicode):
        # class needed temporary to identify temporary paths in the pipeline.
        # must inerit a string type since it is used as a trait value
        pass

    def _files_group(path):
        # TODO: handle formats
        return [path]

    def build_job(process, temp_map={}, transfer_map={}, transfers=[{}, {}],
                  swf_paths=([], {})):
        """ Create a soma-workflow Job from a Capsul Process

        Parameters
        ----------
        process: Process (mandatory)
            a CAPSUL process instance
        temp_map: dict (optional)
            temporary paths map.
        transfer_map: dict (optional)
            file transfers and shared translated paths.
            This dict is updated when needed during the process.
        swf_paths: tuple of 2 items (optional)
            holds information about file transfers and shared resource paths.
            If not specified, no translation/transfers will be used.

        Returns
        -------
        job: Job
            a soma-workflow Job instance that will execute the CAPSUL process
        """
        def _replace_in_list(rlist, temp_map):
            for i, item in enumerate(rlist):
                if item in temp_map:
                    value = temp_map[item]
                    if isinstance(value, list):
                        # FileTransfer can have 2 values: input, output
                        if value[0] is None:
                            value = value[1]
                        else:
                            value = value[0]
                    rlist[i] = value
                elif isinstance(item, list) or isinstance(item, tuple):
                    deeperlist = list(item)
                    _replace_in_list(deeperlist, temp_map)
                    rlist[i] = deeperlist

        def _translated_path(path, trait, transfer_map, swf_paths):
            if path is None or path is Undefined \
                    or (not swf_paths[0] and not swf_paths[1]) \
                    or (not isinstance(trait.trait_type, File) \
                    and not isinstance(trait.trait_type, Directory)):
                return None # not a path
            item = transfer_map.get(path)
            output = not not trait.output # trait.output can be None
            if item is not None:
                # already in map
                if isinstance(item, list):
                    # FileTransfer, list for I / O
                    item2 = item[output]
                    if item2 is not None:
                        return item2
                    # must make an opposite I/O
                    item2 = item[not output]
                    item3 = item2.__class__(
                        not output, path, item2.client_paths)
                    item[output] = item3
                    return item3
                # SharedResourcePath in map
                return item

            transfer_paths, tranlate_paths = [], swf_paths[1] # FIXME
            for base_dir in transfer_paths:
                if path.startswith(base_dir + os.sep):
                    item = swclient.FileTransfer(
                        not output, path, _files_group(path))
                    transfer_map.setdefault(path, [None, None])[output] \
                        = item
                    return item
            for namespace, base_dir in tranlate_paths.iteritems():
                if path.startswith(base_dir + os.sep):
                    rel_path = path[len(base_dir)+1:]
                    uuid = path
                    item = swclient.SharedResourcePath(
                        rel_path, namespace, uuid=uuid)
                    transfer_map[path] = item
                    return item
            return None

        # Get the process command line
        process_cmdline = process.get_commandline()

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
                        input_replaced_paths.append(temp_map[value])
                else:
                    translated_path = _translated_path(
                        value, parameter, transfer_map, swf_paths)
                    if isinstance(translated_path, swclient.FileTransfer):
                        if parameter.output:
                            output_replaced_paths.append(translated_path)
                        else:
                            input_replaced_paths.append(translated_path)

        # and replace in commandline
        iproc_transfers = transfers[0].get(process, {})
        oproc_transfers = transfers[1].get(process, {})
        proc_transfers = dict(iproc_transfers)
        proc_transfers.update(oproc_transfers)
        _replace_in_list(process_cmdline, temp_map)
        _replace_in_list(process_cmdline, transfer_map)
        _replace_in_list(process_cmdline, proc_transfers)

        # Return the soma-workflow job
        return swclient.Job(name=process.name,
            command=process_cmdline,
            referenced_input_files=input_replaced_paths + iproc_transfers.values(),
            referenced_output_files=output_replaced_paths + oproc_transfers.values())

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
        resource_conf = resources_conf.get(computing_resource)
        if resource_conf is None:
            return [], {}
        return (
            resource_conf.get('transfer_paths', []),
            resource_conf.get('path_translations', {}))

    def _propagate_transfer(node, param, path, output, transfers,
                            transfer_item):
        plug = None
        if isinstance(node, Switch):
            if output:
                # propagate to active input
                input_param = node.switch + '_switch_' + param
                plug = node.plugs[input_param]
            else:
                output_param = param[len(node.switch + '_switch_'):]
                plug = node.plugs[output_param]
        else:
            process = node.process
            if hasattr(process, 'nodes'):
                # pipeline
                plug = process.nodes[''].plugs.get(param)
            else:
                transfers[output].setdefault(process, {})[path] \
                    = transfer_item
                return

        if plug is None or not plug.enabled or not plug.activated:
            return
        if output:
            links = plug.links_from
        else:
            links = plug.links_to
        for proc_name, param_name, node, plug, act in links:
            if not node.activated or not node.enabled or not plug.activated \
                    or not plug.enabled:
                continue
            _propagate_transfer(node, param_name, path, output, transfers,
                                transfer_item)

    def _get_transfers(pipeline, swf_paths):
        in_transfers = {}
        out_transfers = {}
        transfers = [in_transfers, out_transfers]
        for param, trait in pipeline.user_traits().iteritems():
            if isinstance(trait.trait_type, File) \
                    or isinstance(trait.trait_type, Directory):
                # is value in paths
                path = getattr(pipeline, param)
                if path is None or path is Undefined:
                    continue
                for tpath in swf_paths[0]:
                    output = bool(trait.output)
                    if path.startswith(os.path.join(tpath, '')):
                        transfer_item = swclient.FileTransfer(
                            not output, path, _files_group(path))
                        transfers[output].setdefault(pipeline, {})[path] \
                            = transfer_item
                        _propagate_transfer(pipeline.pipeline_node, param,
                                            path, output, transfers,
                                            transfer_item)
                        break
        return transfers

    def workflow_from_graph(graph, temp_map={}, transfer_map={},
                            transfers=[{}, {}], swf_paths=([], {})):
        """ Convert a CAPSUL graph to a soma-workflow workflow

        Parameters
        ----------
        graph: Graph (mandatory)
            a CAPSUL graph
        temp_map: dict (optional)
            temporary files to replace by soma_workflow TemporaryPath objects
        transfer_map: dict (optional)
            file transfers and shared translated paths.
            This dict is updated when needed during the process.
        swf_paths: tuple of 2 items (optional)
            holds information about file transfers and shared resource paths.
            If not specified, no translation/transfers will be used.

        Returns
        -------
        workflow: Workflow
            the corresponding soma-workflow workflow
        """
        jobs = {}
        groups = {}
        root_jobs = {}
        root_groups = {}
        dependencies = set()
        group_nodes = {}

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
                            isinstance(process, Process)):
                        job = build_job(process, temp_map, transfer_map,
                                        transfers, swf_paths)
                        sub_jobs[process] = job
                        root_jobs[process] = job
                       #node.job = job
                jobs.update(sub_jobs)

        # Recurence on graph node
        for node_name, node in group_nodes.iteritems():
            wf_graph = node.meta
            (sub_jobs, sub_deps, sub_groups, sub_root_groups,
                       sub_root_jobs) = workflow_from_graph(
                          wf_graph, temp_map, transfer_map, transfers,
                          swf_paths)
            group = build_group(node_name,
                sub_root_groups.values() + sub_root_jobs.values())
            groups[node.meta] = group
            root_groups[node.meta] = group
            jobs.update(sub_jobs)
            groups.update(sub_groups)
            dependencies.update(sub_deps)

        # Add dependencies between a source job and destination jobs
        for node_name, node in graph._nodes.iteritems():
            # Source job
            if isinstance(node.meta, list) and node.meta[0].process in jobs:
                sjob = jobs[node.meta[0].process]
            else:
                sjob = groups[node.meta]
            # Destination jobs
            for dnode in node.links_to:
                if isinstance(dnode.meta, list) and dnode.meta[0].process in jobs:
                    djob = jobs[dnode.meta[0].process]
                else:
                    djob = groups[dnode.meta]
                dependencies.add((sjob, djob))

        return jobs, dependencies, groups, root_groups, root_jobs

    temp_map = assign_temporary_filenames(pipeline)
    temp_subst_list = [(x1, x2[0]) for x1, x2 in temp_map.iteritems()]
    temp_subst_map = dict(temp_subst_list)
    transfer_map = {}
    swf_paths = _get_swf_paths(study_config)
    transfers = _get_transfers(pipeline, swf_paths)

    # Get a graph
    graph = pipeline.workflow_graph()
    (jobs, dependencies, groups, root_groups,
           root_jobs) = workflow_from_graph(graph, temp_subst_map,
                                            transfer_map, transfers, swf_paths)

    restore_empty_filenames(temp_map)

    # TODO: root_group would need reordering according to dependencies
    # (maybe using topological_sort)
    workflow = swclient.Workflow(jobs=jobs.values(),
        dependencies=dependencies,
        root_group=root_groups.values() + root_jobs.values(),
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
    localhost = getfqdn().split(".")[0]
    controller = swclient.WorkflowController(localhost)
    wf_id = controller.submit_workflow(workflow=workflow, name=workflow_name)
    swclient.Helper.wait_workflow(wf_id, controller)
