
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class CatNode(Node):
    '''
    This "inert" node concatenates its inputs (as strings) and outputs the
    concatenation. If the node has no outputs, then the last input is
    considered to be the "output" string, which will then be an input and can
    be connected to another node output.

    Parameters
    ----------
    separator: str or None
        if not specified (None), then the node will have no separator parameter (meaning that it will not possible to set a different separator afterwards)
    '''

    def __init__(self, pipeline, name, inputs, outputs, make_optional=(),
                 separator=None, param_types={}):
        node_inputs = [dict(name=i, optional=True) for i in inputs]
        node_outputs = [dict(name=i, optional=(i in make_optional))
                        for i in outputs]
        if separator not in (None, traits.Undefined):
            node_inputs.insert(-1, {'name': 'separator', 'optional': True})
            param_types = dict(param_types)
            param_types['separator'] = traits.Str(separator)
        super(CatNode, self).__init__(pipeline, name, node_inputs,
                                      node_outputs)
        self.add_parameters(param_types)
        self.set_callbacks()

    def add_parameters(self, param_types={}):
        output = None
        last_input = None
        for name, plug in six.iteritems(self.plugs):
            ptype = param_types.get(name)
            if ptype is None:
                if plug.output:
                    ptype = traits.Str(traits.Undefined)
                else:
                    ptype = traits.Any(traits.Undefined)
            self.add_trait(name, ptype)
            self.trait(name).output = plug.output
            self.trait(name).optional = plug.optional
            if plug.output:
                if output is None:
                    output = name
            elif name != 'separator':
                last_input = name
        if output is not None:
            self._output = output
        else:
            self._output = last_input
        print('output:', self._output)

    def set_callbacks(self, update_callback=None):
        inputs = [name for name, plug in six.iteritems(self.plugs)
                  if not plug.output and name != self._output]
        if len(inputs) == 0:
            return # no inputs, nothing will be done
        if update_callback is None:
            update_callback = self.cat_callback
        for name in inputs:
            self.on_trait_change(update_callback, name)

    def cat_callback(self):
        inputs = [name for name, plug in six.iteritems(self.plugs)
                  if not plug.output and name != 'separator'
                      and name != self._output]
        sep = getattr(self, 'separator', '')
        if sep in (None, traits.Undefined):
            sep = ''
        result = sep.join([unicode(getattr(self, name)) for name in inputs])
        setattr(self, self._output, result)

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.trait(self._output).trait_type.__class__.__name__
        c.is_output = self.trait(self._output).output
        c.inputs = [name for name, plug in six.iteritems(self.plugs)
                    if not plug.output and name != 'separator'
                        and name != self._output]
        c.output = self._output
        c.separator = getattr(self, 'separator', None)
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('inputs', traits.List(traits.Str()))
        c.add_trait('separator', traits.Str(None))
        c.add_trait('output', traits.Str())
        c.add_trait('is_output', traits.Bool(True))
        c.add_trait('param_type', traits.Str('string'))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        inputs = list(conf_controller.inputs)
        if conf_controller.is_output:
            outputs = [conf_controller.output]
        else:
            outputs = []
            inputs.append(conf_controller.output)
        t = {}
        if conf_controller.param_type == 'string':
            t = dict((p, traits.Str(traits.Undefined))
                     for p in inputs + outputs)
        elif conf_controller.param_type == 'file':
            t = dict((p, traits.File(traits.Undefined))
                     for p in inputs + outputs)
        print('inputs:', inputs)
        print('outputs:', outputs)
        node = CatNode(pipeline, name, inputs, outputs,
                       separator=conf_controller.separator, param_types=t)
        return node

