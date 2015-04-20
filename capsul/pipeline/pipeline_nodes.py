#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import numpy
import logging

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
import traits.api as traits
from traits.api import Enum
from traits.api import Str
from traits.api import Bool
from traits.api import Any
from traits.api import Undefined

# Capsul import
from capsul.utils.trait_utils import clone_trait
from capsul.utils.trait_utils import trait_ids
from capsul.utils.trait_utils import build_expression
from capsul.utils.trait_utils import eval_trait
from capsul.utils.trait_utils import is_trait_pathname

# Soma import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial


class Plug(Controller):
    """ Overload of the traits in oder to keep the pipeline memory.

    Attributes
    ----------
    enabled : bool
        user parameter to control the plug activation
    activated : bool
        parameter describing the Plug status
    output : bool
        parameter to set the Plug type (input or output)
    optional : bool
        parameter to create an optional Plug
    has_default_value : bool
        indicate if a value is available for that plug even if its not linked
    links_to : set (node_name, plug_name, node, plug, is_weak)
        the successor plugs of this  plug
    links_from : set (node_name, plug_name, node, plug, is_weak)
        the predecessor plugs of this plug
    """
    enabled = Bool(default_value=True)
    activated = Bool(default_value=False)
    output = Bool(default_value=False)
    optional = Bool(default_value=False)

    def __init__(self, **kwargs):
        """ Generate a Plug, i.e. a trait with the memory of the
        pipeline adjacent nodes.
        """
        super(Plug, self).__init__(**kwargs)
        # The links correspond to edges in the graph theory
        # links_to = successor
        # links_from = predecessor
        # A link is a tuple of the form (node, plug)
        self.links_to = set()
        self.links_from = set()
        # The has_default value flag can be set by setting a value for a
        # parameter in Pipeline.add_process
        self.has_default_value = False


