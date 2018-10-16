
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class InertNode(Node):
    '''
    This "inert" node does just nothing. It can be used to attach links to
    plugs. A typical use is a "reflector", which allows to connect indirectly
    two inputs or two outputs.
    '''

    def __init__(self, pipeline, name, inputs, outputs, make_optional = (),
                 param_types={}):
        node_inputs = [dict(name=i, optional=(i in make_optional))
                       for i in inputs]
        node_outputs = [dict(name=i, optional=(i in make_optional))
                        for i in outputs]
        super(InertNode, self).__init__(pipeline, name, node_inputs,
                                      node_outputs)
        self.add_parameters(param_types)

    def add_parameters(self, param_types={}):
        for name, plug in six.iteritems(self.plugs):
            ptype = param_types.get(name)
            if ptype is None:
                ptype = traits.Any(traits.Undefined)
            self.add_trait(name, ptype)
            self.trait(name).output = plug.output
            self.trait(name).optional = plug.optional

    def configured_controller(self):
        c = self.configure_controller()
        c.inputs = [name for name, plug in six.iteritems(self.plugs)
                    if not plug.output]
        c.outputs = [name for name, plug in six.iteritems(self.plugs)
                     if plug.output]
        c.param_types = [self.trait(x).trait_type.__class__.__name__
                         for x in c.inputs + c.outputs]
        c.optional_plugs = [x for x in c.inputs + c.outputs
                            if self.trait(x).optional]
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('inputs', traits.List(traits.Str()))
        c.add_trait('outputs', traits.List(traits.Str()))
        c.add_trait('param_types', traits.List(traits.Str('Str')))
        c.add_trait('optional_plugs', traits.List(traits.Str()))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = {}
        if conf_controller.param_types:
            for name, ptype in zip(conf_controller.inputs
                                   + conf_controller.outputs,
                                   conf_controller.param_types):
                t[name] = getattr(traits, ptype)()
        node = InertNode(pipeline, name, conf_controller.inputs,
                         conf_controller.outputs,
                         make_optional=conf_controller.optional_plugs,
                         param_types=t)
        return node

