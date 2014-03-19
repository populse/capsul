#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging

try:
    import traits.api as traits
    from traits.api import (File, Float, Enum, Str, Int, Bool, List, Tuple,
        Instance, Any, Event, CTrait, Directory)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import (File, Float, Enum, Str, Int, Bool,
        List, Tuple, Instance, Any, Event, CTrait, Directory)

from capsul.controller import Controller
from capsul.utils.sorted_dictionary import SortedDictionary
from capsul.process import Process

from topological_sort import GraphNode, Graph

from pipeline_nodes import (Plug, ProcessNode, PipelineNode,
                            Switch)


class Pipeline(Process):
    """ Pipeline containing Process nodes, and links between node parameters.
    """

    selection_changed = Event()

    def __init__(self, **kwargs):
        super(Pipeline, self).__init__(**kwargs)
        super(Pipeline, self).add_trait('nodes_activation',
                                        Instance(Controller))
        self.list_process_in_pipeline = []
        self.attributes = {}
        self.nodes_activation = Controller()
        self.nodes = SortedDictionary()
        self.node_position = {}
        self.pipeline_node = PipelineNode(self, '', self)
        self.nodes[''] = self.pipeline_node
        self.do_not_export = set()
        self.pipeline_definition()

        self.workflow_repr = ""
        self.workflow_list = []

        for node_name, node in self.nodes.iteritems():
            for parameter_name, plug in node.plugs.iteritems():
                if parameter_name in ('nodes_activation', 'selection_changed'):
                    continue
                if ((node_name, parameter_name) not in self.do_not_export and
                    not plug.links_to and not plug.links_from and not
                   self.nodes[node_name].get_trait(parameter_name).optional):
                    self.export_parameter(node_name, parameter_name)

        self.update_nodes_and_plugs_activation()

    def add_trait(self, name, trait):
        '''
        '''
        super(Pipeline, self).add_trait(name, trait)
        self.get(name)

        if self.is_user_trait(trait):
            # hack
            #output = isinstance(trait, File) and bool(trait.output)
            output = bool(trait.output)
            plug = Plug(output=output)
            self.pipeline_node.plugs[name] = plug

            plug.on_trait_change(self.update_nodes_and_plugs_activation,
                                 'enabled')

    def add_process(self, name, process, do_not_export=None,
                    make_optional=None, **kwargs):
        '''Add a new node in the pipeline

        Parameters
        ----------
        name: str
        process: Process
        do_not_export: bool, optional
        '''
        make_optional = set(make_optional or [])
        do_not_export = set(do_not_export or [])
        do_not_export.update(kwargs)
        if name in self.nodes:
            raise ValueError('Pipeline cannot have two nodes with the'
                             'same name : %s' % name)
        self.nodes[name] = node = ProcessNode(self, name, process, **kwargs)
        for parameter_name in self.nodes[name].plugs:
            if (parameter_name in do_not_export or
                parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))
            if parameter_name in make_optional:
                # if do_not_export, set plug optional setting to True
                self.nodes[name].plugs[parameter_name].optional = True
        self.nodes_activation.add_trait(name, Bool)
        setattr(self.nodes_activation, name, node.enabled)
        self.nodes_activation.on_trait_change(self._set_node_enabled, name)
        self.list_process_in_pipeline.append(process)

    def add_switch(self, name, inputs, outputs):
        '''Add a switch node in the pipeline

        Parameters
        ----------
        name: str
            name for the switch node
        inputs: list of str
            names for switch inputs. Switch activation will select amongst
            them.
            Inputs names will actually be a combination of input and output,
            in the shape "input-output".
            This behaviour is needed when there are several outputs, and thus
            several input groups.
        outputs: list of str
            names for outputs.

        Examples
        --------
        >>> pipeline.add_switch('group_switch', ['in1', 'in2'],
            ['out1', 'out2'])

        will create a switch with 4 inputs and 2 outputs:
        inputs: "in1-out1", "in2-out1", "in1-out2", "in2-out2"
        outputs: "out1", "out2"
        '''
        if name in self.nodes:
            raise ValueError('Pipeline cannot have two nodes with the same '
                             'name : %s' % name)
        node = Switch(self, name, inputs, outputs)
        self.nodes[name] = node
        self.export_parameter(name, 'switch', name)

    def parse_link(self, link):
        source, dest = link.split('->')
        source_node_name, source_parameter, source_node, source_plug = \
            self.parse_parameter(source)
        dest_node_name, dest_parameter, dest_node, dest_plug = \
            self.parse_parameter(dest)
        return (source_node_name, source_parameter, source_node, source_plug,
                dest_node_name, dest_parameter, dest_node, dest_plug)

    def parse_parameter(self, name):
        dot = name.find('.')
        if dot < 0:
            node_name = ''
            node = self.pipeline_node
            parameter_name = name
        else:
            node_name = name[:dot]
            node = self.nodes.get(node_name)
            if node is None:
                raise ValueError('%s is not a valid node name' % node_name)
            parameter_name = name[dot + 1:]
        if parameter_name not in node.plugs:
            raise ValueError('%s is not a valid parameter name for node %s' %
                             (parameter_name, (node_name if node_name else
                                               'pipeline')))
        return node_name, parameter_name, node, node.plugs[parameter_name]

    def add_link(self, link, weak_link=False):
        '''Add a link between pipeline nodes

        Parameters
        ----------
        link: str
          link description. Its shape should be:
          "node.output->other_node.input".
          If no node is specified, the pipeline itself is assumed.
        '''
        source, dest = link.split('->')
        source_node_name, source_parameter, source_node, source_plug = \
            self.parse_parameter(source)
        dest_node_name, dest_parameter, dest_node, dest_plug = \
            self.parse_parameter(dest)
        if not source_plug.output and source_node is not self.pipeline_node:
            raise ValueError('Cannot link from an input plug : %s' % link)
        # hack: cant link output parameters
        if dest_plug.output and dest_node is not self.pipeline_node:
            raise ValueError('Cannot link to an output plug : %s' % link)

        source_plug.links_to.add((dest_node_name, dest_parameter, dest_node,
                                  dest_plug, weak_link))
        dest_plug.links_from.add((source_node_name, source_parameter,
                                  source_node, source_plug, weak_link))
        if (isinstance(dest_node, ProcessNode) and
            isinstance(source_node, ProcessNode)):

            source_trait = source_node.process.trait(source_parameter)
            dest_trait = dest_node.process.trait(dest_parameter)
            if source_trait.output and not dest_trait.output:
                dest_trait.connected_output = True
        source_node.connect(source_parameter, dest_node, dest_parameter)
        dest_node.connect(dest_parameter, source_node, source_parameter)

    def export_parameter(self, node_name, parameter_name,
                         pipeline_parameter=None, weak_link=False,
                         is_enabled=True):
        '''Exports one of the nodes parameters at the level of the pipeline.
        '''
        node = self.nodes[node_name]
        trait = node.get_trait(parameter_name)
        if trait is None:
            raise ValueError('Node %(n)s (%(nn)s) has no parameter %(p)s' %
                             dict(n=node_name, nn=node.name, p=parameter_name))
        if not pipeline_parameter:
            pipeline_parameter = parameter_name
        if pipeline_parameter in self.user_traits():
            raise ValueError('Parameter %(pn)s of node %(nn)s cannot be '
                             'exported to pipeline parameter %(pp)s' %
                             dict(nn=node_name, pn=parameter_name,
                                  pp=pipeline_parameter))
        trait.enabled = is_enabled
        self.add_trait(pipeline_parameter, trait)

        if trait.output:
            self.add_link('%s.%s->%s' % (node_name, parameter_name,
                                         pipeline_parameter), weak_link)
        else:
            self.add_link('%s->%s.%s' % (pipeline_parameter,
                                         node_name, parameter_name), weak_link)

    def _set_node_enabled(self, node_name, value):
        node = self.nodes.get(node_name)
        if node:
            node.enabled = value

    def update_nodes_and_plugs_activation(self):

        # Activate the pipeline node and all its plugs (if they are enabled)
        # Activate the Switch Node and its connection with the Pipeline Node
        # Desactivate all other nodes (and their plugs).
        pipeline_node = None
        for node in self.nodes.itervalues():
            if isinstance(node, (PipelineNode)):
                pipeline_node = node
                node.activated = node.enabled
                for plug in node.plugs.itervalues():
                    plug.activated = node.activated and plug.enabled
            elif isinstance(node, (Switch)):
                node.activated = False
                for plug in node.plugs.itervalues():
                    for nn, pn, n, p, weak_link in plug.links_from:
                        if (isinstance(n, (PipelineNode)) and plug.enabled):
                            plug.activated = True
            else:
                node.activated = False
                for plug in node.plugs.itervalues():
                    plug.activated = False

        def backward_activation(node):
            """ Activate node and its plugs according output links
            Plugs and Nodes are activated if enabled.
            Nodes and plugs are supposed to be deactivated when this
            function is called.
            """
            # Browse all node plugs
            for plug_name, plug in node.plugs.iteritems():
                # Case input plug
                if not plug.output:
                    # If the node is a Switch, follow the selcted way
                    if isinstance(node, Switch):
                        if plug.activated:
                            for nn, pn, n, p, weak_link in plug.links_from:
                                p.activated = p.enabled
                                n.activated = n.enabled
                                backward_activation(n)
                    # Otherwise browse all node plugs
                    else:
                        # First activate the input plug if connected
                        plug.activated = plug.enabled
                        # Get the linked plugs
                        for nn, pn, n, p, weak_link in plug.links_from:
                            # Stop criterion: Pipeline input plug reached
                            if isinstance(n, (PipelineNode)):
                                continue
                            # Go through the pipeline nodes
                            else:
                                p.activated = p.enabled
                                # Stop going through the pipeline if the node
                                # has already been activated
                                if not n.activated:
                                    n.activated = n.enabled
                                    backward_activation(n)
                # Case output plug
                else:
                    # Activate weak links
                    for nn, pn, n, p, weak_link in plug.links_to:
                        if weak_link:
                            p.activated = p.enabled

        # Follow each link that is not weak from the output plugs
        for plug_name, plug in pipeline_node.plugs.iteritems():
            # Check if the pipeline plug is an output
            if plug.output:
                # Get the linked plugs
                for nn, pn, n, p, weak_link in plug.links_from:
                    if not weak_link:
                        p.activated = p.enabled
                        n.activated = n.enabled
                        backward_activation(n)
                    else:
                        plug.activated = False

        self.selection_changed = True

    def workflow_graph(self):
        """ Generate a workflow graph: list of process node to execute

        Returns
        -------
        graph: topological_sort.Graph
            grpah representation of the workflow from the current state of
            the pipeline
        """

        def insert(node_name, plug, dependencies, direct=True):
            """ Browse the plug links and add the correspondings edges
            to the node.
            If direct is set to true, the search looks for successor nodes.
            Otherwise, the search looks for predecessor nodes
            """
            # Get links
            if direct:
                plug_to_treat = plug.links_to
            else:
                plug_to_treat = plug.links_from

            # Main loop
            for item in plug_to_treat:
                # Plug need to be activated and must not be in the pipeline
                if (item[2].activated and not isinstance(item[2],
                                                         PipelineNode)):
                    # If plug links to a switch, we need to address the switch
                    # plugs
                    if not isinstance(item[2], Switch):
                        if direct:
                            dependencies.add((node_name, item[0]))
                        else:
                            dependencies.add((item[0], node_name))
                    else:
                        for switch_plug in item[2].plugs.itervalues():
                            insert(node_name, switch_plug, dependencies,
                                   direct)

        # Create a graph and a list of graph node edges
        graph = Graph()
        dependencies = set()

        # Add activated Process nodes in the graph
        for node_name, node in self.nodes.iteritems():
            # Select only Process nodes
            if (node.activated and not isinstance(node, PipelineNode) and
                    not isinstance(node, Switch)):
                # If Pipeline: meta in node is the workflow (list of
                # Process)
                if isinstance(node.process, Pipeline):
                    graph.add_node(GraphNode(node_name,
                                             node.process.workflow_graph()))
                # If Process: meta in node is a list with one Process
                else:
                    graph.add_node(GraphNode(node_name, [node.process, ]))

                # Add node edges (Successor: direct=True and
                # Predecessor: direct=False)
                for plug_name, plug in node.plugs.iteritems():
                    if plug.activated:
                        insert(node_name, plug, dependencies, direct=False)
                        insert(node_name, plug, dependencies, direct=True)

        # Add edges to the graph
        for d in dependencies:
            graph.add_link(d[0], d[1])

        return graph

    def workflow_ordered_nodes(self):
        """ Generate a workflow: list of process node to execute

        Returns
        -------
        workflow_list: list of Process
            an ordered list of Processes to execute
        """
        # Create a graph and a list of graph node edges
        graph = self.workflow_graph()
        # Start the topologival sort
        ordered_list = graph.topological_sort()

        def walk_wokflow(wokflow, workflow_list):
            """ Recursive fonction to go through pipelines' graphs
            """
            for sub_workflow in wokflow:
                if isinstance(sub_workflow[1], list):
                    workflow_list.extend(sub_workflow[1])
                else:
                    tmp = sub_workflow[1].topological_sort()
                    walk_wokflow(tmp, workflow_list)

        # Generate the output
        self.workflow_repr = "->".join([x[0] for x in ordered_list])
        logging.debug("Workflow: {0}". format(self.workflow_repr))
        self.workflow_list = []
        walk_wokflow(ordered_list, self.workflow_list)

        return self.workflow_list

    def _run_process(self):
        """ Execution of the pipeline, in a sequential, single-processor mode
        """
        nodes_list = self.workflow_ordered_nodes()
        returned = []
        for node in nodes_list:
            node_ret = node() # execute node
            returned.append( node_ret )
        return returned
