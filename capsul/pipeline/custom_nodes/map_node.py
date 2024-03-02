"""
:class:`MapNode`
------------------------
"""


from soma.controller import Controller, File, field, type_from_str, undefined

from capsul.process.node import Node, Plug


class MapNode(Node):
    """
    This node converts lists into series of single items. Typically an
    input named ``inputs`` is a list of items. The node will separate items and
    output each of them as an output parameter. The i-th item will be output as
    ``output_<i>`` by default.
    The inputs / outputs names can be customized using the constructor
    parameters ``input_names`` and ``output_names``. Several lists can be split
    in the same node.
    The node will also output a ``lengths`` parameter which will contain the
    input lists lengths. This lengths can typically be input in reduce nodes to
    perform the reverse operation (see
    :class:`~capsul.pipeline.custom_nodes.reduce_node.ReduceNode`).

    * ``input_names`` is a list of input parameters names, each being a list to
      be split. The default is ``['inputs']``
    * ``output_names`` is a list of patterns used to build output parameters
      names. Each item is a string containing a substitution pattern ``"%d"``
      which will be replaced with a number. The default is ``['output_%d']``.
      Each pattern will be used to replace items from the corresponding input
      in the same order. Thus ``input_names``  and ``output_names`` should be
      the same length.
    """

    _doc_path = "api/pipeline.html#mapnode"

    def __init__(
        self,
        pipeline,
        name,
        input_names=["inputs"],
        output_names=["output_%d"],
        input_types=None,
    ):
        in_fields = []
        out_fields = [{"name": "lengths", "optional": True}]

        if input_types:
            ptypes = input_types
        else:
            ptypes = [File] * len(input_names)
        self.input_types = ptypes

        for tr in input_names:
            in_fields.append({"name": tr, "optional": False})
        super().__init__(None, pipeline, name, in_fields, out_fields)

        for tr, ptype in zip(input_names, ptypes):
            self.add_field(tr, list[ptype], output=False, default_factory=list)
        self.add_field(
            "lengths",
            list[int],
            output=True,
            optional=True,
            default_factory=list,
            doc="lists lengths",
        )
        self.input_names = input_names
        self.output_names = output_names
        self.lengths = [0] * len(input_names)

        self.set_callbacks()

    def set_callbacks(self):
        self.on_attribute_change.add(self.map_callback, self.input_names)

    def map_callback(self, value, old_value, name, obj):
        index = self.input_names.index(name)
        output = self.output_names[index]
        ptype = self.input_types[index]
        if old_value in (None, undefined):
            old_value = []
        if value in (None, undefined):
            value = []
        if len(old_value) > len(value):
            for i in range(len(old_value) - 1, len(value) - 1, -1):
                pname = output % i
                self.remove_field(pname)
                if pname in self.plugs:
                    # remove links to this plug
                    plug = self.plugs[pname]
                    to_del = []
                    for link in plug.links_to:
                        linkd = (self, pname, link[2], link[1])
                        to_del.append(linkd)
                    for linkd in to_del:
                        self.pipeline.remove_link(linkd)
                    del self.plugs[pname]
        for i in range(len(old_value), len(value)):
            pname = output % i
            ptype = field(type_=ptype, output=True, optional=True)
            self.add_field(pname, ptype)
            plug = self.plugs[pname]
            plug.on_attribute_change.add(
                self.pipeline.update_nodes_and_plugs_activation, "enabled"
            )
        for i, val in enumerate(value):
            setattr(self, output % i, val)
        # update lengths
        lengths = self.lengths
        if not isinstance(lengths, list):
            lengths = []
        while len(lengths) <= index:
            lengths.append(0)
        lengths[index] = len(value)
        self.lengths = lengths

    def configured_controller(self):
        c = self.configure_controller()
        c.input_names = self.input_names
        c.output_names = self.output_names
        c.input_types = [p.type_str() for p in self.input_types]
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("input_types", list[str], default_factory=list)
        c.add_field("input_names", list[str], default_factory=list)
        c.add_field("output_names", list[str], default_factory=list)
        c.input_names = ["inputs"]
        c.output_names = ["output_%d"]
        c.input_types = ["File"]
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = []
        for ptype in conf_controller.input_types:
            t.append(type_from_str(ptype))
        node = MapNode(
            pipeline,
            name,
            conf_controller.input_names,
            conf_controller.output_names,
            input_types=t,
        )
        return node

    def params_to_command(self):
        return ["custom_job"]

    def build_job(
        self,
        name=None,
        referenced_input_files=[],
        referenced_output_files=[],
        param_dict=None,
    ):
        from soma_workflow.custom_jobs import MapJob

        param_dict = dict(param_dict)
        param_dict["input_names"] = self.input_names
        param_dict["output_names"] = self.output_names
        for index, pname in enumerate(self.input_names):
            value = getattr(self, pname, undefined)
            param_dict[pname] = value
            output_name = self.output_names[index]
            if value not in (None, undefined):
                for i in range(len(value)):
                    opname = output_name % i
                    param_dict[opname] = getattr(self, opname)
        job = MapJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict,
        )
        return job
