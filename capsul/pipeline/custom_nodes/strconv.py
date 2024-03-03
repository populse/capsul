"""
:class:`StrConvNode`
--------------------------------
"""

from soma.controller import Any, Controller, type_from_str, undefined

from capsul.process.node import Node


class StrConvNode(Node):
    """
    This "inert" node converts the input into a string.

    """

    _doc_path = "api/pipeline.html#strconvnode"

    def __init__(self, pipeline, name, input_type=None):
        in_fieldsl = ["input"]
        out_fieldsl = ["output"]
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

        self.add_field("input", ptype, output=False)
        is_output = True  # not a choice for now.
        self.add_field("output", str, output=is_output)
        self.input = 0
        self.filter_callback(0, 0, "input")

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ["input"]
        if update_callback is None:
            update_callback = self.filter_callback
        for name in inputs:
            self.on_attribute_change.add(update_callback, name)

    def filter_callback(self, value, old_value, name):
        self.output = self.input

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.field("input").type_str()
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_field("param_type", str, default="Any")
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = None
        if conf_controller.param_type not in (None, undefined):
            t = type_from_str(conf_controller.param_type)
        node = StrConvNode(pipeline, name, input_type=t)
        return node

    def is_job(self):
        return False

    def get_connections_through(self, plug_name, single=False):
        if not self.activated or not self.enabled:
            return []
        plug = self.plugs[plug_name]
        if plug.output:
            connected_plug_name = "input"
        else:
            connected_plug_name = "output"
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
