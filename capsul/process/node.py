# -*- coding: utf-8 -*-
'''
Node classes for CAPSUL process and pipeline elements

Classes
=======
:class:`Plug`
-------------
:class:`Node`
-------------
'''

import typing
from typing import Literal, List

from soma.controller import (Controller, field, is_path, field_type_str)
from soma.undefined import undefined
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial
from soma.utils.weak_proxy import weak_proxy, get_ref

class Plug(Controller):
    """ Overload of the fields in order to keep the pipeline memory.

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
    enabled : bool = True
    activated : bool = False
    output : bool = False
    optional : bool = False

    def __init__(self, **kwargs):
        """ Generate a Plug, i.e. an attribute with the memory of the
        pipeline adjacent nodes.
        """
        super().__init__(**kwargs)
        # The links correspond to edges in the graph theory
        # links_to = successor
        # links_from = predecessor
        # A link is a tuple of the form (node, plug)
        self.links_to = set()
        self.links_from = set()
        # The has_default value flag can be set by setting a value for a
        # parameter in Pipeline.add_process
        self.has_default_value = False

    def __hash__(self):
        return id(self)


class Node(Controller):
    """ Basic Node structure of the pipeline that need to be tuned.

    It is possible to define custom nodes inheriting Node. To be usable in all
    contexts (GUI construction, pipeline save / reload), custom nodes should
    define a few additional instance and class methods which will allow
    automatic systems to reinstantiate and save them:

    * configure_controller(cls): classmethod
        return a Controller instance which specifies parameters needed to build
        the node instance. Typically it may contain a parameters (plugs) list
        and other specifications.
    * configured_controller(self): instance method:
        on an instance, returns a Controller instance in the same shape as
        configure_controller above, but with values filled from the instance.
        This controller will allow saving parameters needed to instantiate
        again the node with the same state.
    * build_node(cls, pipeline, name, conf_controller): class method
        returns an instance of the node class, built using appropriate
        parameters (using configure_controller() or configured_controller()
        from another instance)

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
    set_plug_value
    """
    # name: field(type_=str, metadata={'hidden': True})
    name = ''  # doesn(t need to be a field ?
    enabled: field(type_=bool, default=True, hidden=True)
    activated: field(type_=bool, default=True, hidden=True)
    node_type: field(type_=Literal['processing_node', 'view_node'],
        default='processing_node', hidden=True)

    nonplug_names = (# 'name',
                     'nodes_activation', 'selection_changed',
                     'enabled', 'activated', 'node_type')

    def __init__(self, pipeline=None, name=None, inputs={}, outputs={}):
        """ Generate a Node

        Parameters
        ----------
        pipeline: Pipeline
            the pipeline object where the node is added
        name: str
            the node name
        inputs: list of dict
            a list of input parameters containing a dictionary with default
            values (mandatory key: name)
        outputs: dict
            a list of output parameters containing a dictionary with default
            values (mandatory key: name)
        """
        super().__init__()
        self.name = name
        self.pipeline = None
        self.plugs = SortedDictionary()
        self.invalid_plugs = set()
        # _callbacks -> (src_plug_name, dest_node, dest_plug_name)
        self._callbacks = {}

        self.set_pipeline(pipeline)

        # add plugs for existing (class or instance) fields
        for field in self.fields():  # noqa: F402
            if field.name in self.nonplug_names:
                continue
            output = field.metadata.get('output', False)
            optional = field.metadata.get('optional', False)
            parameter = {
                "name": field.name,
                "output" : output,
                "optional": optional,
            }
            # generate plug with input parameter and identifier name
            self._add_plug(parameter)

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
                # force the parameter type
                parameter["output"] = parameter_type
                # generate plug with input parameter and identifier name
                self._add_plug(parameter)
            else:
                raise Exception("Can't create Node. Expect a dict structure "
                                "to initialize the Node, "
                                "got {0}: {1}".format(type(parameter),
                                                      parameter))

    def __del__(self):
        self._release_pipeline()

    def __hash__(self):
        return id(self)

    def set_pipeline(self, pipeline):

        self._release_pipeline()

        if pipeline is None:
            self.pipeline = None
            return

        self.pipeline = weak_proxy(pipeline)

        for plug in self.plugs.values():
            # add an event on plug to validate the pipeline
            plug.on_attribute_change.add(
                pipeline.update_nodes_and_plugs_activation, "enabled")

        # add an event on the Node instance attributes to validate the pipeline
        self.on_attribute_change.add(
            pipeline.update_nodes_and_plugs_activation, "enabled")

    def _add_plug(self, parameter):
        # parameter = parameter.copy()
        plug_name = parameter.pop("name")

        plug = Plug(**parameter)
        # update plugs list
        self.plugs[plug_name] = plug

        if self.pipeline is not None:
            # add an event on plug to validate the pipeline
            plug.on_attribute_change.add(
                self.pipeline.update_nodes_and_plugs_activation, "enabled")

    def _remove_plug(self, plug_name):
        plug = self.plugs[plug_name]
        if self.pipeline is not None:
            # remove the event on plug to validate the pipeline
            plug.on_attribute_change.remove(
                self.pipeline.update_nodes_and_plugs_activation, "enabled")
        del self.plugs[plug_name]

    def _release_pipeline(self):
        if not hasattr(self, 'pipeline') or self.pipeline is None:
            return  # nothing to do
        try:
            pipeline = get_ref(self.pipeline)
        except ReferenceError:
            return  # pipeline is deleted

        for plug in self.plugs.values():
            # remove the an event on plug to validate the pipeline
            plug.on_attribute_change.remove(
                self.pipeline.update_nodes_and_plugs_activation, "enabled")

        # remove the event on the Node instance attributes
        self.on_attribute_change.remove(
            self.pipeline.update_nodes_and_plugs_activation, "enabled")

        self.pipeline = None

    @property
    def full_name(self):
        if self.pipeline is not None and self.pipeline.parent_pipeline:
            return self.pipeline.pipeline_node.full_name + '.' + self.name
        else:
            return self.name

    def add_field(self, name, type_, default=undefined, metadata=None,
                  **kwargs):
        # delay notification until we have actually added the plug.
        enable_notif = self.enable_notification
        self.enable_notification = False
        try:
            # overload to add the plug
            super().add_field(name, type_, default=default, metadata=metadata,
                              **kwargs)
        finally:
            self.enable_notification = enable_notif

        if name in self.nonplug_names:
            return
        field = self.field(name)
        parameter = {
            "name": name,
            "output": field.metadata.get('output', False),
            "optional": field.metadata.get('optional', False),
        }
        # generate plug with input parameter and identifier name
        self._add_plug(parameter)
        # notify now the new field/plug
        if self.enable_notification:
            self.on_fields_change.fire()

    def remove_field(self, name):
        self._remove_plug(name)
        super().remove_field(name)

    @staticmethod
    def _value_callback(self, source_plug_name, dest_node, dest_plug_name,
                        value):
        """ Spread the source plug value to the destination plug.
        """
        dest_node.set_plug_value(
            dest_plug_name, value,
            self.is_parameter_protected(source_plug_name))

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
        dest_node.set_plug_value(dest_plug_name, value,
                                 self.is_parameter_protected(source_plug_name))

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
        state = super().__getstate__()
        state['_callbacks'] = list(state['_callbacks'].keys())
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
        super().__setstate__(state)
        for callback_key, value_callback in self._callbacks.items():
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
        self.on_attribute_change.add(callback, plug_name)

    def remove_callback_from_plug(self, plug_name, callback):
        """ Remove an event when a plug change

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        callback: @f (mandatory)
            a callback function
        """
        self.on_attribute_change.remove(callback, plug_name)


    def set_plug_value(self, plug_name, value, protected=None):
        """ Set the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        value: object (mandatory)
            the plug value we want to set
        protected: None or bool (tristate)
            if True or False, force the "protected" status of the plug. If None,
            keep it as is.
        """
        if protected is not None:
            self.protect_parameter(plug_name, protected)
        setattr(self, plug_name, value)


    def get_connections_through(self, plug_name, single=False):
        """ If the node has internal links (inside a pipeline, or in a switch
        or other custom connection node), return the "other side" of the
        internal connection to the selected plug. The returned plug may be
        in an internal node (in a pipeline), or in an external node connected to the node.
        When the node is "opaque" (no internal connections), it returns the
        input plug.
        When the node is inactive / disabled, it returns [].

        Parameters
        ----------
        plug_name: str
            plug to get connections with
        single: bool
            if True, stop at the first connected plug. Otherwise return the
            list of all connected plugs.

        Returns
        -------
        connected_plug; list of tuples
            [(node, plug_name, plug), ...]
            Returns [(self, plug_name, plug)] when the plug has no internal
            connection.
        """
        if not self.activated or not self.enabled:
            return []
        else:
            return [(self, plug_name, self.plugs[plug_name])]

    def is_job(self):
      """ if True, the node will be represented as a Job in
      :somaworkflow:`Soma-Workflow <index.html>`. Otherwise the node is static
      and does not run.
      """
      return hasattr(self, 'build_job')

    def is_parameter_protected(self, plug_name):
        return self.metadata(plug_name, 'protected', False)

    def protect_parameter(self, plug_name, state=True):
        self.set_metadata(plug_name, 'protected', state)

    def requirements(self):
        '''
        Requirements needed to run the node. It is a dictionary which keys are
        config/settings modules and values are requests for them.

        The default implementation returns an empty dict (no requirements), and
        should be overloaded by processes which actually have requirements.

        Ex::

            {'spm': 'version >= "12" and standalone == "True"')
        '''
        return {}

    def check_requirements(self, capsul_engine, environment='global',
                           message_list=None):
        '''
        Checks the process requirements against configuration settings values
        in the attached CapsulEngine. This makes use of the
        :meth:`requirements` method and checks that there is one matching
        config value for each required module.

        Parameters
        ----------
        capsul_engine: CapsulEngine
            CapsulEngine containing the execution environment in which the
            requirements are tested.
        environment: str
            config environment id. Normally corresponds to the computing
            resource name, and defaults to "global".
        message_list: list
            if not None, this list will be updated with messages for
            unsatisfied requirements, in order to present the user with an
            understandable error.

        Returns
        -------
        config: dict, list, or None
            if None is returned, requirements are not met: the process cannot
            run. If a dict is returned, it corresponds to the matching config
            values. When no requirements are needed, an empty dict is returned.
            A pipeline, if its requirements are met will return a list of
            configuration values, because different nodes may require different
            config values.
        '''
        settings = capsul_engine.settings
        req = self.requirements()
        config = settings.select_configurations(environment, uses=req)
        success = True
        for module in req:
            module_name = settings.module_name(module)
            if module_name not in config:
                if message_list is not None:
                    message_list.append('requirement: %s is not met in %s'
                                        % (req, self.name))
                else:
                    # if no message is expected, then we can return immediately
                    # without checking further requirements. Otherwise we
                    # continue to get a full list of unsatisfied requirements.
                    return None
                success = False
                return None
        if success:
            return config
        else:
            return None
