
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class CatNode(Node):
    '''
    This "inert" node concatenates its inputs (as strings) and generates the
    concatenation on one of its plugs. All plugs may be inputs or outputs.
    '''

    def __init__(self, pipeline, name, params, concat_plug, outputs,
                 separator=None, make_optional=(), param_types={}):
        '''
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
        separator: str or None
            if not specified (None), then the node will have no separator
            parameter (meaning that it will not possible to set a different
            separator afterwards)
        make_optional: list
            list of plug names which should be optional.
        param_types: dict
            parameters types dict: {param_name: trait_type_as_string}

        '''
        node_inputs = [dict(name=i, optional=(i in make_optional))
                       for i in params if i not in outputs]
        node_outputs = [dict(name=i, optional=(i in make_optional))
                        for i in outputs if i in outputs]
        if concat_plug in outputs:
            node_outputs.append({'name': concat_plug,
                                 'optional': concat_plug in make_optional})
        else:
            node_inputs.append({'name': concat_plug,
                                'optional': concat_plug in make_optional})
        self._has_separator = False
        if separator not in (None, traits.Undefined):
            self._has_separator = True
            node_inputs.insert(-1, {'name': 'separator', 'optional': True})
            param_types = dict(param_types)
            param_types['separator'] = traits.Str(separator)
        super(CatNode, self).__init__(pipeline, name, node_inputs,
                                      node_outputs)
        self._concat_sequence = params
        self._concat_plug = concat_plug
        self.add_parameters(param_types)
        self.set_callbacks()

    def add_parameters(self, param_types={}):
        added_traits = [self._concat_plug]
        if self._has_separator:
            added_traits.insert(0, 'separator')
        for name in self._concat_sequence + added_traits:
            plug = self.plugs[name]
            ptype = param_types.get(name)
            if ptype is None:
                ptype = traits.Any(traits.Undefined)
            self.add_trait(name, ptype)
            self.trait(name).output = plug.output
            self.trait(name).optional = plug.optional

    def set_callbacks(self, update_callback=None):
        if self._has_separator:
            added_traits = ['separator']
        else:
            added_traits = []
        if update_callback is None:
            update_callback = self.cat_callback
        for name in self._concat_sequence + added_traits:
            self.on_trait_change(update_callback, name)

    def cat_callback(self):
        if self._has_separator:
            sep = getattr(self, 'separator', '')
            if sep in (None, traits.Undefined):
                sep = ''
        else:
            sep = ''
        result = sep.join([unicode(getattr(self, name))
                           for name in self._concat_sequence])
        setattr(self, self._concat_plug, result)

    def configured_controller(self):
        c = self.configure_controller()
        c.parameters = self._concat_sequence
        c.concat_plug = self._concat_plug
        param_types = [self.trait(x).trait_type.__class__.__name__
                       for x in c.parameters + [c.concat_plug]]
        c.outputs = [x for x in c.parameters + [c.concat_plug]
                     if self.trait(x).output]
        if self._has_separator:
            param_types.append(
                self.trait('separator').trait_type.__class__.__name__)
            c.separator = self.separator
        c.param_types = param_types
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('parameters', traits.List(traits.Str()))
        c.add_trait('separator', traits.Str(None))
        c.add_trait('concat_plug', traits.Str())
        c.add_trait('outputs', traits.List(traits.Str()))
        c.add_trait('param_types', traits.List(traits.Str('Str')))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        params = [(x, x in conf_controller.outputs) for x in conf_controller.parameters]
        t = {}
        if conf_controller.param_types:
            for name, ptype in zip(conf_controller.parameters
                                   + [conf_controller.concat_plug],
                                   conf_controller.param_types):
                t[name] = getattr(traits, ptype)()
        node = CatNode(pipeline, name, conf_controller.parameters,
                       conf_controller.concat_plug,
                       conf_controller.outputs,
                       separator=conf_controller.separator, param_types=t)
        return node