class Node(Controller):
    """ Basic Node structure of the pipeline that need to be tuned.

    Attributes
    ----------
    name : str
        the node name
    full_name : str
        a unique name among all nodes and sub-nodes of the top level pipeline
    enabled : bool
        user parameter to control the node activation
    activated : bool
        parameter describing the node status

    Methods
    -------
    connect
    set_callback_on_plug
    get_plug_value
    set_plug_value
    get_trait
    """
    name = Str()
    enabled = Bool(default_value=True)
    activated = Bool(default_value=False)
    node_type = Enum(("processing_node", "view_node"))

    def __init__(self, pipeline, name, inputs, outputs):
        """ Generate a Node

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            the pipeline object where the node is added
        name: str (mandatory)
            the node name
        inputs: list of dict (mandatory)
            a list of input parameters containing a dictionary with default
            values (mandatory key: name)
        outputs: dict (mandatory)
            a list of output parameters containing a dictionary with default
            values (mandatory key: name)
        """
        super(Node, self).__init__()
        self.pipeline = pipeline
        self.name = name
        self.plugs = SortedDictionary()
        # _callbacks -> (src_plug_name, dest_node, dest_plug_name)
        self._callbacks = {}

        # generate a list with all the inputs and outputs
        # the second parameter (parameter_type) is False for an input,
        # True for an output
        parameters = zip(inputs, [False, ] * len(inputs))
        parameters.extend(zip(outputs, [True, ] * len(outputs)))
        for parameter, parameter_type in parameters:
            # check if parameter is a dictionary as specified in the
            # docstring
            if isinstance(parameter, dict):
                # check if parameter contains a name item
                # as specified in the docstring
                if "name" not in parameter:
                    raise Exception("Can't create parameter with unknown"
                                    "identifier and parameter {0}".format(
                                        parameter))
                parameter = parameter.copy()
                plug_name = parameter.pop("name")
                # force the parameter type
                parameter["output"] = parameter_type
                # generate plug with input parameter and identifier name
                plug = Plug(**parameter)
            else:
                raise Exception("Can't create Node. Expect a dict structure "
                                "to initialize the Node, "
                                "got {0}: {1}".format(type(parameter),
                                                      parameter))
            # update plugs list
            self.plugs[plug_name] = plug
            # add an event on plug to validate the pipeline
            plug.on_trait_change(pipeline.update_nodes_and_plugs_activation,
                                 "enabled")

        # add an event on the Node instance traits to validate the pipeline
        self.on_trait_change(pipeline.update_nodes_and_plugs_activation,
                             "enabled")

    @property
    def full_name(self):
        if self.pipeline.parent_pipeline:
            return self.pipeline.pipeline_node.full_name + '.' + self.name
        else:
            return self.name

    def _value_callback(self, source_plug_name, dest_node, dest_plug_name,
                        value):
        """ Spread the source plug value to the destination plug.
        """
        dest_node.set_plug_value(dest_plug_name, value)

    def connect(self, source_plug_name, dest_node, dest_plug_name):
        """ Connect linked plugs of two nodes

        Parameters
        ----------
        source_plug_name: str (mandatory)
            the source plug name
        dest_node: Node (mandatory)
            the destination node
        dest_plug_name: str (mandatory)
            the destination plug name
        """
        # add a callback to spread the source plug value
        value_callback = SomaPartial(self._value_callback, source_plug_name,
                                     dest_node, dest_plug_name)
        self._callbacks[(source_plug_name, dest_node,
                         dest_plug_name)] = value_callback
        self.set_callback_on_plug(source_plug_name, value_callback)

    def disconnect(self, source_plug_name, dest_node, dest_plug_name):
        """ disconnect linked plugs of two nodes

        Parameters
        ----------
        source_plug_name: str (mandatory)
            the source plug name
        dest_node: Node (mandatory)
            the destination node
        dest_plug_name: str (mandatory)
            the destination plug name
        """
        # remove the callback to spread the source plug value
        callback = self._callbacks.pop((source_plug_name, dest_node,
                                        dest_plug_name))
        self.remove_callback_from_plug(source_plug_name, callback)

    def __getstate__(self):
        """ Remove the callbacks from the default __getstate__ result because
        they prevent Node instance from being used with pickle.
        """
        state = super(Node, self).__getstate__()
        state['_callbacks'] = state['_callbacks'].keys()
        return state

    def __setstate__(self, state):
        """ Restore the callbacks that have been removed by __getstate__.
        """
        state['_callbacks'] = dict((i, SomaPartial(self._value_callback, *i))
                                   for i in state['_callbacks'])
        super(Node, self).__setstate__(state)
        for callback_key, value_callback in self._callbacks.iteritems():
            self.set_callback_on_plug(callback_key[0], value_callback)

    def set_callback_on_plug(self, plug_name, callback):
        """ Add an event when a plug change

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        callback: @f (mandatory)
            a callback function
        """
        self.on_trait_change(callback, plug_name)

    def remove_callback_from_plug(self, plug_name, callback):
        """ Remove an event when a plug change

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        callback: @f (mandatory)
            a callback function
        """
        self.on_trait_change(callback, plug_name, remove=True)

    def get_plug_value(self, plug_name):
        """ Return the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name

        Returns
        -------
        output: object
            the plug value
        """
        return getattr(self, plug_name)

    def set_plug_value(self, plug_name, value):
        """ Set the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        value: object (mandatory)
            the plug value we want to set
        """
        setattr(self, plug_name, value)

    def get_trait(self, trait_name):
        """ Return the desired trait

        Parameters
        ----------
        trait_name: str (mandatory)
            a trait name

        Returns
        -------
        output: trait
            the trait named trait_name
        """
        return self.trait(trait_name)


