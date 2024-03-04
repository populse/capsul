"""
:class:`StrCatNode`
-------------------
"""

from soma.controller import Any, Controller, type_from_str

from capsul.process.node import Node


class StrCatNode(Node):
    """
    This "inert" node concatenates its inputs (as strings) and generates the
    concatenation on one of its plugs. All plugs may be inputs or outputs.
    """

    _doc_path = "api/pipeline.html#strcatnode"

    def __init__(
        self,
        pipeline,
        name,
        params,
        concat_plug,
        outputs,
        make_optional=(),
        param_types=None,
    ):
        """
        Parameters
        ----------
        pipeline: Pipeline
            pipeline which will hold the node
        name: str
            node name
        params: list
            names of parameters to be concatenated
        concat_plug: str
            name of the concatenated plug (should not be part of params)
        outputs: list
            list of parameters names which are outputs. May include elements
            from params, and/or concat_plug
        make_optional: list
            list of plug names which should be optional.
        param_types: dict
            parameters types dict: {param_name: field_type_as_string}

        """
        param_types = param_types or {}
        node_inputs = [
            dict(name=i, optional=(i in make_optional))
            for i in params
            if i not in outputs
        ]
        node_outputs = [
            dict(name=i, optional=(i in make_optional)) for i in outputs if i in outputs
        ]
        if concat_plug in outputs:
            node_outputs.append(
                {"name": concat_plug, "optional": concat_plug in make_optional}
            )
        else:
            node_inputs.append(
                {"name": concat_plug, "optional": concat_plug in make_optional}
            )
        super().__init__(None, pipeline, name, node_inputs, node_outputs)
        self._concat_sequence = params
        self._concat_plug = concat_plug
        self.add_parameters(param_types)
        self.cat_callback()
        self.set_callbacks()

    def add_parameters(self, param_types=None):
        param_types = param_types or {}
        added_fields = [self._concat_plug]
        for name in self._concat_sequence + added_fields:
            plug = self.plugs[name]
            ptype = param_types.get(name)
            if ptype is None:
                ptype = Any
            self.add_field(name, ptype, output=plug.output, optional=plug.optional)

    def set_callbacks(self, update_callback=None):
        if update_callback is None:
            update_callback = self.cat_callback
        self.on_attribute_change.add(update_callback, self._concat_sequence)

    def cat_callback(self):
        result = "".join([getattr(self, name, "") for name in self._concat_sequence])
        setattr(self, self._concat_plug, result)

    def configured_controller(self):
        c = self.configure_controller()
        c.parameters = self._concat_sequence
        c.concat_plug = self._concat_plug
        param_types = [self.field(x).type_str() for x in c.parameters + [c.concat_plug]]
        c.outputs = [
            x for x in c.parameters + [c.concat_plug] if self.field(x).is_output()
        ]
        c.param_types = param_types
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("parameters", list[str], default_factory=list)
        c.add_field("concat_plug", str)
        c.add_field("outputs", list[str], default_factory=list)
        c.add_field("param_types", list[str], default_factory=lambda: ["str"])
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        params = [(x, x in conf_controller.outputs) for x in conf_controller.parameters]
        t = {}
        if conf_controller.param_types:
            for pname, ptype in zip(
                conf_controller.parameters + [conf_controller.concat_plug],
                conf_controller.param_types,
            ):
                t[pname] = type_from_str(ptype)
        node = StrCatNode(
            pipeline,
            name,
            conf_controller.parameters,
            conf_controller.concat_plug,
            conf_controller.outputs,
            param_types=t,
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
        from soma_workflow.custom_jobs import StrCatJob

        param_dict["input_names"] = self._concat_sequence
        param_dict["output_name"] = self._concat_plug
        # transmit values
        for param in self._concat_sequence:
            param_dict[param] = getattr(self, param)
        # [re] build the concatenated output
        self.cat_callback()
        param_dict[self._concat_plug] = getattr(self, self._concat_plug)
        referenced_input_files = referenced_input_files or []
        referenced_output_files = referenced_output_files or []
        job = StrCatJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict,
        )
        return job
