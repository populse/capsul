
from capsul.pipeline.pipeline_nodes import Node
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
    '''

    def __init__(self, pipeline, name, inputs, outputs, make_optional=(),
                 separator='', param_types={}):
        node_inputs = [dict(name=i, optional=True) for i in inputs]
        node_outputs = [dict(name=i, optional=(i in make_optional))
                        for i in outputs]
        if separator:
            node_inputs.append({'name': 'separator', 'optional': True})
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

    def set_callbacks(self, update_callback=None):
        inputs = [name for name, plug in six.iteritems(self.plugs)
                  if not plug.output]
        if len(inputs) == 0:
            return # no inputs, nothing will be done
        if not self.trait(self._output).output:
            inputs = inputs[:-1]
            if len(inputs) == 0:
                return # no inputs, nothing will be done
        if update_callback is None:
            update_callback = self.cat_callback
        for name in inputs:
            self.on_trait_change(update_callback, name)

    def cat_callback(self):
        inputs = [name for name, plug in six.iteritems(self.plugs)
                  if not plug.output and name != 'separator']
        sep = getattr(self, 'separator', '')
        result = sep.join([unicode(getattr(self, name)) for name in inputs])
        setattr(self, self._output, result)