class ProcessNode(Node):
    """ Process node.

    Attributes
    ----------
    process : process instance
        the process instance stored in the pipeline node

    Methods
    -------
    set_callback_on_plug
    get_plug_value
    set_plug_value
    get_trait
    """
    def __init__(self, pipeline, name, process, **kwargs):
        """ Generate a ProcessNode

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            the pipeline object where the node is added.
        name: str (mandatory)
            the node name.
        process: instance
            a process/interface instance.
        kwargs: dict
            process default values.
        """
        self.process = process
        self.kwargs = kwargs
        inputs = []
        outputs = []
        for parameter, trait in self.process.user_traits().iteritems():
            if parameter in ('nodes_activation', 'selection_changed'):
                continue
            if trait.output:
                outputs.append(dict(name=parameter,
                                    optional=bool(trait.optional),
                                    output=True))
            else:
                inputs.append(dict(name=parameter,
                                   optional=bool(trait.optional or
                                                 parameter in kwargs)))
        super(ProcessNode, self).__init__(pipeline, name, inputs, outputs)

    def set_callback_on_plug(self, plug_name, callback):
        """ Add an event when a plug change

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        callback: @f (mandatory)
            a callback function
        """
        self.process.on_trait_change(callback, plug_name)

    def remove_callback_from_plug(self, plug_name, callback):
        """ Remove an event when a plug change

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        callback: @f (mandatory)
            a callback function
        """
        self.process.on_trait_change(callback, plug_name, remove=True)

    def get_plug_value(self, plug_name):
        """ Return the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name

        Returns
        -------
        output: object
            the plug value
        """
        if not isinstance(self.get_trait(plug_name).handler,
                          traits.Event):
            return getattr(self.process, plug_name)
        else:
            return None

    def set_plug_value(self, plug_name, value):
        """ Set the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        value: object (mandatory)
            the plug value we want to set
        """
        if value in ["", "<undefined>"]:
            value = Undefined
        elif is_trait_pathname(self.process.trait(plug_name)) and value is None:
            value = Undefined
        setattr(self.process, plug_name, value)

    def get_trait(self, trait_name):
        """ Return the desired trait

        Parameters
        ----------
        trait_name: str (mandatory)
            a trait name

        Returns
        -------
        output: trait
            the trait named trait_name
        """
        return self.process.trait(trait_name)


class PipelineNode(ProcessNode):
    """ A special node to store the pipeline user-parameters
    """
    pass


