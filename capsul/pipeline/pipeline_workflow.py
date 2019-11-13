##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

"""Capsul Pipeline conversion into soma-workflow workflow.

Standard use case::

    workflow = workflow_from_pipeline(pipeline)
    controller, wf_id = workflow_run(workflow_name, workflow, study_config)

Functions
=========
:func:`workflow_from_pipeline`
------------------------------
:func:`workflow_run`
--------------------
"""

from __future__ import print_function
import os
import socket
import sys
import six
import weakref

import soma_workflow.client as swclient
import soma_workflow.info as swinfo

from capsul.pipeline.pipeline import Pipeline, Switch, PipelineNode
from capsul.pipeline import pipeline_tools
from capsul.process.process import Process
from capsul.pipeline.topological_sort import Graph
from traits.api import Directory, Undefined, File, Str, Any, List
from soma.sorted_dictionary import OrderedDict
from .process_iteration import ProcessIteration
from capsul.attributes import completion_engine_iteration
from capsul.attributes.completion_engine import ProcessCompletionEngine
from capsul.pipeline.pipeline_nodes import ProcessNode


if sys.version_info[0] >= 3:
    xrange = range
    def six_values(container):
        return list(container.values())
else:
    def six_values(container):
        return container.values()


def workflow_from_pipeline(pipeline, study_config=None, disabled_nodes=None,
                           jobs_priority=0, create_directories=True):
    """ Create a soma-workflow workflow from a Capsul Pipeline

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        a CAPSUL pipeline
    study_config: StudyConfig (optional), or dict
        holds information about file transfers and shared resource paths.
        If not specified, it will be accessed through the pipeline.
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

    class TempFile(str):
        # class needed temporary to identify temporary paths in the pipeline.
        # must inherit a string type since it is used as a trait value
        def __init__(self, string=''):
            # in python3 super(..).__init__() cannot take an argument
            # moreover the str value is assigned anyway.
            super(TempFile, self).__init__()
            if isinstance(string, TempFile):
                self.pattern = string.pattern
                self.value = string.value
                self.ref = string.ref if string.ref else string
            else:
                self.pattern = '%s'
                self.value = string
                self.ref = None

        def referent(self):
            return self.ref if self.ref else self

        def get_value(self):
            return self.referent().value

        def __add__(self, other):
            res = TempFile(str(self) + str(other))
            res.pattern = self.pattern + str(other)
            res.value = self.value
            res.ref = self.referent()
            return res

        def __radd__(self, other):
            res = TempFile(str(other) + str(self))
            res.pattern = str(other) + self.pattern
            res.value = self.value
            res.ref = self.referent()
            return res

        def __iadd__(self, other):
            self.pattern += str(other)
            str(TempFile, self).__iadd__(str(other))

        def __str__(self):
            return self.pattern % self.get_value()

        def __hash__(self):
            if self.ref:
                return self.referent().__hash__()
            return super(TempFile, self).__hash__()

        def __eq__(self, other):
            if not isinstance(other, TempFile):
                return False
            return self.referent() is other.referent()


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

        for base_dir, (namespace, uuid) in six.iteritems(shared_paths):
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
        forbidden_temp: dict
            values forbidden for temporary files (?)
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
                    value = value.__class__(value)
                    if hasattr(item, 'pattern'):
                        # temp case (differs from shared case)
                        value.pattern = item.pattern
                    rlist[i] = value
                elif isinstance(item, (list, tuple)):
                    deeperlist = list(item)
                    _replace_in_list(deeperlist, temp_map)
                    rlist[i] = deeperlist
                elif item is Undefined:
                    rlist[i] = ''

        def _replace_in_dict(rdict, temp_map):
            for name, item in six.iteritems(rdict):
                if isinstance(item, (list, tuple)):
                    deeperlist = list(item)
                    _replace_in_list(deeperlist, temp_map)
                    rdict[name] = deeperlist
                elif item in temp_map:
                    value = temp_map[item]
                    value = value.__class__(value)
                    if hasattr(item, 'pattern'):
                        # temp case (differs from shared case)
                        value.pattern = item.pattern
                    rdict[name] = value
                elif item is Undefined:
                    rdict[name] = ''

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
                            print('*** LIST! ***')
                        else:
                            rlist[i] = value
                    param_name = None
                i += 1

        def _replace_dict_transfers(rdict, process, itransfers, otransfers):
            for param_name, item in six.iteritems(rdict):
                transfer = itransfers.get(param_name)
                if transfer is None:
                    transfer = otransfers.get(param_name)
                if transfer is not None:
                    value = transfer[0]
                    if isinstance(item, list) or isinstance(item, tuple):
                        # TODO: handle lists of files [transfers]
                        #deeperlist = list(item)
                        #_replace_in_list(deeperlist, transfers)
                        #rdict[param_name] = deeperlist
                        print('*** LIST! ***')
                    else:
                        rdict[param_name] = value

        job_name = name
        if not job_name:
            job_name = process.name

        # check for special modified paths in parameters
        input_replaced_paths = []
        output_replaced_paths = []
        param_dict = {}
        has_outputs = False
        forbidden_traits = ('nodes_activation', 'selection_changed')
        for param_name, parameter in six.iteritems(process.user_traits()):
            if param_name not in forbidden_traits:
                if parameter.output \
                        and (parameter.input_filename is False
                             or not (isinstance(parameter.trait_type,
                                                (File, Directory))
                                     or (isinstance(parameter.trait_type,
                                                    List)
                                         and isinstance(
                                              parameter.inner_traits[0].trait_type,
                                              (File, Directory))))):
                    has_outputs = True
                value = getattr(process, param_name)
                if isinstance(value, list):
                    values = value
                else:
                    values = [value]
                for value in values:
                    if isinstance(value, TempFile):
                        # duplicate swf temp and copy pattern into it
                        tval = temp_map[value]
                        tval = tval.__class__(tval)
                        tval.pattern = value.pattern
                        if parameter.output:
                            output_replaced_paths.append(tval)
                        else:
                            if value in forbidden_temp:
                                raise ValueError(
                                    'Temporary value used cannot be generated '
                                    'in the workflkow: %s.%s'
                                    % (job_name, param_name))
                            input_replaced_paths.append(tval)
                    else:
                        _translated_path(value, shared_map, shared_paths,
                                        parameter)

        # Get the process command line
        #process_cmdline = process.get_commandline()
        process_cmdline = process.params_to_command()
        # and replace in commandline
        iproc_transfers = transfers[0].get(process, {})
        oproc_transfers = transfers[1].get(process, {})
        #proc_transfers = dict(iproc_transfers)
        #proc_transfers.update(oproc_transfers)
        _replace_in_list(process_cmdline, temp_map)
        _replace_in_list(process_cmdline, shared_map)
        _replace_transfers(
            process_cmdline, process, iproc_transfers, oproc_transfers)

        use_input_params_file = False
        if process_cmdline[0] == 'capsul_job':
            python_command = os.path.basename(sys.executable)
            process_cmdline = [
                'capsul_job', python_command, '-c',
                'from capsul.api import Process; '
                'Process.run_from_commandline("%s")' % process_cmdline[1]]
            use_input_params_file = True
            param_dict = process.export_to_dict()
        elif process_cmdline[0] == 'json_job':
            use_input_params_file = True
        for name in forbidden_traits:
            if name in param_dict:
                del param_dict[name]

        _replace_in_dict(param_dict, temp_map)
        _replace_in_dict(param_dict, shared_map)
        _replace_dict_transfers(
            param_dict, process, iproc_transfers, oproc_transfers)

        # handle native specification (cluster-specific specs as in
        # soma-workflow)
        native_spec = getattr(process, 'native_specification', None)
        # Return the soma-workflow job
        job = swclient.Job(
            name=job_name,
            command=process_cmdline[1:],
            referenced_input_files
                =input_replaced_paths \
                    + [x[0] for x in iproc_transfers.values()],
            referenced_output_files
                =output_replaced_paths \
                    + [x[0] for x in oproc_transfers.values()],
            priority=priority,
            native_specification=native_spec,
            param_dict=param_dict,
            use_input_params_file=use_input_params_file,
            has_outputs=has_outputs)
        # print('job command:', job.command)
        # handle parallel job info (as in soma-workflow)
        parallel_job_info = getattr(process, 'parallel_job_info', None)
        if parallel_job_info:
            job.parallel_job_info = parallel_job_info
        if step_name:
            job.user_storage = step_name
        # associate job with process
        job.process = weakref.ref(process)
        job._do_not_pickle = ['process']
        job.process_hash = id(process)
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

    def assign_temporary_filenames(pipeline, count_start=0):
        ''' Find and temporarily assign necessary temporary file names'''
        temp_filenames = pipeline.find_empty_parameters()
        temp_map = {}
        count = count_start
        for node, plug_name, optional in temp_filenames:
            if hasattr(node, 'process'):
                process = node.process
            else:
                process = node
            trait = process.trait(plug_name)
            is_list = isinstance(trait.trait_type, List)
            values = []
            if is_list:
                todo = getattr(process, plug_name)
                trait = trait.inner_traits[0]
            else:
                todo = [Undefined]
            for item in todo:
                if item not in (Undefined, '', None):
                    # non-empty list element
                    values.append(item)
                    continue
                is_directory = isinstance(trait.trait_type, Directory)
                if trait.allowed_extensions:
                    suffix = trait.allowed_extensions[0]
                else:
                    suffix = ''
                swf_tmp = swclient.TemporaryPath(is_directory=is_directory,
                    suffix=suffix, name='temporary_%d' % count)
                tmp_file = TempFile('%d' % count)
                count += 1
                temp_map[tmp_file] = (swf_tmp, node, plug_name, optional)
                values.append(tmp_file)
            # set a TempFile value to identify the params / value
            if is_list:
                setattr(process, plug_name, values)
            else:
                setattr(process, plug_name, values[0])
        return temp_map

    def restore_empty_filenames(temporary_map):
      ''' Set back Undefined values to temporarily assigned file names (using
      assign_temporary_filenames()
      '''
      for tmp_file, item in six.iteritems(temporary_map):
          node, plug_name = item[1:3]
          if hasattr(node, 'process'):
              process = node.process
          else:
              process = node
          value = getattr(process, plug_name)
          if isinstance(value, list):
              # FIXME TODO: only restore values in list which correspond to
              # a temporary.
              # Problem: they are sometimes transformed into strings
              # FIXME: several temp items can be part of the same list,
              # so this assignment is likely to be done several times.
              # It could probably be optimized.
              # WARNING: we set "" values instead of Undefined because they may
              # be mandatory
              setattr(process, plug_name, [''] * len(value))
          else:
              setattr(process, plug_name, Undefined)

    def _get_swf_paths(study_config):
        computing_resource = getattr(
            study_config, 'somaworkflow_computing_resource', None)
        if computing_resource in (None, Undefined):
            return [], {}
        resources_conf = getattr(
            study_config, 'somaworkflow_computing_resources_config', None)
        if resources_conf in (None, Undefined):
            return [], {}
        resource_conf = getattr(resources_conf, computing_resource, None)
        if resource_conf in (None, Undefined):
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
            for param, trait in six.iteritems(process.user_traits()):
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
                               for name, sub_node
                                  in six.iteritems(process.nodes)
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
                nodes_list.extend([p for p
                                   in six.itervalues(node.process.nodes)
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
            for param, trait in six.iteritems(process.user_traits()):
                if trait.output and (isinstance(trait.trait_type, File) \
                        or isinstance(trait.trait_type, Directory) \
                        or type(trait.trait_type) is Any):
                    path = getattr(process, param)
                    if otrans is not None:
                        transfer, path2 = otrans.get(param, (None, None))
                    else:
                        transfer = None
                    if transfer is not None:
                        print('transfered output path:', path,
                              'from: %s.%s changes to input.'
                              % (node.name, param))
                        move_to_input[path] = transfer
                        transfer.initial_status \
                            = swclient.constants.FILES_ON_CLIENT
                    elif path in temp_map:
                        print('temp path in: %s.%s will not be produced.'
                              % (node.name, param))
                        remove_temp.add(path)
        return move_to_input, remove_temp

    def iter_to_workflow(process, node_name, step_name, temp_map,
                         shared_map, transfers, shared_paths,
                         disabled_nodes, remove_temp,
                         steps, study_config, iteration):
        '''
        Build a workflow for a single iteration step of a process/sub-pipeline

        is called for each iteration by build_iteration()

        Returns
        -------
        (jobs, dependencies, groups, root_jobs, links)
        '''
        if isinstance(process, Pipeline):
            temp_map2 = assign_temporary_filenames(process, len(temp_map))
            temp_subst_list = [(x1, x2[0]) for x1, x2
                                  in six.iteritems(temp_map2)]
            temp_subst_map = dict(temp_subst_list)
            temp_subst_map.update(temp_map)
            try:
                graph = process.workflow_graph()
                (jobs, dependencies, groups, sub_root_jobs, links) = \
                    workflow_from_graph(
                        graph, temp_subst_map, shared_map, transfers,
                        shared_paths, disabled_nodes=disabled_nodes,
                        forbidden_temp=remove_temp, steps=steps,
                        study_config=study_config)
                group = build_group(node_name, six_values(sub_root_jobs))
                groups[(process, iteration)] = group
                root_jobs = {(process, iteration): group}
            finally:
                restore_empty_filenames(temp_map2)
        elif isinstance(process, ProcessIteration):
            # sub-iteration
            return build_iteration(process, step_name, study_config)
        else:
            # single process
            job = build_job(process, temp_map, shared_map,
                            transfers, shared_paths,
                            forbidden_temp=remove_temp,
                            name=node_name,
                            priority=jobs_priority,
                            step_name=step_name)
            jobs = {(process, iteration): job}
            groups = {}
            dependencies = {}
            links = {}
            root_jobs = {(process, iteration): job}

        return (jobs, dependencies, groups, root_jobs, links)

    def build_iteration(it_process, step_name, temp_map,
                        shared_map, transfers, shared_paths, disabled_nodes,
                        remove_temp, steps, study_config={}):
        '''
        Build workflow for an iterative process: the process / sub-pipeline is
        filled with appropriate parameters for each iteration, and its
        workflow is generated.

        Returns
        -------
        (jobs, dependencies, groups, root_jobs, links)
        '''
        no_output_value = None
        size = None
        size_error = False
        for parameter in it_process.iterative_parameters:
            trait = it_process.trait(parameter)
            psize = len(getattr(it_process, parameter))
            if psize:
                if size is None:
                    size = psize
                elif size != psize:
                    size_error = True
                    break
                if trait.output:
                    if no_output_value is None:
                        no_output_value = False
                    elif no_output_value:
                        size_error = True
                        break
            else:
                if trait.output:
                    if no_output_value is None:
                        no_output_value = True
                    elif not no_output_value:
                        size_error = True
                        break
                else:
                    if size is None:
                        size = psize
                    elif size != psize:
                        size_error = True
                        break

        if size_error:
            raise ValueError('Iterative parameter values must be lists of the '
                'same size: %s' % ','.join('%s=%d'
                    % (n, len(getattr(it_process, n)))
                    for n in it_process.iterative_parameters))

        jobs = {}
        workflows = []
        for parameter in it_process.regular_parameters:
            setattr(it_process.process, parameter,
                    getattr(it_process, parameter))

        jobs = {}
        dependencies = set()
        groups = {}
        root_jobs = {}
        links = {}

        if size == 0:
            return (jobs, dependencies, groups, root_jobs)

        if no_output_value:
            # this case is a "really" dynamic iteration, the number of
            # iterations and parameters are determined in runtime, so we
            # cannot handle it at the moment.
            raise ValueError('Dynamic iteration is not handled in this '
                'version of CAPSUL / Soma-Workflow')

            for parameter in it_process.iterative_parameters:
                trait = it_process.trait(parameter)
                if trait.output:
                    setattr(it_process, parameter, [])
            outputs = {}
            for iteration in xrange(size):
                for parameter in it_process.iterative_parameters:
                    if not no_output_value \
                            or not it_process.trait(parameter).output:
                        setattr(it_process.process, parameter,
                                getattr(it_process, parameter)[iteration])

                # operate completion
                complete_iteration(it_process, iteration)

                #workflow = workflow_from_pipeline(it_process.process,
                                                  #study_config=study_config)
                #workflows.append(workflow)

                for parameter in it_process.iterative_parameters:
                    trait = it_process.trait(parameter)
                    if trait.output:
                        outputs.setdefault(
                            parameter,[]).append(getattr(it_process.process,
                                                         parameter))
            for parameter, value in six.iteritems(outputs):
                setattr(it_process, parameter, value)
        else:
            for iteration in xrange(size):
                for parameter in it_process.iterative_parameters:
                    setattr(it_process.process, parameter,
                            getattr(it_process, parameter)[iteration])

                # operate completion
                complete_iteration(it_process, iteration)

                process_name = it_process.process.name + '_%d' % iteration
                (sub_jobs, sub_dependencies, sub_groups, sub_root_jobs,
                 sub_links) = \
                    iter_to_workflow(it_process.process, process_name,
                        step_name,
                        temp_map, shared_map, transfers,
                        shared_paths, disabled_nodes, remove_temp, steps,
                        study_config, iteration)
                jobs.update(dict([((p, iteration), j)
                                  for p, j in six.iteritems(sub_jobs)]))
                dependencies.update(sub_dependencies)
                groups.update(sub_groups)
                root_jobs.update(sub_root_jobs)
                links.update(sub_links)

        return (jobs, dependencies, groups, root_jobs, links)


    def complete_iteration(it_process, iteration):
        completion_engine = ProcessCompletionEngine.get_completion_engine(
            it_process)
        # check if it is an iterative completion engine
        if hasattr(completion_engine, 'complete_iteration_step'):
            completion_engine.complete_iteration_step(iteration)


    def workflow_from_pipeline_structure(
            pipeline, temp_map={}, shared_map={},
            transfers=[{}, {}], shared_paths={},
            disabled_nodes=set(), forbidden_temp=set(),
            jobs_priority=0, steps={}, current_step='',
            study_config={}, with_links=True):
        """ Convert a CAPSUL graph to a soma-workflow workflow

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            a CAPSUL pipeline
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
        study_config: StydyConfig instance (optional)
            used only for iterative nodes, to be passed to create sub-workflows

        Returns
        -------
        workflow: tuple (jobs, dependencies, groups, root_jobs, links, nodes)
            the corresponding soma-workflow workflow definition (to be passed
            to Workflow constructor)
        """
        def _update_links(links1, links2):
            for dest_node, slink in six.iteritems(links2):
                nlink = links1.setdefault(dest_node, {})
                nlink.update(slink)

        jobs = {}
        groups = {}
        root_jobs = {}
        dependencies = set()
        group_nodes = {}
        links = {}

        nodes = [(pipeline, node_name, node)
                 for node_name, node in six.iteritems(pipeline.nodes)
                 if node.activated and node.enabled
                    and node is not pipeline.pipeline_node
                    and isinstance(node, ProcessNode)]
        all_nodes = list(nodes)

        # Go through all graph nodes
        #while nodes:
        for node_desc in nodes:

            #n_pipeline, node_name, node = nodes.pop(0)
            n_pipeline, node_name, node = node_desc

            if node in disabled_nodes or not node.enabled \
                    or not node.activated:
                continue

            if isinstance(node, PipelineNode):
                # sub-pipeline
                group_nodes[node_name] = node
                #nodes += [(node.process, snode_name, snode)
                          #for snode_name, snode
                              #in six.iteritems(node.process.nodes)
                          #if snode is not node.process.pipeline_node]

                step_name = current_step or steps.get(node_name, '')
                (sub_jobs, sub_deps, sub_groups, sub_root_jobs, sub_links,
                 sub_nodes) \
                    = workflow_from_pipeline_structure(
                        node.process, temp_map, shared_map, transfers,
                        shared_paths, disabled_nodes,
                        jobs_priority=jobs_priority,
                        steps=steps, current_step=step_name, with_links=False)
                group = build_group(node_name, six_values(sub_root_jobs))
                groups[node] = group
                root_jobs[node] = [group]
                jobs.update(sub_jobs)
                groups.update(sub_groups)
                dependencies.update(sub_deps)
                all_nodes += sub_nodes
                #_update_links(links, sub_links)
            # Otherwise convert all the processes to jobs
            else:
                sub_jobs = {}
                process = None
                if isinstance(node, Process):
                    process = node
                elif hasattr(node, 'process'):
                    # process node
                    process = node.process
                if process:
                    step_name = current_step or steps.get(node.name)
                    if isinstance(process, ProcessIteration):
                        # iterative node
                        group_nodes.setdefault(
                            node_name, []).append(node)
                        sub_workflows = build_iteration(
                            process, step_name, temp_map,
                            shared_map, transfers, shared_paths,
                            disabled_nodes,
                            {}, steps, study_config={})
                        (sub_jobs, sub_deps, sub_groups, sub_root_jobs,
                         sub_links, sub_nodes) = sub_workflows
                        group = build_group(node_name,
                                            six_values(sub_root_jobs))
                        groups.setdefault(process, []).append(group)
                        root_jobs.setdefault(process, []).append(group)
                        groups.update(sub_groups)
                        jobs.update(sub_jobs)
                        dependencies.update(sub_deps)
                        all_nodes += sub_nodes
                        #_update_links(links, sub_links)
                    else:
                        job = build_job(process, temp_map, shared_map,
                                        transfers, shared_paths,
                                        forbidden_temp=forbidden_temp,
                                        name=node.name,
                                        priority=jobs_priority,
                                        step_name=step_name)
                        sub_jobs[process] = job
                        root_jobs[process] = [job]
                jobs.update(sub_jobs)

        # links / dependencies
        if with_links:
            for node_desc in all_nodes:
                # TODO iterations
                pipeline, node_name, node = node_desc
                for param, plug in six.iteritems(node.plugs):
                    source = pipeline_tools.where_is_plug_value_from(plug,
                                                                     True)
                    if source != (None, None, None):
                        snode, param_name, parent = source
                        process = getattr(snode, 'process', snode)
                        if not isinstance(snode, ProcessNode):
                            # the node is a custom node. Add deps to all
                            # upstream nodes
                            new_nodes = [snode]
                            while new_nodes:
                                mnode = new_nodes.pop(0)
                                moredep = [
                                    pipeline_tools.where_is_plug_value_from(
                                        mlink[3], True)
                                    for mplug in mnode.plugs.values()
                                    for mlink in mplug.links_from
                                    if not mplug.output
                                ]
                                dependencies.update(
                                    [(x[0].process, node.process)
                                     for x in moredep
                                     if isinstance(x[0], ProcessNode)])
                                new_nodes += [x[0] for x in moredep
                                              if x[0] is not None
                                                  and not isinstance(
                                                      x[0], ProcessNode)]
                        else:  # ProcessNode
                            dependencies.add((jobs[process],
                                              jobs[node.process]))
                            trait = process.trait(param_name)
                            if trait.input_filename is False \
                                    or (not isinstance(trait.trait_type,
                                                      (File, Directory)) \
                                        and (not isinstance(trait.trait_type,
                                                            List)
                                            or not isinstance(
                                                trait.inner_traits[0],
                                                (File, Directory)))):
                                links.setdefault(node.process, {}).setdefault(
                                    param, (process, param_name))

        return jobs, dependencies, groups, root_jobs, links, all_nodes


    def workflow_from_graph(graph, temp_map={}, shared_map={},
                            transfers=[{}, {}], shared_paths={},
                            disabled_nodes=set(), forbidden_temp=set(),
                            jobs_priority=0, steps={}, current_step='',
                            study_config={}):
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
        study_config: StydyConfig instance (optional)
            used only for iterative nodes, to be passed to create sub-workflows

        Returns
        -------
        workflow: tuple (jobs, dependencies, groups, root_jobs, links)
            the corresponding soma-workflow workflow definition (to be passed
            to Workflow constructor)
        """
        def _update_links(links1, links2):
            for dest_node, slink in six.iteritems(links2):
                nlink = links1.setdefault(dest_node, {})
                nlink.update(slink)

        jobs = {}
        groups = {}
        root_jobs = {}
        dependencies = set()
        group_nodes = {}
        links = {}

        ordered_nodes = graph.topological_sort()
        proc_keys = dict([(node[1] if isinstance(node[1], Graph)
                              else node[1][0].process, i)
                           for i, node in enumerate(ordered_nodes)])

        # Go through all graph nodes
        for node_name, node in six.iteritems(graph._nodes):
            # If the the node meta is a Graph store it
            if isinstance(node.meta, Graph):
                group_nodes[node_name] = node
            # Otherwise convert all the processes in meta as jobs
            else:
                sub_jobs = {}
                for pipeline_node in node.meta:
                    process = pipeline_node.process
                    if pipeline_node in disabled_nodes:
                        continue
                    step_name = current_step or steps.get(pipeline_node.name)
                    if isinstance(process, ProcessIteration):
                        # iterative node
                        group_nodes.setdefault(
                            node_name, []).append(pipeline_node)
                    elif (not isinstance(process, Pipeline) and
                            isinstance(process, Process)):
                        job = build_job(process, temp_map, shared_map,
                                        transfers, shared_paths,
                                        forbidden_temp=forbidden_temp,
                                        name=pipeline_node.name,
                                        priority=jobs_priority,
                                        step_name=step_name)
                        sub_jobs[process] = job
                        root_jobs[process] = [job]
                        #node.job = job
                jobs.update(sub_jobs)

        # Recurrence on graph node
        for node_name, node in six.iteritems(group_nodes):
            if isinstance(node, list):
                # iterative nodes
                for i, it_node in enumerate(node):
                    process = it_node.process
                    sub_workflows = build_iteration(
                        process, step_name, temp_map,
                        shared_map, transfers, shared_paths, disabled_nodes,
                        {}, steps, study_config={})
                    (sub_jobs, sub_deps, sub_groups, sub_root_jobs,
                     sub_links) = sub_workflows
                    group = build_group(node_name, six_values(sub_root_jobs))
                    groups.setdefault(process, []).append(group)
                    root_jobs.setdefault(process, []).append(group)
                    groups.update(sub_groups)
                    jobs.update(sub_jobs)
                    dependencies.update(sub_deps)
                    _update_links(links, sub_links)
            else:
                # sub-pipeline
                wf_graph = node.meta
                step_name = current_step or steps.get(node_name, '')
                (sub_jobs, sub_deps, sub_groups, sub_root_jobs, sub_links) \
                    = workflow_from_graph(
                        wf_graph, temp_map, shared_map, transfers,
                        shared_paths, disabled_nodes,
                        jobs_priority=jobs_priority,
                        steps=steps, current_step=step_name)
                group = build_group(node_name, six_values(sub_root_jobs))
                groups[node.meta] = group
                root_jobs[node.meta] = [group]
                jobs.update(sub_jobs)
                groups.update(sub_groups)
                dependencies.update(sub_deps)
                _update_links(links, sub_links)

        # Add dependencies between a source job and destination jobs
        for node_name, node in six.iteritems(graph._nodes):
            # Source job
            if isinstance(node.meta, list):
                if isinstance(node.meta[0].process, ProcessIteration):
                    sjobs = groups.get(node.meta[0].process)
                    if not sjobs:
                        continue # disabled
                elif node.meta[0].process in jobs:
                    sjobs = [jobs[node.meta[0].process]]
                else:
                    continue # disabled node
            else:
                sjobs = [groups[node.meta]]
            # Destination jobs
            for dnode in node.links_to:
                if isinstance(dnode.meta, list):
                    if isinstance(dnode.meta[0].process, ProcessIteration):
                        djobs = groups.get(dnode.meta[0].process)
                        if not djobs:
                            continue # disabled
                    elif dnode.meta[0].process in jobs:
                        djobs = [jobs[dnode.meta[0].process]]
                    else:
                        continue # disabled node
                else:
                    djobs = groups[dnode.meta]
                    if not isinstance(djobs, list):
                        djobs = [djobs]
                for djob in djobs:
                    dependencies.update([(sjob, djob) for sjob in sjobs])

        # sort root jobs/groups
        root_jobs_list = []
        for p, js in six.iteritems(root_jobs):
            root_jobs_list.extend([(proc_keys[p], p, j) for j in js])
        root_jobs_list.sort()
        root_jobs = OrderedDict([x[1:] for x in root_jobs_list])
        _update_links(links, graph.param_links)
        return jobs, dependencies, groups, root_jobs, links

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
        # use a python command to avoid the shell command mkdir
        cmdline = ['python', '-c',
                   'import sys, os; [os.makedirs(p) if not os.path.exists(p) '
                   'else None '
                   'for p in sys.argv[1:]]'] \
                  + paths

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
    for format, values in six.iteritems(formats):
        merged_formats.update(values)

    if study_config is None:
        study_config = pipeline.get_study_config()

    USE_NEW_WORKFLOW = False

    if not isinstance(pipeline, Pipeline):
        # "pipeline" is actally a single process (or should, if it is not a
        # pipeline). Get it into a pipeine (with a single node) to make the
        # workflow.
        new_pipeline = Pipeline()
        new_pipeline.set_study_config(study_config)
        new_pipeline.add_process('main', pipeline)
        new_pipeline.autoexport_nodes_parameters()
        pipeline = new_pipeline
    temp_map = assign_temporary_filenames(pipeline)
    temp_subst_list = [(x1, x2[0]) for x1, x2 in six.iteritems(temp_map)]
    temp_subst_map = dict(temp_subst_list)
    shared_map = {}

    swf_paths = _get_swf_paths(study_config)
    transfers = _get_transfers(pipeline, swf_paths[0], merged_formats)
    #print('disabling nodes:', disabled_nodes)
    # get complete list of disabled leaf nodes
    if disabled_nodes is None:
        disabled_nodes = pipeline.disabled_pipeline_steps_nodes()
    disabled_nodes = disabled_nodes \
        + [name for name, node in six.iteritems(pipeline.nodes)
           if node.node_type != 'processing_node'
              and name not in disabled_nodes]
    disabled_nodes = _expand_nodes(disabled_nodes)
    move_to_input, remove_temp = _handle_disable_nodes(
        pipeline, temp_subst_map, transfers, disabled_nodes)
    #print('changed transfers:', move_to_input)
    #print('removed temp:', remove_temp)
    #print('temp_map:', temp_map, '\n')
    #print('SWF transfers:', swf_paths[0])
    #print('shared paths:', swf_paths[1])

    if create_directories:
        # create job
        dirs_job = _create_directories_job(
            pipeline, shared_map=shared_map, shared_paths=swf_paths[1],
            transfer_paths=swf_paths[0])

    # build steps map
    steps = {}
    if hasattr(pipeline, 'pipeline_steps'):
        for step_name, step \
                in six.iteritems(pipeline.pipeline_steps.user_traits()):
            nodes = step.nodes
            steps.update(dict([(node, step_name) for node in nodes]))

    # Get a graph
    try:
        if USE_NEW_WORKFLOW:
            (jobs, dependencies, groups, root_jobs, links, nodes) \
                = workflow_from_pipeline_structure(
                    pipeline, temp_subst_map, shared_map, transfers,
                    swf_paths[1],
                    disabled_nodes=disabled_nodes, forbidden_temp=remove_temp,
                    steps=steps, study_config=study_config)
        else:
            graph = pipeline.workflow_graph()
            (jobs, dependencies, groups, root_jobs, links) \
                = workflow_from_graph(
                    graph, temp_subst_map, shared_map, transfers, swf_paths[1],
                    disabled_nodes=disabled_nodes, forbidden_temp=remove_temp,
                    steps=steps, study_config=study_config)
    finally:
        restore_empty_filenames(temp_map)

    # post-process links to replace nodes with jobs
    param_links = {}
    # expand jobs map because jobs keys may be tuples (for iterations)
    jobs_map = {}
    for process, job in six.iteritems(jobs):
        while isinstance(process, tuple):
            process = process[0]
        jobs_map.setdefault(process, []).append(job)
    if USE_NEW_WORKFLOW:
        for dnode, dlinks in six.iteritems(links):
            if isinstance(dnode, (Pipeline, ProcessIteration)):
                continue  # FIXME handle this
            djlinks = {}
            for param, link in six.iteritems(dlinks):
                if not isinstance(link[0], (Pipeline, ProcessIteration)):
                    # FIXME handle ProcessIteration cases
                    for job in jobs_map[link[0]]:
                        djlinks[param] = (job, link[1])
            for job in jobs_map[dnode]:
                param_links[job] = djlinks
    else:
        for dnode, dlinks in six.iteritems(links):
            if dnode is pipeline.pipeline_node:
                continue  # skip pipeline node
            if isinstance(dnode.process, (Pipeline, ProcessIteration)):
                continue  # FIXME handle this
            djlinks = {}
            for param, link in six.iteritems(dlinks):
                if not isinstance(link[0].process,
                                  (Pipeline, ProcessIteration)):
                    # FIXME handle Pipeline and ProcessIteration cases
                    for job in jobs_map[link[0].process]:
                        djlinks[param] = (job, link[1])
            for job in jobs_map[dnode.process]:
                param_links[job] = djlinks

    all_jobs = six_values(jobs)
    if USE_NEW_WORKFLOW:
        root_jobs = sum(six_values(root_jobs), [])
    else:
        root_jobs = six_values(root_jobs)

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
        name=pipeline.name,
        param_links=param_links)

    # mark workflow with pipeline
    workflow.pipeline = weakref.ref(pipeline)
    workflow._do_not_pickle = ['pipeline']

    return workflow


