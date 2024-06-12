"""
Node classes for CAPSUL process and pipeline elements

Classes
=======
:class:`Plug`
-------------
:class:`Node`
-------------
"""

import dataclasses
import typing
from typing import List, Literal

from soma.controller import Controller, field
from soma.controller.field import WritableField
from soma.sorted_dictionary import SortedDictionary
from soma.undefined import undefined
from soma.utils.functiontools import SomaPartial
from soma.utils.weak_proxy import get_ref, weak_proxy


class Plug(Controller):
    """A Plug is a connection point in a Node. It is normally linked to a node
    parameter (field).

    Attributes
    ----------
    enabled : bool
        user parameter to control the plug activation
    activated : bool
        parameter describing the Plug status
    output : bool
        parameter to set the Plug type (input or output). For a pipeline,
        this notion is seen from the "exterior" (the pipeline as a process
        inserted in another pipeline).
    optional : bool
        parameter to create an optional Plug
    has_default_value : bool
        indicate if a value is available for that plug even if its not linked
    links_to : set (node_name, plug_name, node, plug, is_weak)
        the successor plugs of this  plug
    links_from : set (node_name, plug_name, node, plug, is_weak)
        the predecessor plugs of this plug
    """

    enabled: bool = True
    activated: bool = True
    output: bool = False
    optional: bool = False

    def __init__(self, **kwargs):
        """Generate a Plug, i.e. an attribute with the memory of the
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
        self.has_default_value = kwargs.get("has_default_value", False)

    def __hash__(self):
        return id(self)


class Node(Controller):
    """Basic Node structure for pipeline elements

    In Capsul 3.x, :class:`~capsul.process.process.Process` and
    :class:`~capsul.pipeline.pipeline.Pipeline` classes directly inherit
    ``Node``, whereas they used to be contained in ``Node`` subclasses before.

    A Node is a :class:`~soma.controller.controller.Controller` subclass. It
    has parameters (fields) that represent the node parameters. Each parameter
    is associated with a :class:`Plug` which allows to connect to other nodes
    into a pipeline graph.

    Custom nodes can also be defined. To be usable in all
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
    pipeline: Pipeline instance or None
        the parent pipeline, kept as a weak proxy.
    name : str
        the node name
    full_name : str (property)
        a unique name among all nodes and sub-nodes of the top level pipeline
    plugs: dict
        {plug_name: Plug instance}

    Fields
    ------
    enabled : bool
        user parameter to control the node activation
    activated : bool
        parameter describing the node status
    node_type: str

    Methods
    -------
    set_plug_value
    """

    # name: field(type_=str, metadata={'hidden': True})
    name = ""  # doesn't need to be a field ?
    enabled: field(type_=bool, default=True, hidden=True)
    activated: field(type_=bool, default=True, hidden=True)
    node_type: field(
        type_=Literal["processing_node", "view_node"],
        default="processing_node",
        hidden=True,
    )

    nonplug_names = (  # 'name',
        "nodes_activation",
        "selection_changed",
        "enabled",
        "activated",
        "node_type",
        "protected_parameters",
        "pipeline_steps",
        "visible_groups",
    )

    def __init__(
        self, definition=None, pipeline=None, name=None, inputs=None, outputs=None
    ):
        """Generate a Node

        Parameters
        ----------
        definition: str
            The definition string defines the Node subclass in order to
            serialize it for execution. In most cases it is the module + class
            names ("capsul.pipeline.test.test_pipeline.MyPipeline" for
            instance).

            For a "locally defined" pipeline, we use the "custom_pipeline"
            string, in order to tell the serialization engine to use a JSON
            doct definition. The subclass
            :class:`~capsul.pipeline.pipeline.CustomPipeline`, and the function
            :meth:`Capsul.custom_pipeline <capsul.application.Capsul.custom_pipeline` take care of it.

            For a "locally defined" process, this definition should be given
            manually, and a locally defined process cannot be serialized, in a
            general way.

            The :meth:`Capsul.executable <capsul.application.Capsul.executable>` function sets this string
            up when possible.
        pipeline: Pipeline
            the pipeline object where the node is added
        name: str
            the node name
        inputs: dict
            a list of input parameters containing a dictionary with default
            values (mandatory key: name)
        outputs: dict
            a list of output parameters containing a dictionary with default
            values (mandatory key: name)
        """

        super().__init__()

        if definition is None:
            defn = []
            if self.__class__.__module__ != "__main__":
                defn.append(self.__class__.__module__)
            else:
                raise TypeError("No definition string given to local Node constructor")
            defn.append(self.__class__.__name__)
            definition = ".".join(defn)

        self.definition = definition

        if name is None:
            name = self.__class__.__name__
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
            output = field.is_output()
            optional = field.optional
            parameter = {
                "name": field.name,
                "output": output,
                "optional": optional,
                "has_default_value": field.has_default(),
            }
            # generate plug with input parameter and identifier name
            self._add_plug(parameter)

        # generate a list with all the inputs and outputs
        # the second parameter (parameter_type) is False for an input,
        # True for an output
        inputs = inputs or {}
        parameters = list(
            zip(
                inputs,
                [
                    False,
                ]
                * len(inputs),
            )
        )
        outputs = outputs or {}
        parameters.extend(
            list(
                zip(
                    outputs,
                    [
                        True,
                    ]
                    * len(outputs),
                )
            )
        )
        for parameter, parameter_type in parameters:
            # check if parameter is a dictionary as specified in the
            # docstring
            if isinstance(parameter, dict):
                # check if parameter contains a name item
                # as specified in the docstring
                if "name" not in parameter:
                    raise Exception(
                        f"Can't create parameter with unknown identifier and parameter {parameter}"
                    )
                parameter = parameter.copy()
                # force the parameter type
                parameter["output"] = parameter_type
                # generate plug with input parameter and identifier name
                self._add_plug(parameter)
            else:
                raise Exception(
                    f"Can't create Node. Expect a dict structure to initialize the Node, got {type(parameter)}: {parameter}"
                )

    def __del__(self):
        self._release_pipeline()

    def __hash__(self):
        return id(self)

    def user_fields(self):
        """
        Iterates over fields, excluding internal machinery fields such
        as "activated", "enabled", "node_type"...

        User fields normally correspond to plugs.
        """
        for f in self.fields():
            if f.name not in self.nonplug_names:
                yield f

    def set_pipeline(self, pipeline):
        from capsul.api import Pipeline

        self._release_pipeline()

        if pipeline is None:
            self.pipeline = None
            return

        self.pipeline = weak_proxy(pipeline)

        if isinstance(self.pipeline, Pipeline):
            for plug in self.plugs.values():
                # add an event on plug to validate the pipeline
                plug.on_attribute_change.add(
                    pipeline.update_nodes_and_plugs_activation, "enabled"
                )

            # add an event on the Node instance attributes to validate the pipeline
            self.on_attribute_change.add(
                pipeline.update_nodes_and_plugs_activation, "enabled"
            )

    def get_pipeline(self):
        if self.pipeline is None:
            return None
        try:
            return get_ref(self.pipeline)
        except ReferenceError:
            return None

    def _add_plug(self, parameter):
        # parameter = parameter.copy()
        plug_name = parameter.pop("name")

        plug = Plug(**parameter)
        # update plugs list
        self.plugs[plug_name] = plug

        if self.pipeline is not None:
            # add an event on plug to validate the pipeline
            plug.on_attribute_change.add(
                self.pipeline.update_nodes_and_plugs_activation, "enabled"
            )

    def _remove_plug(self, plug_name):
        plug = self.plugs[plug_name]
        pipeline = self.pipeline
        if pipeline is None and hasattr(self, "remove_link"):
            pipeline = self  # I am a pipeline
        if pipeline is not None:
            # remove the event on plug to validate the pipeline
            try:
                plug.on_attribute_change.remove(
                    pipeline.update_nodes_and_plugs_activation, "enabled"
                )
            except KeyError:
                pass  # there was no such callback. Nevermind.

            # clear/remove the associated plug links
            links_to_remove = []
            # use intermediary links_to_remove to avoid modifying
            # the links set while iterating on it...
            for link in plug.links_to:
                dst = f"{link[0]}.{link[1]}"
                links_to_remove.append(f"{plug_name}->{dst}")
            for link in plug.links_from:
                src = f"{link[0]}.{link[1]}"
                links_to_remove.append(f"{src}->{plug_name}")
            for link in links_to_remove:
                pipeline.remove_link(link)

        del self.plugs[plug_name]

    def _release_pipeline(self):
        if not hasattr(self, "pipeline") or self.pipeline is None:
            return  # nothing to do
        try:
            pipeline = get_ref(self.pipeline)
        except ReferenceError:
            return  # pipeline is deleted

        for plug in self.plugs.values():
            # remove the an event on plug to validate the pipeline
            plug.on_attribute_change.remove(
                self.pipeline.update_nodes_and_plugs_activation, "enabled"
            )

        # remove the event on the Node instance attributes
        self.on_attribute_change.remove(
            self.pipeline.update_nodes_and_plugs_activation, "enabled"
        )

        self.pipeline = None

    @property
    def full_name(self):
        if (
            getattr(self, "pipeline", None) is not None
            and self.pipeline.get_pipeline() is not None
        ):
            return self.pipeline.full_name + "." + self.name
        else:
            return self.name

    def set_optional(self, field_or_name, optional):
        # overload to set the optional state on the plug also
        field = self.ensure_field(field_or_name)
        field.optional = optional
        name = field.name
        plug = self.plugs[name]
        plug.optional = bool(optional)

    def add_field(self, name, type_, default=undefined, metadata=None, **kwargs):
        # delay notification until we have actually added the plug.
        enable_notif = self.enable_notification
        self.enable_notification = False
        if (
            (
                default is not undefined
                or (
                    "default_factory" in kwargs
                    and kwargs["default_factory"] != dataclasses._MISSING_TYPE
                )
            )
            and "optional" not in kwargs
            and (metadata is None or "optional" not in metadata)
        ):
            # a parameter with a default value becomes optional
            kwargs = dict(kwargs)
            kwargs["optional"] = True
        try:
            # overload to add the plug
            kwargs["field_type"] = WritableField
            kwargs["class_field"] = False
            super().add_field(name, type_, default=default, metadata=metadata, **kwargs)
        finally:
            self.enable_notification = enable_notif

        if name in self.nonplug_names:
            return
        field = self.field(name)
        parameter = {
            "name": name,
            "output": field.is_output(),
            "optional": field.optional,
            "has_default_value": field.has_default(),
        }
        # generate plug with input parameter and identifier name
        self._add_plug(parameter)
        # notify now the new field/plug
        if self.enable_notification:
            self.on_fields_change.fire()

    def remove_field(self, name):
        self._remove_plug(name)
        super().remove_field(name)

    def reorder_fields(self, fields=()):
        fields_set = set(fields)
        fields = list(fields) + [
            f.name
            for f in self.fields()
            if f.name not in fields_set and f.name in self._dyn_fields
        ]
        super().reorder_fields(fields)
        # reorder plugs as well as fields
        new_plugs = SortedDictionary()
        for name in fields:
            if name in self.plugs:
                new_plugs[name] = self.plugs[name]
        # append remaining ones in former order
        for name, plug in self.plugs.items():
            if name not in new_plugs:
                new_plugs[name] = plug
        self.plugs = new_plugs

    def __getstate__(self):
        """Remove the callbacks from the default __getstate__ result because
        they prevent Node instance from being used with pickle.
        """
        state = super().__getstate__()
        state["pipeline"] = get_ref(state["pipeline"])
        return state

    def __setstate__(self, state):
        """Restore the callbacks that have been removed by __getstate__."""
        if state["pipeline"] is state["process"]:
            state["pipeline"] = state["process"] = weak_proxy(state["pipeline"])
        else:
            state["pipeline"] = weak_proxy(state["pipeline"])
        super().__setstate__(state)

    def set_plug_value(self, plug_name, value, protected=None):
        """Set the plug value

        Parameters
        ----------
        plug_name: str (mandatory)
            a plug name
        value: object (mandatory)
            the plug value we want to set
        protected: None or bool (tristate)
            if True or False, force the "protected" status of the plug. If
            None, keep it as is.
        """
        if protected is not None:
            self.protect_parameter(plug_name, protected)
        setattr(self, plug_name, value)

    def get_connections_through(self, plug_name, single=False):
        """If the node has internal links (inside a pipeline, or in a switch
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
        """if True, the node will be represented as a Job in
        :somaworkflow:`Soma-Workflow <index.html>`. Otherwise the node is static
        and does not run.
        """
        return hasattr(self, "build_job")

    # def get_capsul_engine(self):
    #''' OBSOLETE '''
    # engine = getattr(self, 'engine', None)
    # if engine is None:
    # from capsul.engine import capsul_engine
    # engine = capsul_engine()
    # self.engine = engine
    # return engine

    # def set_capsul_engine(self, engine):
    #''' OBSOLETE '''
    # self.engine = engine