class IterativeNode(Node):
    """ A special node to store an iterative process.

    This node is dynamic and try to be updated when a trait value is modified.
    """
    def __init__(self, pipeline, name, process, iterative_plugs, do_not_export,
                 make_optional, **kwargs):
        """ Initialize the IterativeNode class.

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            the pipeline object where the node is added
        name: str (mandatory)
            the node name
        process: instance or string
            a process/interface instance or the corresponding string
            description
        iterative_plugs: list of str (optional)
            a list of plug names on which we want to iterate
        do_not_export: list of str (optional)
            a list of plug names that we do not want to export
        make_optional: list of str (optional)
            a list of plug names that we do not want to export
        """
        # Class parameters
        self.iterative_plugs = iterative_plugs
        self.iterative_process = process
        self.do_not_export = do_not_export
        self.make_optional = make_optional
        self.kwargs = kwargs
        self.process = None
        self.dynamic_node_callbacks = {}
        self.dynamic_process_callbacks = {}

        # Get the traits splited by type: input or output
        # If an iterative trait is found add an extra trait List level.
        # > inputs
        self.input_iterative_traits = {}
        self.input_traits = {}
        for (trait_name,
             trait) in self.iterative_process.traits(output=False).iteritems():

                # Get the trait string description
                trait_description = trait_ids(trait)

                # An iterative trait is found add an extra trait List level.
                if trait_name in self.iterative_plugs:
                    self.input_iterative_traits[trait_name] = ([
                        "List_" + x for x in trait_description], trait)

                # Otherwise just store the string trrait description
                else:
                    self.input_traits[trait_name] = (trait_description, trait)

        # > outputs
        self.output_iterative_traits = {}
        self.output_traits = {}
        for (trait_name,
             trait) in self.iterative_process.traits(output=True).iteritems():

            # Get the trait string description
            trait_description = trait_ids(trait)

            # An iterative trait is found add an extra trait List level.
            if trait_name in self.iterative_plugs:
                self.output_iterative_traits[trait_name] = ([
                    "List_" + x for x in trait_description], trait)

            # Otherwise just store the string trrait description
            else:
                self.output_traits[trait_name] = (trait_description, trait)

        # No regular output traits accepted in an iterative node
        if self.output_traits:
            raise Exception(
                "No regular output traits accepted in an iterative node, got "
                "{0}.".format(self.output_traits))

        # Inherit from node class
        input_traits = [
            dict(name=trait_name)
            for trait_name in self.iterative_process.traits(output=False)]
        output_traits = [
            dict(name=trait_name)
            for trait_name in self.iterative_process.traits(output=True)]
        super(IterativeNode, self).__init__(
            pipeline, name, input_traits, output_traits)

        # Add a trait for each input and each output
        for trait_name, trait_item in self.input_iterative_traits.iteritems():
            trait_description, trait = trait_item
            trait = clone_trait(trait_description)
            self.add_trait(trait_name, trait)
            self.trait(trait_name).output = False
        for trait_name, trait_item in self.input_traits.iteritems():
            expression = build_expression(trait_item[1])
            trait = eval_trait(expression)
            self.add_trait(trait_name, trait)
            self.trait(trait_name).output = False
            setattr(
                self, trait_name, getattr(self.iterative_process, trait_name))
            #self._anytrait_changed(
            #    trait_name, None, getattr(self.iterative_process, trait_name))
        for trait_name, trait_item in self.output_iterative_traits.iteritems():
            trait_description, trait = trait_item
            trait = clone_trait(trait_description)
            self.add_trait(trait_name, trait)
            self.trait(trait_name).output = True

        # Generate / update the iterative pipeline
        self.update_iterative_pipeline(0)

    def _anytrait_changed(self, name, old, new):
        """ Add an event that enables us to create process on the fly when an
        iterative input trait value has changed.

        .. note ::

            Wait to have the same number of items in iterative input traits
            to update the iterative pipeline.

        Parameters
        ----------
        name: str (mandatory)
            the trait name
        old: str (mandatory)
            the old value
        new: str (mandatory)
            the new value
        """
        # If an iterative plug has changed
        if (hasattr(self, "input_iterative_traits") and
           name in self.input_iterative_traits):

            # To refresh the iterative pipeline, need to have the same number
            # of items in iterative traits
            input_size = numpy.asarray([
                len(getattr(self, trait_name))
                for trait_name in self.input_iterative_traits])
            if len(input_size) != 0:
                nb_of_inputs = input_size[0]
                is_valid = (input_size == nb_of_inputs).all()
            else:
                nb_of_inputs = 0
                is_valid = True

            # Generate / update the iterative pipeline
            if is_valid:
                self.update_iterative_pipeline(nb_of_inputs)

    def update_iterative_pipeline(self, nb_of_inputs):
        """ Update the pipeline.

        Parameters
        ----------
        nb_of_inputs: int (mandatory)
            the number of input iterative trait items
        """
        # Local import
        from pipeline_iterative import IterativePipeline, IterativeManager

        # Create / recreate the iterative pipeline
        # > disconnect the iterative process if already crerated
        if self.process is not None:

            # Disconnect all iterative process traits and corresponding node
            #traits
            for trait_name, callback in self.dynamic_node_callbacks.iteritems():
                self.on_trait_change(callback, trait_name, remove=True)
            for trait_name, callback in self.dynamic_process_callbacks.iteritems():
                self.process.on_trait_change(callback, trait_name, remove=True)

        # > create the iterative pipeline
        self.process = IterativePipeline()

        # Go through all input regular traits
        pipeline_node = self.process.nodes[""]
        for trait_name, trait_item in self.input_traits.iteritems():
            expression = build_expression(trait_item[1])
            # FixMe
            if "Either" in expression:
                logger.warning(
                    "Capsul do not deal with either iterative traits. The "
                    "'{0}' trait with expression '{1}' will be temporary "
                    "replaced by a traits.Any type.".format(
                        trait_name, expression))
                expression = "traits.Any()"
            trait = eval_trait(expression)
            pipeline_node.process.add_trait(trait_name, trait)
            pipeline_node.process.trait(trait_name).optional = False
            pipeline_node.process.trait(trait_name).output = False
            pipeline_node.process.trait(trait_name).desc = (
                "a regular trait that will be repeted")
            setattr(
                pipeline_node.process, trait_name, getattr(self, trait_name))

        # Create the dynamic input output iterative traits manager subpipelines
        iterative_traits = {}
        for trait_name, trait_item in self.input_iterative_traits.iteritems():
            trait_description, trait = trait_item
            iterative_traits[trait_name] = (
                trait_description, getattr(self, trait_name))
        regular_traits = {}
        for trait_name, trait_item in self.input_traits.iteritems():
            trait_description, trait = trait_item
            regular_traits[trait_name] = (
                trait_description, getattr(self, trait_name))
        input_manager = IterativeManager(
            self.iterative_process.name, iterative_traits,
            regular_traits, is_input_traits=True)
        iterative_traits = {}
        for trait_name, trait_item in self.output_iterative_traits.iteritems():
            trait_description, trait = trait_item
            iterative_traits[trait_name] = (
                trait_description, [""] * nb_of_inputs)
        output_manager = IterativeManager(
            self.iterative_process.name, iterative_traits, None,
            is_input_traits=False)

        # Add manager node to the pipeline
        self.process.add_process("input_manager", input_manager)
        self.process.add_process("output_manager", output_manager)

        # Add processing nodes to the pipeline: only attached to input manager
        for node_name in input_manager.nodes:
            self.process.add_process(
                node_name, self.iterative_process.id,
                self.do_not_export, self.make_optional, **self.kwargs)

        # Add link to manager
        for link in input_manager.links:
            self.process.add_link(link)
        for link in output_manager.links:
            self.process.add_link(link)

        # Auto export nodes parameters
        self.process.autoexport_nodes_parameters()

        # Connect the iterative pipeline
        # > For input traits, connect the node traits to the iterative pipeline
        # traits
        for trait_name, trait_item in self.input_traits.iteritems():

            # Unpack the trait item
            trait_description, trait = trait_item

            # Update the iterative process trait.
            # Hook: function that will be called to update the iterative
            # process trait when the 'trait_name' node trait is modified.
            callback = SomaPartial(
                IterativeNode.update_iterative_process, self)

            # When the 'trait_name' node trait value is modified,
            # update the underlying corresponding iterative process trait
            self.on_trait_change(callback, name=trait_name)

            # Store the created callback
            self.dynamic_node_callbacks[trait_name] = callback

        # > For output traits, connect the iterative pipeline traits to the
        # node traits
        for trait_name, trait_item in self.output_iterative_traits.iteritems():

            # Unpack the trait item
            trait_description, trait = trait_item

            # Update the node trait.
            # Hook: function that will be called to update the node trait
            # when the 'trait_name' iterative pipeline trait is modified.
            callback = SomaPartial(IterativeNode.update_node, self)

            # When the 'trait_name' iterative process trait value is modified,
            # update the corresponding node trait
            self.process.on_trait_change(callback, name=trait_name)

            # Store the created callback
            self.dynamic_process_callbacks[trait_name] = callback

        # Get the largest element size
        element_sizes = []
        for node_name, node in self.process.nodes.iteritems():
            element_sizes.append(len(node_name))
            element_sizes.extend([len(x) for x in node.plugs])
        fixed_width = numpy.asarray(element_sizes).max() * 10.

        # Get the number of elements in the processing node
        fixed_height = len(self.iterative_process.user_traits()) * 50.

        # Set iterative pipeline node positions
        self.process.node_position = {
            "inputs": (0 * fixed_width, 0.),
            "input_manager": (1 * fixed_width, 0),
            "output_manager": (3 * fixed_width, 0.),
            "outputs": (4 * fixed_width, 0.),
        }
        shift = round(len(input_manager.nodes) / 2)
        for cnt, node_name in enumerate(input_manager.nodes):
            self.process.node_position[node_name] = (
                2 * fixed_width, (cnt - shift) * fixed_height)

    @staticmethod
    def update_iterative_process(iterative_node, parent, trait_name, old, new):
        """ Method to update the iterative process 'trait_name' trait.

        At the end the node and iterative process will have the same value in
        their 'trait_name' trait.

        Parameters
        ----------
        trait_name: str (mandatory)
            the name of the trait to synchronized.
        """
        setattr(iterative_node.process, trait_name,
                getattr(iterative_node, trait_name))

    @staticmethod
    def update_node(iterative_node, parent, trait_name, old, new):
        """ Method to update the node 'trait_name' trait.

        At the end the node and iterative process will have the same value in
        their 'trait_name' trait.

        Parameters
        ----------
        trait_name: str (mandatory)
            the name of the trait to synchronized.
        """
        setattr(iterative_node, trait_name,
                getattr(iterative_node.process, trait_name))