def workflow_run(workflow_name, workflow, study_config):
    """ Create a soma-workflow controller and submit a workflow

    Parameters
    ----------
    workflow_name: str (mandatory)
        the name of the workflow
    workflow: Workflow (mandatory)
        the soma-workflow workflow
    study_config: StudyConfig (mandatory)
        contains needed configuration through the SomaWorkflowConfig module
    """
    swm = study_config.modules['SomaWorkflowConfig']
    swm.connect_resource()
    controller = swm.get_workflow_controller()
    resource_id = swm.get_resource_id()
    queue = None
    if hasattr(study_config.somaworkflow_computing_resources_config,
               resource_id):
        res_conf = getattr(
            study_config.somaworkflow_computing_resources_config, resource_id)
        queue = res_conf.queue
        if queue is Undefined:
            queue = None
    wf_id = controller.submit_workflow(workflow=workflow, name=workflow_name,
                                       queue=queue)
    swclient.Helper.transfer_input_files(wf_id, controller)
    swclient.Helper.wait_workflow(wf_id, controller)

    # get output values
    pipeline = getattr(workflow, 'pipeline', None)
    if pipeline:
        pipeline = pipeline()  # dereference the weakref
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
                    process = proc_map[job.process_hash]
                    process.import_from_dict(out_params)

    # TODO: should we transfer if the WF fails ?
    swclient.Helper.transfer_output_files(wf_id, controller)
    return controller, wf_id
