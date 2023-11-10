# -*- coding: utf-8 -*-
"""
:class:`LeaveOneOutNode`
------------------------
"""


from __future__ import absolute_import
from capsul.process.node import Node
from soma.controller import Controller, Any, type_from_str


class LeaveOneOutNode(Node):
    """
    This "inert" node excludes one input from the list of inputs, to allow
    leave-one-out applications.
    The "outputs" may be either an output field (to serve as inputs to
    other nodes), or an input field (to assign output values to other nodes).
    """

    _doc_path = "api/pipeline.html#leaveoneoutnode"

    def __init__(
        self,
        pipeline,
        name,
        is_output=True,
        input_type=None,
        test_is_output=True,
        has_index=True,
    ):
        self.has_index = has_index
        in_fieldsl = ["inputs"]
        if has_index:
            in_fieldsl.append("index")
        if is_output:
            out_fieldsl = ["train"]
        else:
            out_fieldsl = []
            in_fieldsl.append("train")
        if test_is_output:
            out_fieldsl.append("test")
        else:
            in_fieldsl.append("test")
        in_fields = []
        out_fields = []
        for tr in in_fieldsl:
            in_fields.append({"name": tr, "optional": True})
        for tr in out_fieldsl:
            out_fields.append({"name": tr, "optional": True})
        super(LeaveOneOutNode, self).__init__(
            None, pipeline, name, in_fields, out_fields
        )
        if input_type:
            ptype = input_type
        else:
            ptype = Any

        self.add_field("inputs", list[ptype], output=False, default_factory=list)
        if has_index:
            self.add_field("index", int, default=0)
        self.add_field("train", list[ptype], output=is_output, default_factory=list)
        self.add_field("test", ptype, output=test_is_output)

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ["inputs", "test"]
        if self.has_index:
            inputs.append("index")
        if update_callback is None:
            update_callback = self.exclude_callback
        self.on_attribute_change.add(update_callback, inputs)

    def exclude_callback(self, value, old_value, name):
        if not self.has_index:
            try:
                index = self.inputs.index(self.test)
            except Exception:
                return
        else:
            index = self.index

        result = [x for i, x in enumerate(self.inputs) if i != index]
        self.train = result
        if self.has_index and index < len(self.inputs):
            self.test = self.inputs[index]

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.field("inputs").type.__args__[0].__class__.__name__
        c.is_output = self.field("train").is_output()
        c.test_is_output = self.field("test").is_output()
        c.has_index = self.has_index
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("param_type", str, default="str")
        c.add_field("is_output", bool, default=True)
        c.add_field("test_is_output", bool, default=True)
        c.add_field("has_index", bool, default=True)
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = type_from_str(conf_controller.param_type)
        node = LeaveOneOutNode(
            pipeline,
            name,
            conf_controller.is_output,
            input_type=t,
            test_is_output=conf_controller.test_is_output,
            has_index=conf_controller.has_index,
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
        from soma_workflow.custom_jobs import LeaveOneOutJob

        index = 0
        if self.has_index:
            index = self.index
        else:
            try:
                index = self.inputs.index(self.test)
            except Exception:
                pass
        param_dict = dict(param_dict)
        param_dict["index"] = index
        job = LeaveOneOutJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict,
        )
        return job