class Switch(Node):
    """ Switch node to select a specific Process.

    A switch commutes a group of inputs to its outputs, according to its
    "switch" trait value. Each group may be typically linked to a different
    process. Processes not "selected" by the switch are disabled, if possible.
    Values are also propagated through inputs/outputs of the switch
    (see below).

    Inputs / outputs:

    Say the switch "my_switch" has 2 outputs, "param1" and "param2". It will
    be connected to the outputs of 2 processing nodes, "node1" and "node2",
    both having 2 outputs: node1.out1, node1.out2, node2.out1, node2.out2.
    The switch will thus have 4 entries, in 2 groups, named for instance
    "node1" and "node2". The switch will link the outputs of node1 or
    node2 to its outputs. The switch inputs will be named as follows:

    * 1st group: "node1_switch_param1", "node1_switch_param2"
    * 2nd group: "node2_switch_param1", "node2_switch_param2"

    * When my_switch.switch value is "node1", my_switch.node1_switch_param1
      is connected to my_switch.param1 and my_switch.node1_switch_param2 is
      connected to my_switch.param2. The processing node node2 is disabled
      (unselected).
    * When my_switch.switch value is "node2", my_switch.node2_switch_param1
      is connected to my_switch.param1 and my_switch.node2_switch_param2 is
      connected to my_switch.param2. The processing node node1 is disabled
      (unselected).

    Values propagation:

    * When a switch is activated (its switch parameter is changed), the
      outputs will reflect the selected inputs, which means their values will
      be the same as the corresponding inputs.

    * But in many cases, parameters values will be given from the output
      (if the switch output is one of the pipeline outputs, this one will be
      visible from the "outside world, not the switch inputs). In this case,
      values set as a switch input propagate to its inputs.

    * An exception is when a switch input is linked to the parent pipeline
      inputs: its value is also visible from "outside" and should not be set
      via output values via the switch. In this specific case, output values
      are not propagated to such inputs.

    Notes
    -----
    Switch is normally not instantiated directly, but from a pipeline
    :py:meth:`pipeline_definition
    <capsul.pipeline.pipeline.Pipeline.pipeline_definition>` method

    Attributes
    ----------
    _switch_values : list
        the switch options
    _outputs: list
        the switch output parameters

    See Also
    --------
    _switch_changed
    _anytrait_changed
    capsul.pipeline.pipeline.Pipeline.add_switch
    capsul.pipeline.pipeline.Pipeline.pipeline_definition
    """

    def __init__(self, pipeline, name, inputs, outputs, make_optional=()):
        """ Generate a Switch Node

        Warnings
        --------
        The input plug names are built according to the following rule:
        <input_name>_switch_<output_name>

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            the pipeline object where the node is added
        name: str (mandatory)
            the switch node name
        inputs: list (mandatory)
            a list of options
        outputs: list (mandatory)
            a list of output parameters
        make_optional: sequence (optional)
            list of optional outputs.
            These outputs will be made optional in the switch output. By
            default they are mandatory.
        """
        # if the user pass a simple element, create a list and add this
        # element
        #super(Node, self).__init__()
        self.__block_output_propagation = False
        if not isinstance(outputs, list):
            outputs = [outputs, ]

        # check consistency
        if not isinstance(inputs, list) or not isinstance(outputs, list):
            raise Exception("The Switch node input and output parameters "
                            "are inconsistent: expect list, "
                            "got {0}, {1}".format(type(inputs), type(outputs)))

        # private copy of outputs and inputs
        self._outputs = outputs
        self._switch_values = inputs

        # format inputs and outputs to inherit from Node class
        flat_inputs = []
        for switch_name in inputs:
            flat_inputs.extend(["{0}_switch_{1}".format(switch_name, plug_name)
                                for plug_name in outputs])
        node_inputs = ([dict(name="switch"), ] +
                       [dict(name=i, optional=True) for i in flat_inputs])
        node_outputs = [dict(name=i, optional=(i in make_optional))
                        for i in outputs]
        # inherit from Node class
        super(Switch, self).__init__(pipeline, name, node_inputs,
                                     node_outputs)
        for node in node_inputs[1:]:
            self.plugs[node["name"]].enabled = False

        # add switch enum trait to select the process
        self.add_trait("switch", Enum(output=False, *inputs))

        # add a trait for each input and each output
        for i in flat_inputs:
            self.add_trait(i, Any(output=False))
        for i in outputs:
            self.add_trait(i, Any(output=True))

        # activate the switch first Process
        self._switch_changed(self._switch_values[0], self._switch_values[0])

    def _switch_changed(self, old_selection, new_selection):
        """ Add an event to the switch trait that enables us to select
        the desired option.

        Parameters
        ----------
        old_selection: str (mandatory)
            the old option
        new_selection: str (mandatory)
            the new option
        """
        self.__block_output_propagation = True
        self.pipeline.delay_update_nodes_and_plugs_activation()
        # deactivate the plugs associated with the old option
        old_plug_names = ["{0}_switch_{1}".format(old_selection, plug_name)
                          for plug_name in self._outputs]
        for plug_name in old_plug_names:
            self.plugs[plug_name].enabled = False

        # activate the plugs associated with the new option
        new_plug_names = ["{0}_switch_{1}".format(new_selection, plug_name)
                          for plug_name in self._outputs]
        for plug_name in new_plug_names:
            self.plugs[plug_name].enabled = True

        # refresh the pipeline
        self.pipeline.update_nodes_and_plugs_activation()

        # Refresh the links to the output plugs
        for output_plug_name in self._outputs:
            # Get the associated input name
            corresponding_input_plug_name = "{0}_switch_{1}".format(
                new_selection, output_plug_name)

            # Update the output value
            setattr(self, output_plug_name,
                    getattr(self, corresponding_input_plug_name))

            # Propagate the associated trait description
            out_trait = self.trait(output_plug_name)
            in_trait = self.trait(corresponding_input_plug_name)
            out_trait.desc = in_trait.desc

        self.pipeline.restore_update_nodes_and_plugs_activation()
        self.__block_output_propagation = False

    def _anytrait_changed(self, name, old, new):
        """ Add an event to the switch trait that enables us to select
        the desired option.

        Parameters
        ----------
        name: str (mandatory)
            the trait name
        old: str (mandatory)
            the old value
        new: str (mandatory)
            the new value
        """
        # if the value change is on an output of the switch, and comes from
        # an "external" assignment (ie not the result of switch action or
        # change in one of its inputs), then propagate the new value to
        # all corresponding inputs.
        # However those inputs which are connected to a pipeline input are
        # not propagated, to avoid cyclic feedback between outputs and inputs
        # inside a pipeline
        if hasattr(self, '_outputs') and not self.__block_output_propagation \
                and name in self._outputs:
            self.__block_output_propagation = True
            flat_inputs = ["{0}_switch_{1}".format(switch_name, name)
                           for switch_name in self._switch_values]
            for input_name in flat_inputs:
                # check if input is connected to a pipeline input
                plug = self.plugs[input_name]
                for link_spec in plug.links_from:
                    if isinstance(link_spec[2], PipelineNode) \
                            and not link_spec[3].output:
                        break
                else:
                    setattr(self, input_name, new)
            self.__block_output_propagation = False
        # if the change is in an input, change the corresponding output
        # accordingly.
        spliter = name.split("_switch_")
        if len(spliter) == 2 and spliter[0] in self._switch_values:
            switch_selection, output_plug_name = spliter
            self.__block_output_propagation = True
            setattr(self, output_plug_name, new)
            self.__block_output_propagation = False

    def __setstate__(self, state):
        self.__block_output_propagation = True
        super(Switch, self).__setstate__(state)
