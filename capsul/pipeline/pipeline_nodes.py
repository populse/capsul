#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# Trait import
try:
    import traits.api as traits
    from traits.api import (File, Float, Enum, Str, Int, Bool, List, Tuple,
        Instance, Any, Event, CTrait, Directory)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import (File, Float, Enum, Str, Int, Bool,
        List, Tuple, Instance, Any, Event, CTrait, Directory)

# Capsul import
from capsul.controller import Controller
from capsul.utils.sorted_dictionary import SortedDictionary
from capsul.process import get_process_instance


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
    links_to : set (node, plug)
        the successor plugs of this  plug
    links_from : set (node, plug)
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


class Node(Controller):
    """ Basic Node structure of the pipeline that need to be tuned.

    Attributes
    ----------
    name : str
        the node name
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
        def value_callback(value):
            """ Spread the source plug value to the destination plug
            """
            if (value is not None and self.plugs[source_plug_name].activated
                    and dest_node.plugs[dest_plug_name].activated):
                dest_node.set_plug_value(dest_plug_name, value)
        # add a callback to spread the source plug value
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
        del self._callbacks[(source_plug_name, dest_node,
                            dest_plug_name)]
        # self.set_callback_on_plug(source_plug_name)

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
            the pipeline object where the node is added
        name: str (mandatory)
            the node name
        process: instance or string
            a process/interface instance or the corresponding string
            description
        kwargs: dict
            process default values
        """
        self.process = get_process_instance(process, **kwargs)
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
        from traits.trait_base import _Undefined
        if value in ["", "<undefined>"]:
            value = _Undefined()
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


class Switch(Node):
    """ Switch node to select a specific Process.

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
    """

    def __init__(self, pipeline, name, inputs, outputs):
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
        """
        # if the user pass a simple element, create a list and add this
        # element
        super(Node, self).__init__()
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

        # add switch enum trait to select the process
        self.add_trait('switch', Enum(*inputs))

        # format inputs and outputs to inherit from Node class
        flat_inputs = []
        for switch_name in inputs:
            flat_inputs.extend(["{0}_switch_{1}".format(switch_name, plug_name)
                                for plug_name in outputs])
        node_inputs = ([dict(name="switch"), ] +
                       [dict(name=i, optional=True) for i in flat_inputs])
        node_outputs = [dict(name=i)
                        for i in outputs]
        # inherit from Node class
        super(Switch, self).__init__(pipeline, name, node_inputs,
                                     node_outputs)

        # add a trait for each input and each output
        for i in flat_inputs:
            self.add_trait(i, Any())
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
        # deactivate the plugs associated with the old option
        old_plug_names = ["{0}_switch_{1}".format(old_selection, plug_name)
                          for plug_name in self._outputs]
        for plug_name in old_plug_names:
            self.plugs[plug_name].activated = False
            self.plugs[plug_name].enabled = False

        # activate the plugs associated with the new option
        new_plug_names = ["{0}_switch_{1}".format(new_selection, plug_name)
                          for plug_name in self._outputs]
        for plug_name in new_plug_names:
            self.plugs[plug_name].activated = True
            self.plugs[plug_name].enabled = True

        # refresh the pipeline
        self.pipeline.update_nodes_and_plugs_activation()

        # refresh the links to the output plugs
        for output_plug_name in self._outputs:
            corresponding_input_plug_name = "{0}_switch_{1}".format(
                new_selection, output_plug_name)
            setattr(self, output_plug_name,
                    getattr(self, corresponding_input_plug_name))
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
        if hasattr(self, '_outputs') and not self.__block_output_propagation and name in self._outputs:
            self.__block_output_propagation = True
            flat_inputs = ["{0}_switch_{1}".format(switch_name, name) \
                for switch_name in self._switch_values]
            for input_name in flat_inputs:
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
