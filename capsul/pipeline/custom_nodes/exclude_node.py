
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class ExcludeNode(Node):
    '''
    This "inert" node excludes one input from the list of inputs, to allow
    leave-one-out applicatons.
    The "outputs" may be either an output trait (to serve as inputs to
    other nodes), or an input trait (to assign output values to other nodes).
    '''

    def __init__(self, pipeline, name, is_output=True, input_type=None):
        in_traitsl = ['inputs', 'exclude']
        if is_output:
            out_traitsl = ['filtered']
        else:
            out_traitsl = []
            in_traitsl.append('filtered')
        in_traits = []
        out_traits = []
        for tr in in_traitsl:
            in_traits.append({'name': tr, 'optional': True})
        for tr in out_traitsl:
            out_traits.append({'name': tr, 'optional': True})
        super(ExcludeNode, self).__init__(pipeline, name, in_traits,
                                          out_traits)
        if input_type:
            ptype = input_type
        else:
            ptype = traits.Any(traits.Undefined)

        self.add_trait('inputs', traits.List(ptype, output=False))
        self.add_trait('exclude', ptype)
        self.add_trait('filtered', traits.List(ptype, output=is_output))

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ['inputs', 'exclude']
        if update_callback is None:
            update_callback = self.exclude_callback
        for name in inputs:
            self.on_trait_change(update_callback, name)

    def exclude_callback(self):
        result = [x for x in self.inputs if x != self.exclude]
        self.filtered =  result

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.trait('exclude').trait_type.__class__.__name__
        c.is_output = self.trait('filtered').output
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('param_type', traits.Str('Str'))
        c.add_trait('is_output', traits.Bool(True))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = None
        if conf_controller.param_type == 'Str':
            t = traits.Str(traits.Undefined)
        elif conf_controller.param_type == 'File':
            t = traits.File(traits.Undefined)
        elif conf_controller.param_type not in (None, traits.Undefined):
            t = getattr(traits, conf_controller.param_type)()
        node = ExcludeNode(pipeline, name, conf_controller.is_output,
                           input_type=t)
        return node

