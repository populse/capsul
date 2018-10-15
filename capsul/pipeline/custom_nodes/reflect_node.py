
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class ReflectNode(Node):
    '''
    This "inert" node reflects its input from inputs to outputs or inversely.
    The node has either only inputs or only outputs, since the reflected
    parametrs are returned on the same side of the brick.
    '''

    def __init__(self, pipeline, name, inputs, outputs=None, output=False,
                 input_types={}):
        if not outputs:
            outputs = ['%s_reflect' % x for x in inputs]
        self._inputs = set(inputs)
        in_traits = []
        for tr in inputs + outputs:
            in_traits.append({'name': tr, 'optional': True})
        if output:
            out_traits = in_traits
            in_trais = []
        else:
            out_traits = []
        super(ReflectNode, self).__init__(pipeline, name, in_traits,
                                          out_traits)
        self.add_parameters(input_types)
        self.set_callbacks()

    def add_parameters(self, param_types={}):
        i = 0
        inputs = []
        ni = len(self._inputs)
        for name, plug in six.iteritems(self.plugs):
            if i < ni:
                inputs.append(name)
                ptype = param_types.get(name)
            else:
                ptype = param_types.get(inputs[i - ni])
            if ptype is None:
                ptype = traits.Any(traits.Undefined)
            self.add_trait(name, ptype)
            self.trait(name).output = plug.output
            self.trait(name).optional = plug.optional

    def set_callbacks(self, update_callback=None):
        if update_callback is None:
            update_callback = self.copy_callback
        for name in self.plugs:
            self.on_trait_change(update_callback, name)

    def copy_callback(self, name, new_value):
        params = self.plugs.keys()
        i = params.index(name)
        if i < len(self._inputs):
            output = params[i + len(self._inputs)]
        else:
            output = params[i - len(self._inputs)]
        setattr(self, output, new_value)

    def configured_controller(self):
        c = self.configure_controller()
        inputs = []
        outputs = []
        itypes = []
        for x in self.plugs:
            if x in self._inputs:
                print('configured_controller:', type(x), x)
                inputs.append(x)
                itypes.append(self.trait(x).trait_type.__class__.__name__)
            else:
                outputs.append(x)
        c.inputs = inputs
        c.input_types = itypes
        c.outputs = outputs
        c.is_output = self.trait(inputs[0]).output
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('inputs', traits.List(traits.Str()))
        c.add_trait('outputs', traits.List(traits.Str()))
        c.add_trait('is_output', traits.Bool(False))
        c.add_trait('input_types', traits.List(traits.Str('Str')))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = {}
        if conf_controller.input_types:
            for name, ptype in zip(conf_controller.inputs,
                                   conf_controller.input_types):
                t[name] = ptype
        node = ReflectNode(pipeline, name, conf_controller.inputs,
                           conf_controller.outputs,
                           output=conf_controller.is_output, input_types=t)
        return node

