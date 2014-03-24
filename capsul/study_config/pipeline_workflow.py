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
from socket import getfqdn

import soma_workflow.client as swclient

from capsul.pipeline import Pipeline
from capsul.process import Process
from capsul.pipeline.topological_sort import Graph


def workflow_from_pipeline(pipeline):
    """ Create a soma-workflow workflow from a Capsul Pipeline

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        a CAPSUL pipeline

    Returns
    -------
    workflow: Workflow
        a soma-workflow workflow
    """

    def build_job(process):
        """ Create a soma-workflow Job from a Capsul Process

        Parameters
        ----------
        process: Process (mandatory)
            a CAPSUL process instance

        Returns
        -------
        job: Job
            a soma-workflow Job instance that will execute the CAPSUL process
        """
        # Get the process command line
        process_cmdline = process.get_commandline()

        # Return the soma-workflow job
        return swclient.Job(name=process.name, command=process_cmdline)

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

    def workflow_from_graph(graph):
        """ Convert a CAPSUL graph to a soma-workflow workflow

        Parameters
        ----------
        graph: Graph (mandatory)
            a CAPSUL graph

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
                for process in node.meta:
                    if (not isinstance(process, Pipeline) and
                            isinstance(process, Process)):
                        job = build_job(process)
                        sub_jobs[process] = job
                        root_jobs[process] = job
                       #node.job = job
                jobs.update(sub_jobs)

        # Recurence on graph node
        for node_name, node in group_nodes.iteritems():
            wf_graph = node.meta
            (sub_jobs, sub_deps, sub_groups, sub_root_groups,
                       sub_root_jobs) = workflow_from_graph(wf_graph)
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
            if isinstance(node.meta, list) and node.meta[0] in jobs:
                sjob = jobs[node.meta[0]]
            else:
                sjob = groups[node.meta]
            # Destination jobs
            djobs = []
            for dnode in node.links_to:
                if isinstance(dnode.meta, list) and dnode.meta[0] in jobs:
                    djob = jobs[dnode.meta[0]]
                else:
                    djob = groups[dnode.meta]
                dependencies.add((sjob, djob))


        return jobs, dependencies, groups, root_groups, root_jobs

    # Get a graph
    graph = pipeline.workflow_graph()
    (jobs, dependencies, groups, root_groups,
           root_jobs) = workflow_from_graph(graph)

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