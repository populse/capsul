"""
:class:`ReduceNode`
------------------------
"""

from soma.controller import Controller, File, Path, Union, type_from_str, undefined

from capsul.process.node import Node, Plug


class ReduceNode(Node):
    """
    Reduce node: converts series of inputs into lists. Typically a series of
    inputs named ``input_0`` .. ``input_<n>`` will be output as a single list
    named ``outputs``.

    Several input series can be handled by the node, and input names can be
    customized.

    * The numbers of inputs for each series is given as the ``lengths`` input
      parameter. It is typically linked from the output of a
      :class:`~capsul.pipeline.custom_nodes.map_node.MapNode`.
    * Input parameters names patterns are given as the ``input_names``
      parameter. It is a list of patterns, each containing a ``"%d"`` pattern
      for the input number. The default value is ``['input_%d']``.
    * Output parameters names are given as the ``output_names`` parameter. The
      default is ``['outputs']``.

    """

    _doc_path = "api/pipeline.html#reducenode"

    def __init__(
        self,
        pipeline,
        name,
        input_names=None,
        output_names=None,
        input_types=None,
    ):
        input_names = input_names or ["input_%d"]
        output_names = output_names or ["outputs"]
        in_fields = [
            {"name": "lengths", "optional": True},
            {"name": "skip_empty", "optional": True},
        ]
        out_fields = []

        if input_types:
            ptypes = input_types
        else:
            ptypes = [File] * len(input_names)
        self.input_types = ptypes

        for tr in output_names:
            out_fields.append({"name": tr, "optional": False})
        super().__init__(None, pipeline, name, in_fields, out_fields)

        for tr, ptype in zip(output_names, ptypes):
            self.add_field(
                tr,
                list[Union[ptype, type(undefined)]],
                output=True,
                default_factory=list,
            )
        self.add_field(
            "lengths",
            list[int],
            output=False,
            doc="lists lengths",
            default_factory=list,
        )
        self.add_field(
            "skip_empty",
            bool,
            default=False,
            output=False,
            doc="remove empty (Undefined, None, empty strings) from the output lists",
        )
        self.input_names = input_names
        self.output_names = output_names
        self.lengths = [0] * len(input_names)

        self.set_callbacks()

        self.lengths = [1] * len(input_names)

    def set_callbacks(self):
        self.on_attribute_change.add(self.resize_callback, "lengths")
        self.on_attribute_change.add(self.reduce_callback, "skip_empty")

    def resize_callback(self, value, old_value, name, obj):
        if old_value in (None, undefined):
            old_value = [0] * len(self.input_names)
        if value in (None, undefined):
            value = [0] * len(self.input_names)

        # remove former callback
        inputs = []
        for i, pname_p in enumerate(self.input_names):
            inputs += [pname_p % j for j in range(old_value[i])]
        self.on_attribute_change.remove(self.reduce_callback, inputs)

        # adjust sizes
        for in_index in range(len(value)):
            ptype = self.input_types[in_index]
            pname_p = self.input_names[in_index]
            oval = old_value[in_index]
            val = value[in_index]
            if oval > val:
                for i in range(oval - 1, val - 1, -1):
                    pname = pname_p % i
                    self.remove_field(pname)
                    if pname in self.plugs:
                        # remove links to this plug
                        plug = self.plugs[pname]
                        to_del = []
                        for link in plug.links_from:
                            linkd = (link[2], link[1], self, pname)
                            to_del.append(linkd)
                        for linkd in to_del:
                            self.pipeline.remove_link(linkd)
                    del self.plugs[pname]
            for i in range(oval, val):
                pname = pname_p % i
                self.add_field(pname, ptype, output=False, optional=False)
                plug = self.plugs[pname]
                plug.on_attribute_change.add(
                    self.pipeline.update_nodes_and_plugs_activation, "enabled"
                )
            if oval != val:
                ovalue = [getattr(self, pname_p % i, undefined) for i in range(val)]
                # if isinstance(ptype, (str, Path)):
                ## list field doesn't accept undefined as items
                # ovalue = [v # if v not in (None, undefined) else ''
                # for v in ovalue]
                setattr(self, self.output_names[in_index], ovalue)

        # setup new callback
        inputs = []
        for i, pname_p in enumerate(self.input_names):
            inputs += [pname_p % j for j in range(value[i])]
        self.on_attribute_change.add(self.reduce_callback, inputs)

    def reduce_callback(self, value, old_value, name, obj):
        # find out which input pattern is used
        in_index = None
        for index, pname_p in enumerate(self.input_names):
            for i in range(self.lengths[index]):
                pname = pname_p % i
                if name == pname:
                    in_index = index
                    break
            if in_index is not None:
                break
        if in_index is None:
            in_indices = range(len(self.input_names))
        else:
            in_indices = [in_index]
        for in_index in in_indices:
            output = self.output_names[in_index]
            value = [
                getattr(self, pname_p % i, undefined)
                for i in range(self.lengths[in_index])
            ]
            if self.skip_empty:
                value = [v for v in value if v not in (None, undefined, "")]
            # elif isinstance(self.input_types[in_index], (str, Path)):
            ## list field doesn't accept undefined as items
            # value = [v # if v not in (None, undefined) else undefined
            # for v in value]
            setattr(self, output, value)

    def configured_controller(self):
        c = self.configure_controller()
        c.input_names = self.input_names
        c.output_names = self.output_names
        c.input_types = [p.__class__.__name__ for p in self.input_types]
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("input_types", list[str], default_factory=list)
        c.add_field("input_names", list[str], default_factory=list)
        c.add_field("output_names", list[str], default_factory=list)
        c.input_names = ["input_%d"]
        c.output_names = ["outputs"]
        c.input_types = ["File"]
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = []
        for ptype in conf_controller.input_types:
            if ptype not in (None, undefined, "None", "NoneType", "<undefined>"):
                t.append(type_from_str(ptype))
        node = ReduceNode(
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
        referenced_input_files=None,
        referenced_output_files=None,
        param_dict=None,
    ):
        from soma_workflow.custom_jobs import MapJob

        param_dict = dict(param_dict)
        param_dict["input_names"] = self.input_names
        param_dict["output_names"] = self.output_names
        param_dict["lengths"] = self.lengths
        for index, pname_p in enumerate(self.input_names):
            for i in range(self.lengths[index]):
                pname = pname_p % i
                param_dict[pname] = getattr(self, pname, undefined)
            output_name = self.output_names[index]
            value = getattr(self, output_name, undefined)
            if value not in (None, undefined):
                param_dict[output_name] = value
        referenced_input_files = referenced_input_files or []
        referenced_output_files = referenced_output_files or []
        job = MapJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict,
        )
        return job
