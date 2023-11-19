"""
:class:`CrossValidationFoldNode`
--------------------------------
"""

from capsul.process.node import Node
from soma.controller import Controller, Any, type_from_str, undefined


class CrossValidationFoldNode(Node):
    """
    This "inert" node filters a list to separate it into (typically) learn and
    test sublists.

    The "outputs" are "train" and "test" output fields.
    """

    _doc_path = "api/pipeline.html#crossvalidationfoldnode"

    def __init__(self, pipeline, name, input_type=None):
        in_fieldsl = ["inputs", "fold", "nfolds"]
        out_fieldsl = ["train", "test"]
        in_fields = []
        out_fields = []
        for tr in in_fieldsl:
            in_fields.append({"name": tr, "optional": True})
        for tr in out_fieldsl:
            out_fields.append({"name": tr, "optional": True})
        super().__init__(None, pipeline, name, in_fields, out_fields)
        if input_type:
            ptype = input_type
        else:
            ptype = Any

        self.add_field("inputs", list[ptype], output=False, default_factory=list)
        self.add_field("fold", int, default=0)
        self.add_field("nfolds", int, default=10)
        is_output = True  # not a choice for now.
        self.add_field("train", list[ptype], output=is_output, default_factory=list)
        self.add_field("test", list[ptype], output=is_output, default_factory=list)

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ["inputs", "fold", "nfolds"]
        if update_callback is None:
            update_callback = self.filter_callback
        for name in inputs:
            self.on_attribute_change.add(update_callback, name)

    def filter_callback(self):
        n = len(self.inputs) // self.nfolds
        ninc = len(self.inputs) % self.nfolds
        begin = self.fold * n + min((ninc, self.fold))
        end = min((self.fold + 1) * n + min((ninc, self.fold + 1)), len(self.inputs))
        self.train = self.inputs[:begin] + self.inputs[end:]
        self.test = self.inputs[begin:end]

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.field("inputs").type.__args__[0].__name__
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("param_type", str, default="str")
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = None
        if conf_controller.param_type not in (None, undefined):
            t = type_from_str(conf_controller.param_type)
        node = CrossValidationFoldNode(pipeline, name, input_type=t)
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
        from soma_workflow.custom_jobs import CrossValidationFoldJob

        if param_dict is None:
            param_dict = {}
        else:
            param_dict = dict(param_dict)
        param_dict["inputs"] = self.inputs
        param_dict["train"] = self.train
        param_dict["test"] = self.test
        param_dict["nfolds"] = self.nfolds
        param_dict["fold"] = self.fold
        job = CrossValidationFoldJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict,
        )
        return job
