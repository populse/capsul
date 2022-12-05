# -*- coding: utf-8 -*-
'''
Node classes for CAPSUL pipeline elements

Classes
=======
:class:`Plug`
-------------
:class:`Node`
-------------
:class:`ProcessNode`
--------------------
:class:`PipelineNode`
---------------------
:class:`Switch`
---------------
:class:`OptionalOutputSwitch`
-----------------------------
'''

from __future__ import print_function

# System import
from __future__ import absolute_import
import logging
import six
from six.moves import zip

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
import traits.api as traits
from traits.api import Enum
from traits.api import Str
from traits.api import Bool
from traits.api import Any
from traits.api import Undefined
from traits.api import File
from traits.api import Directory
from traits.api import TraitError

# Capsul import
from soma.controller.trait_utils import trait_ids
from soma.controller.trait_utils import is_trait_pathname

# Soma import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial
from soma.utils.weak_proxy import weak_proxy, get_ref

import os


class Plug(Controller):
    """ Overload of the traits in order to keep the pipeline memory.

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

    It is possible to define custom nodes inheriting Node. To be usable in all
    contexts (GUI construction, pipeline save / reload), custom nodes should
    define a few additional instance and class methods which will allow
    automatic systems (such as :func:`~capsul.study_config.get_node_instance`)
    to reinstantiate and save them:

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
    get_plug_value
    set_plug_value
    get_trait
    """
    name = Str(hidden=True)
    enabled = Bool(default_value=True, hidden=True)
    activated = Bool(default_value=False, hidden=True)
    node_type = Enum(("processing_node", "view_node"), hidden=True)

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
        self.pipeline = weak_proxy(pipeline, self._pipeline_deleted)
        self.name = name
        self.plugs = SortedDictionary()
        self.invalid_plugs = set()
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
        try:
            return get_ref(self._process)
        except AttributeError:
            raise AttributeError('%s object has no attribute process'
                                 % repr(self))
        except ReferenceError:
            raise ReferenceError(
                'The process underlying node %s, %s has been destroyed '
                'before the node that contains it.' % (self, self.name))
    
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
        try:
            dest_node.set_plug_value(
                dest_plug_name, value,
                self.is_parameter_protected(source_plug_name))
        except traits.TraitError:
            if isinstance(value, list) and len(value) == 1:
                # Nipype MultiObject, when a single object is involved, looks
                # like a single object but is actually a list. We want to
                # allow it to be linked to a "single object" plug.
                try:
                    dest_node.set_plug_value(
                        dest_plug_name, value[0],
                        self.is_parameter_protected(source_plug_name))
                except traits.TraitError:
                    pass

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

    def disconnect(self, source_plug_name, dest_node, dest_plug_name,
                   silent=False):
        """ disconnect linked plugs of two nodes

        Parameters
        ----------
        source_plug_name: str (mandatory)
            the source plug name
        dest_node: Node (mandatory)
            the destination node
        dest_plug_name: str (mandatory)
            the destination plug name
        silent: bool
            if False, do not fire an exception if the connection does not exust
            (perhaps already disconnected
        """
        # remove the callback to spread the source plug value
        try:
            callback = self._callbacks.pop(
                (source_plug_name, dest_node, dest_plug_name))
            self.remove_callback_from_plug(source_plug_name, callback)
        except Exception:
            if not silent:
                raise

    def _pipeline_deleted(self, pipeline):
        self.cleanup()

    def cleanup(self):
        """ cleanup before deletion

        disconnects all plugs, remove internal and cyclic references
        """
        try:
            pipeline = get_ref(self.pipeline)
        except Exception:
            pipeline = None

        for plug_name, plug in self.plugs.items():
            to_discard = []
            for link in plug.links_from:
                link[2].disconnect(link[1], self, plug_name, silent=True)
                self.disconnect(plug_name, link[2], link[1], silent=True)
                link[3].links_to.discard((self.name, plug_name,
                                          self, plug, True))
                to_discard.append(link)
            for link in to_discard:
                plug.links_from.discard(link)
            to_discard = []
            for link in plug.links_to:
                self.disconnect(plug_name, link[2], link[1], silent=True)
                link[2].disconnect(link[1], self, plug_name, silent=True)
                to_discard.append(link)
                link[3].links_from.discard((self.name, plug_name,
                                            self, plug, False))
            if pipeline:
                plug.on_trait_change(
                    pipeline.update_nodes_and_plugs_activation, remove=True)
        if pipeline:
            self.on_trait_change(pipeline.update_nodes_and_plugs_activation,
                                 remove=True)
        self._callbacks = {}
        self.pipeline = None
        self.plugs = {}

    def __getstate__(self):
        """ Remove the callbacks from the default __getstate__ result because
        they prevent Node instance from being used with pickle.
        Also remove the _weakref attribute eventually set by
        soma.utils.weak_proxy because it prevent Process instance
        from being used with pickle.
        """
        state = super(Node, self).__getstate__()
        state['_callbacks'] = [(c[0], get_ref(c[1]), c[2])
                               for c in state['_callbacks'].keys()]
        #state['pipeline'] = get_ref(state['pipeline'])
        state.pop('_weakref', None)
        state = {k: get_ref(v) for k, v in state.items()}
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

    def check_requirements(self, environment='global', message_list=None):
        '''
        Checks the process requirements against configuration settings values
        in the attached CapsulEngine. This makes use of the
        :meth:`requirements` method and checks that there is one matching
        config value for each required module.

        Parameters
        ----------
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
        capsul_engine = self.get_study_config().engine
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

    def get_missing_mandatory_parameters(self, exclude_links=False):
        ''' Returns a list of parameters which are not optional, and which
        value is Undefined or None, or an empty string for a File or
        Directory parameter.

        Parameters
        ----------
        exclude_links: bool
            if True, an empty parameter which has a link to another node
            will not be reported missing, since the execution
            will assign it a temporary value which will not prevent the
            pipeline from running.
        '''
        def check_trait(node, plug, trait, value, exclude_links):
            if trait.optional:
                return True
            if hasattr(trait, 'inner_traits') and len(trait.inner_traits) != 0:
                if value is Undefined:
                    return bool(trait.output)
                for i, item in enumerate(value):
                    j = min(i, len(trait.inner_traits) - 1)
                    if not check_trait(node, plug, trait.inner_traits[j],
                                       item, exclude_links):
                        return False
                return True
            if isinstance(trait.trait_type, (File, Directory)):
                if value not in (Undefined, None, '') \
                        or (trait.output
                            and trait.input_filename is not False):
                    return True
                if not exclude_links:
                    return False
                if trait.output:
                    links = plug.links_to
                else:
                    links = plug.links_from
                # check if there is a connection not going outside the
                # current pipeline
                end = [l for l in links if l[0] != '']
                if len(end) != 0:
                    return True  # it's connected.
                # otherwise check if there is a connection outside the
                # current pipeline
                end = [l for l in links if l[0] == '']
                for link in end:
                    p = link[2].plugs[link[1]]
                    if trait.output:
                        relinks = p.links_to
                    else:
                        relinks = p.links_from
                    if relinks:
                        return True  # it's connected.
                return False  # no other connection.
            return trait.output or value not in (Undefined, None)

        missing = []
        for name, plug in six.iteritems(self.plugs):
            trait = self.get_trait(name)
            if not trait.optional:
                value = self.get_plug_value(name)
                if not check_trait(self, plug, trait, value, exclude_links):
                    missing.append(name)
        return missing

    def get_study_config(self):
        ''' Get (or create) the StudyConfig this process belongs to
        '''
        study_config = getattr(self, 'study_config', None)
        if study_config is None:
            # Import cannot be done on module due to circular dependencies
            from capsul.study_config.study_config import default_study_config
            self.study_config = default_study_config()
        return self.study_config

    def set_study_config(self, study_config):
        ''' Set the StudyConfig this process belongs to
        '''
        self.study_config = study_config


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
            self.process = weak_proxy(process, self._process_deleted)
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
        try:
            self.process.on_trait_change(callback, plug_name, remove=True)
        except ReferenceError:
            pass  # process is deleted, just go on

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
            try:
                return getattr(self.process, plug_name)
            except TraitError:
                return Undefined
        else:
            return None

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
        if value in ["<undefined>"]:
            value = Undefined
        elif is_trait_pathname(self.process.trait(plug_name)) and value is None:
            value = Undefined
        self.process.set_parameter(plug_name, value, protected)

    def is_parameter_protected(self, plug_name):
        return self.process.is_parameter_protected(plug_name)

    def protect_parameter(self, plug_name, state=True):
        self.process.protect_parameter(plug_name, state)

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

    def is_job(self):
        return True


    def requirements(self):
        '''
        Requirements reimplementation for a process node. This node delegates
        to its underlying process. see
        :meth:`capsul.process.process.requirements`
        '''
        return self.process.requirements()

    def check_requirements(self, environment='global', message_list=None):
        '''
        Reimplementation of
        :meth:`capsul.pipeline.pipeline_nodes.Node.requirements` for a
        ProcessNode. This one delegates to its underlying process (or
        pipeline).

        .. see:: :meth:`capsul.process.process.check_requirements`
        '''
        return self.process.check_requirements(environment,
                                               message_list=message_list)

    def get_study_config(self):
        ''' Get (or create) the StudyConfig this process belongs to
        '''
        return self.process.get_study_config()

    def set_study_config(self, study_config):
        ''' Get (or create) the StudyConfig this process belongs to
        '''
        return self.process.set_study_config(study_config)

    def _process_deleted(self, process):
        self.cleanup()

    @property
    def study_config(self):
        try:
            return self.process.study_config
        except ReferenceError:
            return None

    @study_config.setter
    def study_config(self, value):
        try:
            self.process.study_config = value
        except ReferenceError:
            pass

    @study_config.deleter
    def study_config(self):
        try:
            del self.process.study_config
        except ReferenceError:
            pass

    @property
    def completion_engine(self):
        try:
            return self.process.completion_engine
        except ReferenceError:
            return None

    @completion_engine.setter
    def completion_engine(self, value):
        try:
            self.process.completion_engine = value
            if value is not None:
                # move the completion engine process to node level
                # in order to allow access to nodes links
                value.process = weak_proxy(self, value._clear_node)
        except ReferenceError:
            pass

    @completion_engine.deleter
    def completion_engine(self):
        try:
            del self.process.completion_engine
        except ReferenceError:
            pass


class PipelineNode(ProcessNode):
    """ A special node to store the pipeline user-parameters
    """
    def get_connections_through(self, plug_name, single=False):
        if not self.activated or not self.enabled:
            return []

        plug = self.plugs[plug_name]
        if plug.output:
            links = plug.links_from
        else:
            links = plug.links_to
        dest_plugs = []
        for link in links:
            done = False
            if not link[2].activated or not link[2].enabled:
                continue  # skip disabled nodes
            if link[2] is self:
                # other side of the pipeline
                if link[3].output:
                    more_links = link[3].links_to
                else:
                    more_links = link[3].links_from
                if not more_links:
                    # going outside the pipeline which seems to be top-level:
                    # keep it
                    dest_plugs.append((link[2], link[1], link[3]))
                    if single:
                        done = True
                for other_link in more_links:
                    other_end = other_link[2].get_connections_through(
                        other_link[1], single)
                    dest_plugs += other_end
                    if other_end and single:
                        done = True
                        break
            else:
                other_end = link[2].get_connections_through(link[1], single)
                dest_plugs += other_end
                if other_end and single:
                    done = True
            if done:
                break
        return dest_plugs


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

    _doc_path = 'api/pipeline.html#capsul.pipeline.pipeline_nodes.Switch'

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
            If given, this sequence should have the same size as outputs. It
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

    def connections(self):
        """ Returns the current internal connections between input and output
        plugs

        Returns
        -------
        connections: list
            list of internal connections
            [(input_plug_name, output_plug_name), ...]
        """
        return [('{0}_switch_{1}'.format(self.switch, plug_name), plug_name)
                for plug_name in self._outputs]

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

    def get_connections_through(self, plug_name, single=False):
        if not self.activated or not self.enabled:
            return []
        plug = self.plugs[plug_name]
        if plug.output:
            connected_plug_name = '%s_switch_%s' % (self.switch, plug_name)
        else:
            splitter = plug_name.split("_switch_")
            if len(splitter) != 2:
                # not a switch input plug
                return []
            connected_plug_name = splitter[1]
        connected_plug = self.plugs[connected_plug_name]
        if plug.output:
            links = connected_plug.links_from
        else:
            links = connected_plug.links_to
        dest_plugs = []
        for link in links:
            if link[2] is self.pipeline.pipeline_node:
                other_end = [(link[2], link[1], link[3])]
            else:
                other_end = link[2].get_connections_through(link[1], single)
            dest_plugs += other_end
            if other_end and single:
                break
        return dest_plugs

    def is_job(self):
        return False

    def get_switch_inputs(self):
        inputs = []
        for plug, trait in self.user_traits().items():
            if trait.output:
                continue
            ps = plug.split('_switch_')
            if len(ps) == 2 and ps[1] in self.user_traits() \
                    and self.trait(ps[1]).output:
                inputs.append(ps[0])
        return inputs

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('inputs', traits.List(traits.Str))
        c.add_trait('outputs', traits.List(traits.Str))
        c.add_trait('optional_params', traits.List(traits.Str))
        c.add_trait('output_types', traits.List(traits.Str))
        c.inputs = ['input_1', 'input_2']
        c.outputs = ['output']
        c.output_types = ['Any']
        return c

    def configured_controller(self):
        c = self.configure_controller()
        c.outputs = [plug for plug, trait in self.user_traits().items()
                     if trait.output]
        c.inputs = self.get_switch_inputs()
        c.output_types = [self.trait(p).trait_type.__class__.__name__
                          for p in self.outputs]
        c.optional_params = [self.trait(p).optional for p in self.inputs]

        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        node = Switch(pipeline, name, conf_controller.inputs,
                      conf_controller.outputs,
                      make_optional=conf_controller.optional_params,
                      output_types=conf_controller.output_types)
        return node


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

    _doc_path = 'api/pipeline.html' \
        '#capsul.pipeline.pipeline_nodes.OptionalOutputSwitch'

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

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('input', traits.Str)
        c.add_trait('output', traits.Str)
        c.input = 'input'
        c.output = 'output'
        return c

    def configured_controller(self):
        c = self.configure_controller()
        c.output = [plug for plug, trait in self.user_traits().items()
                    if trait.output][0]
        c.input = self.get_switch_inputs()[0]

        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        node = OptionalOutputSwitch(pipeline, name, conf_controller.input,
                                    conf_controller.output)
        return node
