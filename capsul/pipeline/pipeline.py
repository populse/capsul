#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging

# Trait import
try:
    import traits.api as traits
    from traits.api import (File, Float, Enum, Str, Int, Bool, List, Tuple,
        Instance, Any, Event, CTrait, Directory, Trait)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import File, Float, Enum, Str, Int, Bool,\
        List, Tuple, Instance, Any, Event, CTrait, Directory

# Capsul import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary
from capsul.process import Process
from capsul.process import get_process_instance
from topological_sort import GraphNode, Graph
from pipeline_nodes import Plug, ProcessNode, PipelineNode,\
                           Switch


class Pipeline(Process):
    """ Pipeline containing Process nodes, and links between node
    parameters.

    Attributes
    ----------
    nodes : dict {node_name: node}
        a dictionary containing the pipline nodes and where the pipeline node name is ''
    workflow_list : list
        a list of odered nodes that can be executed
    workflow_repr : str
        a string representation of the workflow list `<node_i>-><node_i+1>`

    Methods
    -------
    add_trait
    add_process
    add_switch
    add_link
    remove_link
    export_parameter
    workflow_ordered_nodes
    workflow_graph
    update_nodes_and_plugs_activation
    parse_link
    parse_parameter
    find_empty_parameters
    count_items
    _set_node_enabled
    _run_process
    """

    #
    selection_changed = Event()

    def __init__(self, autoexport_nodes_parameters=True, **kwargs):
        """ Initialize the Pipeline class

        Parameters
        ----------
        autoexport_nodes_parameters: bool
            if True (default) nodes containing pipeline plugs are automatically
            exported.
        """
        # Inheritance
        super(Pipeline, self).__init__(**kwargs)
        super(Pipeline, self).add_trait('nodes_activation',
                                        Instance(Controller))

        # Class attributes
        self.list_process_in_pipeline = []
        self.attributes = {}
        self.nodes_activation = Controller()
        self.nodes = SortedDictionary()
        self.node_position = {}
        self.pipeline_node = PipelineNode(self, '', self)
        self.nodes[''] = self.pipeline_node
        self.do_not_export = set()
        self.parent_pipeline = None
        self._disable_update_nodes_and_plugs_activation = False
        self.pipeline_definition()

        self.workflow_repr = ""
        self.workflow_list = []
        
        # Automatically export node containing pipeline plugs
        # If plug is not optional and if the plug has to be exported
        if autoexport_nodes_parameters:
            for node_name, node in self.nodes.iteritems():
                if node_name == '':
                        continue
                for parameter_name, plug in node.plugs.iteritems():
                    if parameter_name in \
                            ('nodes_activation', 'selection_changed'):
                        continue
                    if ((node_name, parameter_name) not in self.do_not_export \
                            and ((plug.output and not plug.links_to) or\
                                 (not plug.output and not plug.links_from)) \
                            and not self.nodes[node_name].get_trait(
                            parameter_name).optional):
                        self.export_parameter(node_name, parameter_name)

        # Refresh pipeline activation
        self.update_nodes_and_plugs_activation()
        
    ##############
    # Methods    #
    ##############

    def add_trait(self, name, trait):
        """ Add a trait to the pipeline

        Parameters
        ----------
        name: str (mandatory)
            the trait name
        trait: trait instance (mandatory)
            the trait we want to add
        """
        # Add the trait
        super(Pipeline, self).add_trait(name, trait)
        self.get(name)

        # If we insert a user trait, create the associated plug
        if self.is_user_trait(trait):
            output = bool(trait.output)
            optional = bool(trait.optional)
            plug = Plug(output=output,optional=optional)
            self.pipeline_node.plugs[name] = plug
            plug.on_trait_change(self.update_nodes_and_plugs_activation,
                                 'enabled')

    def add_process(self, name, process, do_not_export=None,
                    make_optional=None, **kwargs):
        """ Add a new node in the pipeline

        Parameters
        ----------
        name: str (mandatory)
            the node name (has to be unique)
        process: Process (mandatory)
            the process we want to add
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export
        make_optional: list of str (optional)
            a list of plug names that we do not want to export

        """
        # Unique constrains
        make_optional = set(make_optional or [])
        do_not_export = set(do_not_export or [])
        do_not_export.update(kwargs)

        # Check the unicity of the name we want to insert
        if name in self.nodes:
            raise ValueError("Pipeline cannot have two nodes with the"
                             "same name : {0}".format(name))

        # Create a process node
        process = get_process_instance(process, **kwargs)
        if isinstance(process, Pipeline):
            node = process.pipeline_node
            node.name = name
            process.parent_pipeline = self
        else:
            node = ProcessNode(self, name, process)
        self.nodes[name] = node

        # Change plug default properties
        for parameter_name in self.nodes[name].plugs:
            # Do not export plug
            if (parameter_name in do_not_export or
                    parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))

            # Optional plug
            if parameter_name in make_optional:
                self.nodes[name].plugs[parameter_name].optional = True

        # Create a trait to control the node activation (enable property)
        self.nodes_activation.add_trait(name, Bool)
        setattr(self.nodes_activation, name, node.enabled)

        # Observer
        self.nodes_activation.on_trait_change(self._set_node_enabled, name)

        # Add new node in pipeline process list
        self.list_process_in_pipeline.append(process)

    def add_switch(self, name, inputs, outputs):
        """ Add a switch node in the pipeline

        Parameters
        ----------
        name: str (mandatory)
            name for the switch node (has to be unique)
        inputs: list of str (mandatory)
            names for switch inputs.
            Switch activation will select amongst them.
            Inputs names will actually be a combination of input and output,
            in the shape "input_switch_output".
            This behaviour is needed when there are several outputs, and thus
            several input groups.
        outputs: list of str (mandatory)
            names for outputs.

        Examples
        --------
        >>> pipeline.add_switch('group_switch', ['in1', 'in2'],
            ['out1', 'out2'])

        will create a switch with 4 inputs and 2 outputs:
        inputs: "in1_switch_out1", "in2_switch_out1", "in1_switch_out2",
        "in2_switch_out2"
        outputs: "out1", "out2"
        """
        # Check the unicity of the name we want to insert
        if name in self.nodes:
            raise ValueError("Pipeline cannot have two nodes with the same "
                             "name: {0}".format(name))

        # Create the node
        node = Switch(self, name, inputs, outputs)
        self.nodes[name] = node

        # Export the switch controller to the pipeline node
        self.export_parameter(name, "switch", name)

    def parse_link(self, link):
        """ Parse a link comming from export_parameter method.

        Parameters
        ----------
        link: str
            the link description of the form
            'node_from.plug_name->node_to.plug_name'

        Returns
        -------
        output: tuple
            tuple containing the link description and instances

        Examples
        --------
        >>> Pipeline.parse_link("node1.plug1->node2.plug2")
        "node1", "plug1", <instance node1>, <instance plug1>,
        "node2", "plug2", <instance node2>, <instance plug2>

        For a pipeline node:

        >>> Pipeline.parse_link("plug1->node2.plug2")
        "", "plug1", <instance pipeline>, <instance plug1>,
        "node2", "plug2", <instance node2>, <instance plug2>
        """
        # Split source and destination node descriptions
        source, dest = link.split("->")

        # Parse the source and destination parameters
        source_node_name, source_plug_name, source_node, source_plug = \
            self.parse_parameter(source)
        dest_node_name, dest_plug_name, dest_node, dest_plug = \
            self.parse_parameter(dest)

        return (source_node_name, source_plug_name, source_node, source_plug,
                dest_node_name, dest_plug_name, dest_node, dest_plug)

    def parse_parameter(self, name):
        """ Parse parameter of a node from its description.

        Parameters
        ----------
        name: str
            the description plug we want to load
            'node.plug'

        Returns
        -------
        output: tuple
            tuple containing the plug description and instances
        """
        # Parse the plug description
        dot = name.find(".")

        # Check if its a pipeline node
        if dot < 0:
            node_name = ""
            node = self.pipeline_node
            plug_name = name
        else:
            node_name = name[:dot]
            node = self.nodes.get(node_name)
            if node is None:
                raise ValueError("{0} is not a valid node name".format(
                                 node_name))
            plug_name = name[dot + 1:]

        # Check if plug nexists
        if plug_name not in node.plugs:
            raise ValueError('%s is not a valid parameter name for node %s' %
                             (plug_name, (node_name if node_name else
                                               'pipeline')))
        return node_name, plug_name, node, node.plugs[plug_name]

    def add_link(self, link, weak_link=False):
        """ Add a link between pipeline nodes.

        Parameters
        ----------
        link: str
            link descriptionof the form:
            "node.output->other_node.input".
            If no node is specified, the pipeline node itself is used:
            "output->other_node.input".
        weak_link: bool
             this property is used when nodes are optional,
             the plug information may not be generated.
        """
        # Parse the link
        (source_node_name, source_plug_name, source_node,
         source_plug, dest_node_name, dest_plug_name, dest_node,
        dest_plug) = self.parse_link(link)

        # Assure that pipeline plugs are not linked
        if not source_plug.output and source_node is not self.pipeline_node:
            raise ValueError("Cannot link from a pipeline input "
                             "plug: {0}".format(link))
        if dest_plug.output and dest_node is not self.pipeline_node:
            raise ValueError("Cannot link to a pipeline output "
                             "plug: {0}".format(link))
                
        # Propagate the plug value from source to destination
        value = source_node.get_plug_value(source_plug_name)
        if value is not None:
            dest_node.set_plug_value(dest_plug_name, value)

        # Update plugs memory of the pipeline
        source_plug.links_to.add((dest_node_name, dest_plug_name, dest_node,
                                  dest_plug, weak_link))
        dest_plug.links_from.add((source_node_name, source_plug_name,
                                  source_node, source_plug, weak_link))

        # Set a connected_output property
        if (isinstance(dest_node, ProcessNode) and
                isinstance(source_node, ProcessNode)):
            source_trait = source_node.process.trait(source_plug_name)
            dest_trait = dest_node.process.trait(dest_plug_name)
            if source_trait.output and not dest_trait.output:
                dest_trait.connected_output = True

        # Observer
        source_node.connect(source_plug_name, dest_node, dest_plug_name)
        dest_node.connect(dest_plug_name, source_node, source_plug_name)

        # Refresh pipeline activation
        self.update_nodes_and_plugs_activation()

    def remove_link(self, link):
        '''Remove a link between pipeline nodes

        Parameters
        ----------
        link: str
          link description. Its shape should be:
          "node.output->other_node.input".
          If no node is specified, the pipeline itself is assumed.
        '''
        # Parse the link
        (source_node_name, source_plug_name, source_node,
         source_plug, dest_node_name, dest_plug_name, dest_node,
        dest_plug) = self.parse_link(link)

        # Update plugs memory of the pipeline
        source_plug.links_to.discard((dest_node_name, dest_plug_name,
                                      dest_node, dest_plug, True))
        source_plug.links_to.discard((dest_node_name, dest_plug_name,
                                      dest_node, dest_plug, False))
        dest_plug.links_from.discard((source_node_name, source_plug_name,
                                      source_node, source_plug, True))
        dest_plug.links_from.discard((source_node_name, source_plug_name,
                                      source_node, source_plug, False))

        # Set a connected_output property
        if (isinstance(dest_node, ProcessNode) and
                isinstance(source_node, ProcessNode)):
            source_trait = source_node.process.trait(source_plug_name)
            dest_trait = dest_node.process.trait(dest_plug_name)
            if dest_trait.connected_output:
                dest_trait.connected_output = False  # FIXME

        # Observer
        source_node.disconnect(source_plug_name, dest_node, dest_plug_name)
        dest_node.disconnect(dest_plug_name, source_node, source_plug_name)

    def export_parameter(self, node_name, plug_name,
                         pipeline_parameter=None, weak_link=False,
                         is_enabled=None, is_optional=None):
        """ Export a node plug at the pipeline level.

        Parameters
        ----------
        node_name: str (mandatory)
            the name of node containing the plug we want to export
        plug_name: str (mandatory)
            the node plug name we want to export
        pipeline_parameter: str (optional)
            the name to access this parameter at the pipeline level.
            Default None, the plug name is used
        weak_link: bool (optional)
            this property is used when nodes are weak,
            **FIXME:** what does it exactly mean ?
            the plug information may not be generated.
        is_enabled: bool (optional)
            a property to specify that it is not a user-parameter
            automatic generation)
        is_optional: bool (optional)
            sets the exported parameter to be optional
        """
        # Get the node and parameter
        node = self.nodes[node_name]
        # Make a copy of the trait
        trait = Trait(node.get_trait(plug_name))

        # Check if the plug name is valid
        if trait is None:
            raise ValueError("Node {0} ({1}) has no parameter "
                             "{2}".format(node_name, node.name, plug_name))

        # If a tuned name is not specified, used the plug name
        if not pipeline_parameter:
            pipeline_parameter = plug_name

        # Check the the pipeline parameter name is not already used
        if pipeline_parameter in self.user_traits():
            raise ValueError("Parameter {0} of node {1} cannot be "
                             "exported to pipeline parameter "
                             "{2}".format(plug_name, node_name or 'pipeline_node',
                             pipeline_parameter))

        # Set user enabled parameter only if specified
        # Important because this property is automatically set during
        # the nipype interface wrappings
        if is_enabled is not None:
            trait.enabled = bool(is_enabled)

        # Change the trait optional property
        if is_optional is not None:
            trait.optional = bool(is_optional)

        # Now add the parameter to the pipeline
        self.add_trait(pipeline_parameter, trait)
        # Propagate the parameter value to the new exported one
        setattr(self, pipeline_parameter, node.get_plug_value(plug_name))

        # Do not forget to link the node with the pipeline node
        if trait.output:
            self.add_link("{0}.{1}->{2}".format(node_name, plug_name,
                                         pipeline_parameter), weak_link)
        else:
            self.add_link("{0}->{1}.{2}".format(pipeline_parameter,
                                         node_name, plug_name), weak_link)
        
    def _set_node_enabled(self, node_name, is_enabled):
        """ Method to enable or disabled a node

        Parameters
        ----------
        node_name: str (mandatory)
            the node name
        is_enabled: bool (mandatory)
            the desired property
        """
        node = self.nodes.get(node_name)
        if node:
            node.enabled = is_enabled
                                     
    def all_nodes(self):
        '''Iterate over all pipeline nodes including sub-pipeline nodes.        
        Returns
        -------
        nodes: Generator of Node
            Iterates over all nodes
        '''
        for node in self.nodes.itervalues():
            yield node
            if isinstance(node,PipelineNode) and node is not self.pipeline_node:
                for sub_node in node.process.all_nodes():
                    if sub_node is not node:
                        yield sub_node
        
    def _check_local_node_activation(self, node):
        '''Try to activate a node and its plugs according to its 
        state and the state of its direct neighbouring nodes.

        Parameters
        ----------
        node: Node (mandatory)
            node to check
        
        Returns
        -------
        can_be_activated: Bool
            True if at least a plug has been activated.
        '''
        # If a node is disabled, it will never be activated
        activations_modified = False
        if node.enabled:
            # Try to activate input plugs
            node_activated = True
            if node is self.pipeline_node:
                for plug_name, plug in node.plugs.iteritems():
                    if plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            activations_modified = True
            else:
                for plug_name, plug in node.plugs.iteritems():
                    if plug.output:
                        # ignore output plugs
                        continue
                    if plug.enabled:
                        # Look for a non weak link connected to an activated
                        # plug in order to activate the plug
                        for nn, pn, n, p, weak_link in plug.links_from:
                            if not weak_link and p.activated:
                                if not plug.activated:
                                    plug.activated = True
                                    activations_modified = True
                                break
                    # If the plug is not activated, is mandatory and must be
                    # exported, the whole node is deactivated
                    if not plug.activated and not (plug.optional or
                        (node.name, node) in node.pipeline.do_not_export):
                        node_activated = False
                        break
            if node_activated:
                if not node.activated:
                    node.activated = True
                    activations_modified = True
                # If node is activated, activate enabled output plugs
                for plug_name, plug in node.plugs.iteritems():
                    if plug.output and plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            activations_modified = True
        #print '!forward_activation!', node.name, node, activations_modified
        return activations_modified
        
    def _check_local_node_deactivation(self, node, force_plug_output):
        # Desactivate node (and its plugs) according only to links to its
        # output plugs. Node is supposed to be activated when this
        # function is called.
        activations_modified = False
        if node.activated:
            #print '!bacward_deactivations!', ('<?>' if force_plug_output is None else ('->' if force_plug_output else '<-')), node.name, getattr(node,'process',None) or node
            for plug_name, plug in node.plugs.iteritems():
                if plug.activated:
                    if force_plug_output is None:
                        output = plug.output
                        if node is self.pipeline_node:
                            output = not output
                    else:
                        output = force_plug_output
                    if output:
                        links = plug.links_to
                    else:
                        links = plug.links_from
                    plug_activated = None
                    weak_activation = False
                    for nn, pn, n, p, weak_link in links:
                        if weak_link:
                            weak_activation = (weak_activation or p.activated)
                        else:
                            if p.activated:
                                plug_activated = True
                                break
                            else:
                                plug_activated = False
                    if plug_activated is None:
                        # plug is connected only with weak links
                        plug_activated = weak_activation
                    if not plug_activated:
                        plug.activated = False
                        activations_modified = True
                        #print '!bacward_deactivations! ---', plug_name
                        if not (plug.optional or
                                (node.name, node) in node.pipeline.do_not_export):
                            node.activated = False
                            #print '!bacward_deactivations! ---', node.name, node
                            break
            if not node.activated:
                for plug_name, plug in node.plugs.iteritems():
                    #if plug.activated:
                        #print '!bacward_deactivations! -=-', plug_name
                    plug.activated = False
        #print '!bacward_deactivations!', node.name, node, activations_modified
        return activations_modified

    def update_nodes_and_plugs_activation(self):
        """Reset all nodes and plugs activations according to the current state
        of the pipeline (i.e. switch selection, nodes disabled, etc.).
        Activations are set according to the following rules.
        1) A node is not activated if it is not enabled.
        2) A plug is not activated if it is not enabled
        3)
        """
        if self._disable_update_nodes_and_plugs_activation:
            return
        if not hasattr(self, 'parent_pipeline'):
            # self is being initialized (the call comes from self.__init__).
            return
         
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.update_nodes_and_plugs_activation()
            return
        
        #print '!update_nodes_and_plugs_activation!', self.id
        # Remember all links that are inactive (i.e. at least one of the two
        # plugs is inactive) in order to execute a callback if they become
        # active (see at the end of this method)
        inactive_links = []
        for node in self.all_nodes():
            for source_plug_name, source_plug in node.plugs.iteritems():
                for nn, pn, n, p, weak_link in source_plug.links_to:
                    if not source_plug.activated or not p.activated:
                        inactive_links.append((node, source_plug_name,
                                               source_plug, n, pn, p))

        # Initialization : deactivate all nodes and their plugs
        for node in self.all_nodes():
            node.activated = False
            for plug in node.plugs.itervalues():
                plug.activated = False

        # Forward activation : try to activate nodes (and their input plugs) and
        # propagate all activations to output plugs and to nodes connected to
        # output plugs.
        nodes_to_check = set(self.all_nodes())
        while nodes_to_check:
            #print '!---forward activations---!', len(nodes_to_check)
            new_nodes_to_check = set()
            for node in nodes_to_check:
                if self._check_local_node_activation(node):
                    for plug in node.plugs.itervalues():
                        if plug.activated:
                            for nn, pn, n, p, weak_link in plug.links_to.union(plug.links_from):
                                if not weak_link and p.enabled:
                                    new_nodes_to_check.add(n)
            nodes_to_check = new_nodes_to_check        

        # Backward deactivation
        nodes_to_check = set(self.all_nodes())
        while nodes_to_check:
            new_nodes_to_check = set()
            #print '!---backward deactivations---!', len(nodes_to_check)
            for node in nodes_to_check:
                if isinstance(node, PipelineNode) and node is not self.pipeline_node:
                    test = self._check_local_node_deactivation(node,True) or\
                           self._check_local_node_deactivation(node,False)
                else:
                    test = self._check_local_node_deactivation(node,None)
                if test:
                    for plug in node.plugs.itervalues():
                        if not plug.activated:
                            for nn, pn, n, p, weak_link in plug.links_from.union(plug.links_to):
                                if p.activated:
                                    new_nodes_to_check.add(n)
            nodes_to_check = new_nodes_to_check        

        # Update processes to hide or show their traits according to the
        # corresponding plug activation
        for node in self.all_nodes():
            if isinstance(node,ProcessNode):
                traits_changed = False
                for plug_name, plug in node.plugs.iteritems():
                    trait = node.process.trait(plug_name)
                    if plug.activated:
                        if getattr(trait, 'hidden', False):
                            trait.hidden = False
                            traits_changed = True
                    else:
                        if not getattr(trait, 'hidden', False):
                            trait.hidden = True
                            traits_changed = True
                if traits_changed:
                    node.process.user_traits_changed = True

        # Execute a callback for all links that have become active.
        for node, source_plug_name, source_plug, n, pn, p in inactive_links:
            if (source_plug.activated and p.activated):
                value = node.get_plug_value(source_plug_name)
                node._callbacks[(source_plug_name, n, pn)](value)

        # Refresh views relying on plugs and nodes selection
        for node in self.all_nodes():
            if isinstance(node, PipelineNode):
                node.pipeline.selection_changed = True

    def workflow_graph(self):
        """ Generate a workflow graph

        Returns
        -------
        graph: topological_sort.Graph
            graph representation of the workflow from the current state of
            the pipeline
        """

        def insert(pipeline, node_name, plug, dependencies):
            """ Browse the plug links and add the correspondings edges
            to the node.
            If direct is set to true, the search looks for successor nodes.
            Otherwise, the search looks for predecessor nodes
            """

            # Main loop
            for dest_node_name, dest_plug_name, dest_node, dest_plug, \
                  weak_link in plug.links_to:
                # Ignore the link if it is pointing to a node in a
                # sub-pipeline or in the parent pipeline
                if pipeline.nodes.get(dest_node_name) is not dest_node:
                    continue
                
                # Plug need to be activated
                if dest_node.activated:
                    # If plug links to a switch, we need to address the switch
                    # plugs
                    if not isinstance(dest_node, Switch):
                        dependencies.add((node_name, dest_node_name))
                    else:
                        for switch_plug in dest_node.plugs.itervalues():
                            insert(pipeline, node_name, switch_plug,
                                   dependencies)

        # Create a graph and a list of graph node edges
        graph = Graph()
        dependencies = set()

        # Add activated Process nodes in the graph
        for node_name, node in self.nodes.iteritems():
            if not node_name:
                continue
            # Select only Process nodes
            if node.activated and not isinstance(node, Switch):
                # If Pipeline: meta in node is the workflow (list of
                # Process)
                if isinstance(node.process, Pipeline):
                    graph.add_node(GraphNode(node_name,
                                             node.process.workflow_graph()))
                # If Process: meta in node is a list with one Process
                else:
                    graph.add_node(GraphNode(node_name, [node.process]))

                # Add node edges (Successor: direct=True and
                # Predecessor: direct=False)
                for plug_name, plug in node.plugs.iteritems():
                    if plug.activated:
                        insert(self, node_name, plug, dependencies)

        # Add edges to the graph
        for d in dependencies:
            if graph.find_node(d[0]) and graph.find_node(d[1]):
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
        workflow_list = []
        walk_wokflow(ordered_list, workflow_list)

        return workflow_list

    def _run_process(self):
        """ Execution of the pipeline, in a sequential,
        single-processor mode.

        Returns
        -------
        returned: list
            the execution return results of each node in the worflow
        """
        nodes_list = self.workflow_ordered_nodes()
        returned = []
        for node in nodes_list:
            node_ret = node()  # execute node
            returned.append(node_ret)
        return returned

    def find_empty_parameters(self):
        """ Find internal File/Directory parameters not exported to the main
        input/output parameters of the pipeline with empty values. This is
        meant to track parameters which should be associated with temporary
        files internally.

        Returns
        -------
        list
            Each element is a list with 3 values: node, parameter_name,
            optional
        """
        empty_params = []
        # walk all activated nodes, recursively
        nodes = [(node_name, node) \
            for node_name, node in self.nodes.iteritems() \
            if node_name != '' and node.enabled and node.activated]
        while nodes:
            node_name, node = nodes.pop(0)
            if hasattr(node, 'process'):
                process = node.process
                if isinstance(process, Pipeline):
                    nodes += [(cnode_name, cnode) \
                        for cnode_name, cnode in process.nodes.iteritems() \
                        if cnode_name != '' and cnode.enabled \
                        and cnode.activated]
            else:
                process = node
            # check output plugs; input ones don't work with generated
            # temporary files (unless they are connected with an output one,
            # which will do the job)
            for plug_name, plug in node.plugs.iteritems():
                if not plug.enabled or not plug.output or \
                        (not plug.activated and plug.optional):
                    continue
                parameter = process.user_traits()[plug_name]
                if not isinstance(parameter.trait_type, File) \
                        and not isinstance(parameter.trait_type, Directory):
                    continue
                value = getattr(process, plug_name)
                if value != '' and value is not traits.Undefined:
                    continue # non-null value: not an empty parameter.
                optional = bool(parameter.optional)
                valid = True
                links = list(plug.links_from.union(plug.links_to))
                if len(links) == 0:
                    if optional:
                        # an optional, non-connected output can stay empty
                        continue
                # check where this plug is linked
                while links:
                    link = links.pop(0)
                    oplug = link[3]
                    if link[0] == '':
                        if link[2] == self.nodes['']:
                            # linked to the main node: keep it as is
                            valid = False
                            break
                        # linked to an output plug of an intermediate pipeline:
                        # needed only if this pipeline plug is used later,
                        # or mandatory
                        if oplug.optional:
                            links += oplug.links_to
                    optional &= bool(oplug.optional)
                if valid:
                    empty_params.append((node, plug_name, optional))
        return empty_params

    def count_items(self):
        """ Count pipeline items to get its size.

        Returns
        -------
        items: tuple
            (nodes_count, processes_count, plugs_count, params_count,
            links_count, enabled_nodes_count, enabled_procs_count,
            enabled_links_count)
        """
        nodes = self.nodes.values()
        plugs_count = 0
        params_count = len([param \
            for param_name, param in self.user_traits().iteritems() \
            if param_name not in ('nodes_activation', 'selection_changed')])
        nodes_count = 0
        links_count = 0
        procs = set()
        nodeset = set()
        enabled_nodes_count = 0
        enabled_procs_count = 0
        enabled_links_count = 0
        while nodes:
            node = nodes.pop(0)
            nodeset.add(node)
            nodes_count += 1
            if node.enabled and node.activated:
                enabled_nodes_count += 1
            plugs_count += len(node.plugs)
            links_count += sum([len(plug.links_to) + len(plug.links_from) \
                for plug in node.plugs.itervalues()])
            enabled_links_count += sum(
                [len([pend for pend in plug.links_to \
                        if pend[3].enabled and pend[3].activated]) \
                    + len([pend for pend in plug.links_from
                        if pend[3].enabled and pend[3].activated]) \
                    for plug in node.plugs.itervalues() \
                    if plug.enabled and plug.activated])
            if hasattr(node, 'nodes'):
                sub_nodes = [sub_node
                    for sub_node in node.nodes.values()
                    if sub_node not in nodeset and sub_node not in nodes]
                nodes += sub_nodes
            elif hasattr(node, 'process'):
                if node.process in procs:
                    continue
                procs.add(node.process)
                if node.enabled and node.activated:
                    enabled_procs_count += 1
                params_count += len([param \
                    for param_name, param \
                    in node.process.user_traits().iteritems() \
                    if param_name not in (
                        'nodes_activation', 'selection_changed')])
                if hasattr(node.process, 'nodes'):
                    sub_nodes = [sub_node
                        for sub_node in node.process.nodes.values()
                        if sub_node not in nodeset and sub_node not in nodes]
                    nodes += sub_nodes
            elif hasattr(node, 'user_traits'):
                params_count += len([param \
                    for param_name, param in node.user_traits().iteritems() \
                    if param_name not in (
                        'nodes_activation', 'selection_changed', 'activated',
                        'enabled', 'name')])
        return nodes_count, len(procs), plugs_count, params_count, \
            links_count, enabled_nodes_count, enabled_procs_count, \
            enabled_links_count

