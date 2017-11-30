##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
import logging
import six

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
from soma.controller.trait_utils import trait_ids
from soma.controller.trait_utils import is_trait_pathname

# Soma import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial
from soma.utils.weak_proxy import weak_proxy, get_ref


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
        self.pipeline = weak_proxy(pipeline)
        self.name = name
        self.plugs = SortedDictionary()
        # _callbacks -> (src_plug_name, dest_node, dest_plug_name)
        self._callbacks = {}

        # generate a list with all the inputs and outputs
        # the second parameter (parameter_type) is False for an input,
        # True for an output
        parameters = list(zip(inputs, [False, ] * len(inputs)))
        parameters.extend(list(zip(outputs, [True, ] * len(outputs))))
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
    def process(self):
        return get_ref(self._process)
    
    @process.setter
    def process(self, value):
        self._process = value
    
    
    @property
    def full_name(self):
        if self.pipeline.parent_pipeline:
            return self.pipeline.pipeline_node.full_name + '.' + self.name
        else:
            return self.name

    @staticmethod
    def _value_callback(self, source_plug_name, dest_node, dest_plug_name,
                        value):
        """ Spread the source plug value to the destination plug.
        """
        dest_node.set_plug_value(dest_plug_name, value)

    def _value_callback_with_logging(
            self, log_stream, prefix, source_plug_name, dest_node,
            dest_plug_name, value):
        """ Spread the source plug value to the destination plug, and log it in
        a stream for debugging.
        """
        #print '(debug) value changed:', self, self.name, source_plug_name, dest_node, dest_plug_name, repr(value), ', stream:', log_stream, prefix

        plug = self.plugs.get(source_plug_name, None)
        if plug is None:
            return
        def _link_name(dest_node, plug, prefix, dest_plug_name,
                       source_node_or_process):
            external = True
            sibling = False
            # check if it is an external link: if source is not a parent of dest
            if hasattr(source_node_or_process, 'process') \
                    and hasattr(source_node_or_process.process, 'nodes'):
                source_process = source_node_or_process
                source_node = source_node_or_process.process.pipeline_node
                children = [x for k, x in source_node.process.nodes.items()
                            if x != '']
                if dest_node in children:
                    external = False
            # check if it is a sibling node:
            # if external and source is not in dest
            if external:
                sibling = True
                #print >> open('/tmp/linklog.txt', 'a'), 'check sibling, prefix:', prefix, 'source:', source_node_or_process, ', dest_plug_name:', dest_plug_name, 'dest_node:', dest_node, dest_node.name
                if hasattr(dest_node, 'process') \
                        and hasattr(dest_node.process, 'nodes'):
                    children = [x for k, x in dest_node.process.nodes.items()
                                if x != '']
                    if source_node_or_process in children:
                        sibling = False
                    else:
                        children = [
                            x.process for x in children \
                            if hasattr(x, 'process')]
                    if source_node_or_process in children:
                        sibling = False
                #print 'sibling:', sibling
            if external:
                if sibling:
                    name = '.'.join(prefix.split('.')[:-2] \
                        + [dest_node.name, dest_plug_name])
                else:
                    name = '.'.join(prefix.split('.')[:-2] + [dest_plug_name])
            else:
                # internal connection in a (sub) pipeline
                name = prefix + dest_node.name
                if name != '' and not name.endswith('.'):
                  name += '.'
                name += dest_plug_name
            return name
        dest_plug = dest_node.plugs[dest_plug_name]
        #print >> open('/tmp/linklog.txt', 'a'), 'link_name:',  self, repr(self.name), ', prefix:', repr(prefix), ', source_plug_name:', source_plug_name, 'dest:', dest_plug, repr(dest_plug_name), 'dest node:', dest_node, repr(dest_node.name)
        print('value link:', \
            'from:', prefix + source_plug_name, \
            'to:', _link_name(dest_node, dest_plug, prefix, dest_plug_name,
                              self), \
            ', value:', repr(value), file=log_stream) #, 'self:', self, repr(self.name), ', prefix:',repr(prefix), ', source_plug_name:', source_plug_name, 'dest:', dest_plug, repr(dest_plug_name), 'dest node:', dest_node, repr(dest_node.name)
        log_stream.flush()

        # actually propagate
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
        value_callback = SomaPartial(
            self.__class__._value_callback, weak_proxy(self),
            source_plug_name, weak_proxy(dest_node), dest_plug_name)
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
        callback = self._callbacks.pop(
            (source_plug_name, dest_node, dest_plug_name))
        self.remove_callback_from_plug(source_plug_name, callback)

    def __getstate__(self):
        """ Remove the callbacks from the default __getstate__ result because
        they prevent Node instance from being used with pickle.
        """
        state = super(Node, self).__getstate__()
        state['_callbacks'] = state['_callbacks'].keys()
        state['pipeline'] = get_ref(state['pipeline'])
        return state

    def __setstate__(self, state):
        """ Restore the callbacks that have been removed by __getstate__.
        """
        state['_callbacks'] = dict((i, SomaPartial(self._value_callback, *i))
                                   for i in state['_callbacks'])
        if state['pipeline'] is state['process']:
            state['pipeline'] = state['process'] = weak_proxy(state['pipeline'])
        else:
            state['pipeline'] = weak_proxy(state['pipeline'])
        super(Node, self).__setstate__(state)
        for callback_key, value_callback in six.iteritems(self._callbacks):
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
        if process is pipeline:
            self.process = weak_proxy(process)
        else:
            self.process = process
        self.kwargs = kwargs
        inputs = []
        outputs = []
        for parameter, trait in six.iteritems(self.process.user_traits()):
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
        self.process.set_parameter(plug_name, value)

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

    def __init__(self, pipeline, name, inputs, outputs, make_optional=(),
                 output_types=None):
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
        output_types: sequence of traits (optional)
            If given, this sequence sould have the same size as outputs. It
            will specify each switch output parameter type (as a standard
            trait). Input parameters for each input block will also have this
            type.
        """
        # if the user pass a simple element, create a list and add this
        # element
        #super(Node, self).__init__()
        self.__block_output_propagation = False
        if not isinstance(outputs, list):
            outputs = [outputs, ]
        if output_types is not None:
            if not isinstance(output_types, list) \
                    and not isinstance(output_types, tuple):
                raise ValueError(
                    'output_types parameter should be a list or tuple')
            if len(output_types) != len(outputs):
                raise ValueError('output_types should have the same number of '
                                 'elements as outputs')
        else:
            output_types = [Any(Undefined)] * len(outputs)

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
            plug = self.plugs[node["name"]]
            plug.enabled = False

        # add switch enum trait to select the process
        self.add_trait("switch", Enum(output=False, *inputs))

        # add a trait for each input and each output
        input_types = output_types * len(inputs)
        for i, trait in zip(flat_inputs, input_types):
            self.add_trait(i, trait)
            self.trait(i).output = False
            self.trait(i).optional = self.plugs[i].optional
        for i, trait in zip(outputs, output_types):
            self.add_trait(i, trait)
            self.trait(i).output = True
            self.trait(i).optional = self.plugs[i].optional

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

        Propagates value through the switch, from in put to output if the
        switch state corresponds to this input, or from output to inputs.

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
        # accordingly, if the current switch selection is on this input.
        spliter = name.split("_switch_")
        if len(spliter) == 2 and spliter[0] in self._switch_values:
            switch_selection, output_plug_name = spliter
            if self.switch == switch_selection:
                self.__block_output_propagation = True
                setattr(self, output_plug_name, new)
                self.__block_output_propagation = False

    def __setstate__(self, state):
        self.__block_output_propagation = True
        super(Switch, self).__setstate__(state)


class OptionalOutputSwitch(Switch):
    ''' A switch which activates or disables its input/output link according
    to the output value. If the output value is not None or Undefined, the
    link is active, otherwise it is inactive.

    This kind of switch is meant to make a pipeline output optional, but still
    available for temporary files values inside the pipeline.

    Ex:

        A.output -> B.input

        B.input is mandatory, but we want to make A.output available and
        optional in the pipeline outputs. If we directlty export A.output, then
        if the pipeline does not set a value, B.input will be empty and the
        pipeline run will fail.

        Instead we can add an OptionalOutputSwitch between A.output and
        pipeline.output. If pipeline.output is set a valid value, then A.output
        and B.input will have the same valid value. If pipeline.output is left
        Undefined, then A.output and B.input will get a temporary value during
        the run.

    Technically, the OptionalOutputSwitch is currently implemented as a
    specialized switch node with two inputs and one output, and thus follows
    the inputs naming rules. The first input is the defined one, and the
    second, hidden one, is named "_none". As a consequence, its 1st input
    should be connected under the name "<input>_switch_<output> as in a
    standard switch.
    The "switch" input is hidden (not exported to the pipeline) and set
    automatically according to the output value.
    The implementation details may change in future versions.
    '''
    def __init__(self, pipeline, name, input, output):
        """ Generate an OptionalOutputSwitch Node

        Warnings
        --------
        The input plug name is built according to the following rule:
        <input>_switch_<output>

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            the pipeline object where the node is added
        name: str (mandatory)
            the switch node name
        input: str (mandatory)
            option
        output: str (mandatory)
            output parameter
        """
        super(OptionalOutputSwitch, self).__init__(
            pipeline, name, [input, '_none'], [output], [output])
        self.trait('switch').optional = True
        self.plugs['switch'].optional = True
        self.switch = '_none'
        pipeline.do_not_export.add((name, 'switch'))
        none_input = '_none_switch_%s' % output
        pipeline.do_not_export.add((name, none_input))
        # hide internal machinery plugs
        self.trait('switch').hidden = True
        self.plugs['switch'].hidden = True
        self.trait(none_input).hidden = True
        self.plugs[none_input].hidden = True

    def _anytrait_changed(self, name, old, new):
        """ Add an event to the switch trait that enables us to select
        the desired option.

        Propagates value through the switch, from output to input.

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
        if name == 'trait_added':
            return
        if hasattr(self, '_outputs') \
                and not self._Switch__block_output_propagation \
                and name in self._outputs:
            self._Switch__block_output_propagation = True
            # change the switch value according to the output value
            if new in (None, Undefined):
                self.switch = '_none'
            else:
                self.switch = self._switch_values[0]
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
            self._Switch__block_output_propagation = False
        # if the change is in an input, change the corresponding output
        # accordingly, if the current switch selection is on this input.
        spliter = name.split("_switch_")
        if len(spliter) == 2 and spliter[0] in self._switch_values:
            switch_selection, output_plug_name = spliter
            if self.switch == switch_selection:
                self._Switch__block_output_propagation = True
                setattr(self, output_plug_name, new)
                self._Switch__block_output_propagation = False
