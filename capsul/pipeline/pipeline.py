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
from copy import deepcopy
import types

# Trait import
try:
    import traits.api as traits
    from traits.trait_base import _Undefined
    from traits.api import (File, Float, Enum, Str, Int, Bool, List, Tuple,
        Instance, Any, Event, CTrait, Directory, Trait)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.trait_base import _Undefined
    from enthought.traits.api import (File, Float, Enum, Str, Int, Bool,
        List, Tuple, Instance, Any, Event, CTrait, Directory)

# Capsul import
from capsul.process import Process
from capsul.process import get_process_instance
from topological_sort import GraphNode, Graph
from pipeline_nodes import (
    Plug, ProcessNode, PipelineNode, Switch, IterativeNode)

# Soma import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary


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
        self._disable_update_nodes_and_plugs_activation = 1
        self._must_update_nodes_and_plugs_activation = False
        self.pipeline_definition()

        self.workflow_repr = ""
        self.workflow_list = []
        
        if autoexport_nodes_parameters:
            self.autoexport_nodes_parameters()
            
        # Refresh pipeline activation
        self._disable_update_nodes_and_plugs_activation -= 1
        self.update_nodes_and_plugs_activation()
        
    ##############
    # Methods    #
    ##############

    def autoexport_nodes_parameters(self):
        """Automatically export node containing pipeline plugs
        If plug is not optional and if the plug has to be exported
        """
        for node_name, node in self.nodes.iteritems():
            if node_name == "":
                    continue
            for parameter_name, plug in node.plugs.iteritems():
                if parameter_name in ("nodes_activation", "selection_changed"):
                    continue
                if (((node_name, parameter_name) not in self.do_not_export and
                    ((plug.output and not plug.links_to) or
                    (not plug.output and not plug.links_from)) and
                    not self.nodes[node_name].get_trait(parameter_name).optional)):

                    self.export_parameter(node_name, parameter_name)

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
            node.pipeline = self
            process.parent_pipeline = self
        else:
            node = ProcessNode(self, name, process)
        self.nodes[name] = node
        
        # If a default value is given to a parameter, change the corresponding
        # plug so that it gets activated even if not linked
        for parameter_name in kwargs:
            if process.trait(parameter_name):
                node.plugs[i].has_default_value = True
                make_optional.add(parameter_name)

        # Change plug default properties
        for parameter_name in node.plugs:
            # Do not export plug
            if (parameter_name in do_not_export or
                    parameter_name in make_optional):
                self.do_not_export.add((name, parameter_name))

            # Optional plug
            if parameter_name in make_optional:
                node.plugs[parameter_name].optional = True

        # Create a trait to control the node activation (enable property)
        self.nodes_activation.add_trait(name, Bool)
        setattr(self.nodes_activation, name, node.enabled)

        # Observer
        self.nodes_activation.on_trait_change(self._set_node_enabled, name)

        # Add new node in pipeline process list
        self.list_process_in_pipeline.append(process)

    def add_iterative_process(self, name, process, iterative_plugs=None,
                              do_not_export=None, make_optional=None, **kwargs):
        """ Add a new iterative node in the pipeline.

        Parameters
        ----------
        name: str (mandatory)
            the node name (has to be unique)
        process: Process (mandatory)
            the process we want to add
        iterative_plugs: list of str (optional)
            a list of plug names on which we want to iterate 
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export
        make_optional: list of str (optional)
            a list of plug names that we do not want to export
        """
        # If no iterative plug are given as parameter, add a process
        if iterative_plugs is None:
            self.add_process(name, process, do_not_export,
                             make_optional, **kwargs)

        # Otherwise, need to create a dynamic structure
        else:
            # Check the unicity of the name we want to insert
            if name in self.nodes:
                raise ValueError("Pipeline cannot have two nodes with the"
                                 "same name : {0}".format(name)) 
   
            # Create the iterative pipeline node
            process = get_process_instance(process, **kwargs)
            node = IterativeNode(
                self, name, process, iterative_plugs, do_not_export,
                make_optional, **kwargs)
            self.nodes[name] = node

            # Create a trait to control the node activation (enable property)
            self.nodes_activation.add_trait(name, Bool)
            setattr(self.nodes_activation, name, node.enabled)

            # Observer
            self.nodes_activation.on_trait_change(self._set_node_enabled, name)

            # Add new node in pipeline process list
            self.list_process_in_pipeline.append(node.process)

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

        If the destination node is a switch, force the source plug to be not 
        optional.

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

        # If the plug value is None, replace it by the undefined 
        # trait value
        plug_value = node.get_plug_value(plug_name)
        if plug_value is None:
            node.set_plug_value(plug_name, _Undefined())

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
        plugs_activated: list
            list of (plug_name,plug) containing all plugs that have been
            activated
        '''
        plugs_activated = []
        # If a node is disabled, it will never be activated
        if node.enabled:
            # Try to activate input plugs
            node_activated = True
            if node is self.pipeline_node:
                # For the top-level pipeline node, all enabled plugs
                # are activated
                for plug_name, plug in node.plugs.iteritems():
                    if plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            plugs_activated.append((plug_name, plug))
            else:
                # Look for input plugs that can be activated
                for plug_name, plug in node.plugs.iteritems():
                    if plug.output:
                        # ignore output plugs
                        continue
                    if plug.enabled and not plug.activated:
                        if plug.has_default_value:
                            plug.activated = True
                            plugs_activated.append((plug_name,plug))
                        else:
                            # Look for a non weak link connected to an activated
                            # plug in order to activate the plug
                            for nn, pn, n, p, weak_link in plug.links_from:
                                if not weak_link and p.activated:
                                    plug.activated = True
                                    plugs_activated.append((plug_name,plug))
                                    break
                    # If the plug is not activated and is not optional the
                    # whole node is deactivated
                    if not plug.activated and not plug.optional:
                        node_activated = False
            if node_activated:
                node.activated = True
                # If node is activated, activate enabled output plugs
                for plug_name, plug in node.plugs.iteritems():
                    if plug.output and plug.enabled:
                        if not plug.activated:
                            plug.activated = True
                            plugs_activated.append((plug_name,plug))
        return plugs_activated
        
    def _check_local_node_deactivation(self, node):
        '''Check plugs that have to be deactivated according to node
        activation state and to the state of its direct neighbouring nodes.

        Parameters
        ----------
        node: Node (mandatory)
            node to check
        
        Returns
        -------
        plugs_deactivated: list
            list of (plug_name,plug) containing all plugs that have been
            deactivated
        '''
        def check_plug_activation(plug,links):
            # After th next fo loop, plug_activated can have three
            # values:
            #  True  if there is a non weak link connected to an
            #        activated plug
            #  False if there are non weak links that ar all connected
            #        to inactive plugs
            #  None if there is no non weak links
            plug_activated = None
            # weak_activation will be True if there is at least one
            # weak link connected to an activated plug
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
                # plug is connected only with weak links therefore
                # they are used to define its activation state
                plug_activated = weak_activation
            return plug_activated
        
        plugs_deactivated = []
        # If node has already been  deactivated there is nothing to do
        if node.activated:
            deactivate_node = bool(node.plugs)
            for plug_name, plug in node.plugs.iteritems():
                # Check all activated plugs
                if plug.activated:
                    # A plug with a default value is always activated
                    if plug.has_default_value:
                        continue
                    output = plug.output
                    if isinstance(node, PipelineNode) and \
                          node is not self.pipeline_node and \
                          output:
                        plug_activated = check_plug_activation(plug,
                            plug.links_to) and \
                            check_plug_activation(plug, plug.links_from)
                    else:
                        if node is self.pipeline_node:
                            output = not output
                        if output:
                            plug_activated = check_plug_activation(plug,
                                plug.links_to)
                        else:
                            plug_activated = check_plug_activation(plug,
                                plug.links_from)
                    
                    # Plug must be deactivated, record it in result and check
                    # if this deactivation also deactivate the node
                    if not plug_activated:
                        plug.activated = False
                        plugs_deactivated.append((plug_name, plug))
                        if not (plug.optional or
                                node is self.pipeline_node):
                            node.activated = False
                            break
                if plug.output and plug.activated:
                    deactivate_node = False
            if deactivate_node:
                node.activated = False
                for plug_name, plug in node.plugs.iteritems():
                    if plug.activated:
                        plug.activated = False
                        plugs_deactivated.append((plug_name,plug))
        return plugs_deactivated

    def delay_update_nodes_and_plugs_activation(self):
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.delay_update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation == 0:
            self._must_update_nodes_and_plugs_activation = False
        self._disable_update_nodes_and_plugs_activation += 1

    def restore_update_nodes_and_plugs_activation(self):
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.restore_update_nodes_and_plugs_activation()
            return
        self._disable_update_nodes_and_plugs_activation -= 1
        if self._disable_update_nodes_and_plugs_activation == 0 and \
                self._must_update_nodes_and_plugs_activation:
            self.update_nodes_and_plugs_activation()

    def update_nodes_and_plugs_activation(self):
        '''Reset all nodes and plugs activations according to the current state
        of the pipeline (i.e. switch selection, nodes disabled, etc.).
        Activations are set according to the following rules.
        '''
        if not hasattr(self, 'parent_pipeline'):
            # self is being initialized (the call comes from self.__init__).
            return
        if self.parent_pipeline is not None:
            # Only the top level pipeline can manage activations
            self.parent_pipeline.update_nodes_and_plugs_activation()
            return
        if self._disable_update_nodes_and_plugs_activation:
            self._must_update_nodes_and_plugs_activation = True
            return
        
        self._disable_update_nodes_and_plugs_activation += 1
        
        #print '!'
        #print '!update_nodes_and_plugs_activation!', self.id, self, self._disable_update_nodes_and_plugs_activation
        debug = getattr(self, '_debug_activations', None)
        if debug:
            debug = open(debug,'w')
            print >> debug,self.id
                
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
            for plug_name, plug in node.plugs.iteritems():
                plug.activated = False

        # Forward activation : try to activate nodes (and their input plugs) and
        # propagate activations neighbours of activated plugs
        
        # Starts iterations with all nodes
        nodes_to_check = set(self.all_nodes())
        iteration = 1
        while nodes_to_check:
            new_nodes_to_check = set()
            for node in nodes_to_check:
                node_activated = node.activated
                for plug_name, plug in self._check_local_node_activation(node):
                    if debug:
                        print >> debug, '%d+%s:%s' % (iteration, node.full_name, plug_name)
                    #print '!activations! iteration', iteration, '+++ %s:%s' % (node.full_name,plug_name)
                    for nn, pn, n, p, weak_link in plug.links_to.union(plug.links_from):
                        if not weak_link and p.enabled:
                            new_nodes_to_check.add(n)
                if (not node_activated) and node.activated:
                    if debug:
                        print >> debug, '%d+%s' % (iteration, node.full_name)
            nodes_to_check = new_nodes_to_check
            iteration += 1

        # Backward deactivation : deactivate plugs that should not been
        # activated and propagate deactivation to neighbouring plugs
        nodes_to_check = set(self.all_nodes())
        iteration = 1
        while nodes_to_check:
            new_nodes_to_check = set()
            for node in nodes_to_check:
                node_activated = node.activated
                # Test plugs deactivation according to their input/output
                # state
                test = self._check_local_node_deactivation(node)
                if test:
                    for plug_name, plug in test:
                        if debug:
                            print >> debug, '%d-%s:%s' % (iteration, node.full_name, plug_name)
                        #print '!deactivations! iteration', iteration, '--- %s:%s' % (node.full_name,plug_name)
                        for nn, pn, n, p, weak_link in plug.links_from.union(plug.links_to):
                            if p.activated:
                                new_nodes_to_check.add(n)
                    if not node.activated:
                        # If the node has been deactivated, force deactivation
                        # of all plugs that are still active and propagate
                        # this deactivation to neighbours
                        if node_activated and debug:
                            print >> debug, '%d-%s' % (iteration, node.full_name)
                        for plug_name, plug in node.plugs.iteritems():
                            if plug.activated:
                                plug.activated = False
                                #print '!deactivations! iteration', iteration, '--> %s:%s' % (node.full_name,plug_name)
                                if debug:
                                    print >> debug, '%d=%s:%s' % (iteration, node.full_name, plug_name)
                                for nn, pn, n, p, weak_link in plug.links_from.union(plug.links_to):
                                    if p.activated:
                                        new_nodes_to_check.add(n)
            nodes_to_check = new_nodes_to_check
            iteration += 1

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
                node.process.selection_changed = True
        
        self._disable_update_nodes_and_plugs_activation -= 1
            
    def workflow_graph(self):
        """Generate a workflow graph

        Returns
        -------
        graph: topological_sort.Graph
            graph representation of the workflow from the current state of
            the pipeline
        """

        def insert(pipeline, node_name, plug, dependencies):
            """ Browse the plug links and add the correspondings edges
            to the node.
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

                # Add node edges
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

    def pipeline_state(self):
        '''Return an object composed of basic Python objects that contains
        the whole structure and state of the pipeline. This object can be 
        given to compare_to_state method in order to get the differences with 
        a previously stored state. This is typically used in tests scripts.

        Returns
        -------
        pipeline_state: dictionary
        '''
        result = {}
        for node in self.all_nodes():
            plugs_list = []
            node_dict = dict(name=node.name,
                             enabled=node.enabled,
                             activated=node.activated,
                             plugs=plugs_list)                  
            result[node.full_name] = node_dict
            for plug_name, plug in node.plugs.iteritems():
                links_to_dict = {}
                links_from_dict = {}
                plug_dict = dict(enabled=plug.enabled,
                                 activated=plug.activated,
                                 output=plug.output,
                                 optional=plug.optional,
                                 has_default_value=plug.has_default_value,
                                 links_to=links_to_dict,
                                 links_from=links_from_dict)
                plugs_list.append((plug_name,plug_dict))
                for nn, pn, n, p, weak_link in plug.links_to:
                    link_name = '%s:%s' % (n.full_name,pn)
                    links_to_dict[link_name] = weak_link
                for nn, pn, n, p, weak_link in plug.links_from:
                    link_name = '%s:%s' % (n.full_name,pn)
                    links_from_dict[link_name] = weak_link
        return result
    
    def compare_to_state(self, pipeline_state):
        '''Returns the differences between this pipeline and a previously recorded state.
        
        Returns
        -------
        differences: list
            each element is a human readable string explaining one difference
            (e.g. 'node "my_process" is missing')
        '''
        result = []
        def compare_dict(ref_dict, other_dict):
            for ref_key, ref_value in ref_dict.iteritems():
                if ref_key not in other_dict:
                    yield '%s = %s is missing' % (ref_key,repr(ref_value))
                else:
                    other_value = other_dict.pop(ref_key)
                    if ref_value != other_value:
                        yield '%s = %s differs from %s' % (ref_key, repr(ref_value), repr(other_value))
            for other_key, other_value in other_dict.iteritems():
                yield '%s=%s is new' % (other_key,repr(other_value))
        
        pipeline_state = deepcopy(pipeline_state)
        for node in self.all_nodes():
            node_name = node.full_name
            node_dict = pipeline_state.pop(node_name,None)
            if node_dict is None:
                result.append('node "%s" is missing' % node_name)
            else:
                plugs_list = node_dict.pop('plugs')
                result.extend('in node "%s": %s' % (node_name,i) for i in
                              compare_dict(dict(name=node.name,
                                                enabled=node.enabled,
                                                activated=node.activated),
                                           node_dict))
                ref_plug_names = list(node.plugs)
                other_plug_names = [i[0] for i in plugs_list]
                if ref_plug_names != other_plug_names:
                    if sorted(ref_plug_names) == sorted(other_plug_names):
                        result.append('in node "%s": plugs order = %s '
                                      'differs from %s' % \
                                      (node_name, repr(ref_plug_names), 
                                       repr(other_plug_names)))
                    else:
                        result.append('in node "%s": plugs list = %s '
                                      'differs from %s' % \
                                      (node_name, repr(ref_plug_names), 
                                       repr(other_plug_names)))
                        # go to next node
                        continue
                for plug_name, plug in node.plugs.iteritems():
                    plug_dict = plugs_list[0][1]
                    del plugs_list[0]
                    links_to_dict = plug_dict.pop('links_to')
                    links_from_dict = plug_dict.pop('links_from')
                    result.extend('in plug "%s:%s": %s' % (node_name,plug_name,i) for i in
                                  compare_dict(dict(enabled=plug.enabled,
                                                    activated=plug.activated,
                                                    output=plug.output,
                                                    optional=plug.optional,
                                                    has_default_value=plug.has_default_value),
                                               plug_dict))
                    for nn, pn, n, p, weak_link in plug.links_to:
                        link_name = '%s:%s' % (n.full_name,pn)
                        if link_name not in links_to_dict:
                            result.append('in plug "%s:%s": missing link to %s' % (node_name,plug_name,link_name))
                        else:
                            other_weak_link = links_to_dict.pop(link_name)
                            if weak_link != other_weak_link:
                                result.append('in plug "%s:%s": link to %s is%sweak' % (node_name,plug_name,link_name,(' not' if weak_link else '')))
                    for link_name, weak_link in links_to_dict.iteritems():
                        result.append('in plug "%s:%s": %slink to %s is new' % (node_name,plug_name,(' weak' if weak_link else ''),link_name))
                    for nn, pn, n, p, weak_link in plug.links_from:
                        link_name = '%s:%s' % (n.full_name,pn)
                        if link_name not in links_from_dict:
                            result.append('in plug "%s:%s": missing link from %s' % (node_name,plug_name,link_name))
                        else:
                            other_weak_link = links_from_dict.pop(link_name)
                            if weak_link != other_weak_link:
                                result.append('in plug "%s:%s": link from %s is%sweak' % (node_name,plug_name,link_name,(' not' if weak_link else '')))
                    for link_name, weak_link in links_from_dict.iteritems():
                        result.append('in plug "%s:%s": %slink from %s is new' % (node_name,plug_name,(' weak' if weak_link else ''),link_name))
                        
        for node_name in pipeline_state:
            result.append('node "%s" is new' % node_name)
        return result
