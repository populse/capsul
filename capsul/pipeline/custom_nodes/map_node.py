'''
:class:`MapNode`
------------------------
'''


from capsul.pipeline.pipeline_nodes import Node, Plug
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class MapNode(Node):
    '''
    This "inert" node converts lists into series of single items. Typically an
    input named ``inputs`` is a list of items. The job will separate items and
    output each of them as an output parameter. The i-th item will be output as
    ``output_<i>`` by default.
    The inputs / outputs names can be customized using the parameters
    ``input_names`` and ``output_names``. Several lists can be split in the
    same node.
    The node will also output a ``lengths`` parameter which will contain the
    input lists lengths. This lengths can typically be input in reduce nodes to
    perform the reverse operation (see :class:`ReduceNode`).

    * ``input_names`` is a list of input parameters names, each being a list to
    be split. The default is ``['inputs']``
    * ``output_names`` is a list of patterns used to build output parameters
    names. Each item is a string containing a substitution pattern ``"%d"``
    which will be replaced with a number. The default is ``['output_%d']``.
    Each pattern will be used to replace items from the corresponding input in
    the same order. Thus ``input_names``  and ``output_names`` should be the
    same length.
    * all other parameters given in ``param_dict`` are passed to the output
    dictionary of the job, so that the job acts as a
    :class:`~soma_workflow.client_types.BarrierJob` for parameters which are
    not "mapped".



    '''

    def __init__(self, pipeline, name, input_names=['inputs'],
                 output_names=['output_%d'], input_types=None):
        in_traits = []
        #{'name': 'input_names', 'optional': True},
                     #{'name': 'output_names', 'optional': True}]
        out_traits = []

        if input_types:
            ptypes = input_types
        else:
            ptypes = [traits.File(traits.Undefined, output=False)] \
                * len(input_names)
        self.input_types  = ptypes

        for tr in input_names:
            in_traits.append({'name': tr, 'optional': False})
        super(MapNode, self).__init__(pipeline, name, in_traits, out_traits)

        #self.add_trait('input_names', traits.List(traits.Str, output=False))
        #self.add_trait('output_names', traits.List(traits.Str, output=False))
        for tr, ptype in zip(input_names, ptypes):
            self.add_trait(tr, traits.List(ptype, output=False))
        self.input_names = input_names
        self.output_names = output_names

        self.set_callbacks()

    def set_callbacks(self):
        self.on_trait_change(self.map_callback, self.input_names)

    def map_callback(self, obj, name, old_value, value):
        index = self.input_names.index(name)
        output = self.output_names[index]
        ptype = self.input_types[index]
        print('use output:', output)
        print('old:', old_value, ', new:', value)
        if old_value in (None, traits.Undefined):
            old_value = []
        if value in (None, traits.Undefined):
            value = []
        if len(old_value) > len(value):
            print('was longer')
            for i in range(len(old_value) - 1, len(value) - 1, -1):
                pname = output % i
                self.remove_trait(pname)
                # TODO: remove links to this plug
                if pname in self.plugs:
                    del self.plugs[pname]
        for i in range(len(old_value), len(value)):
            pname = output % i
            print('add trait:', pname)
            ptype = self._clone_trait(ptype,
                                      {'output': True, 'optional': True})
            self.add_trait(pname, ptype)
            plug = Plug(name=output % i, optional=True, output=True)
            self.plugs[pname] = plug
            plug.on_trait_change(
                self.pipeline.update_nodes_and_plugs_activation, "enabled")
        for i, val in enumerate(value):
            setattr(self, output % i, val)


    def configured_controller(self):
        c = self.configure_controller()
        c.input_names = self.input_names
        c.output_names = self.output_names
        c.input_types = [p.trait_type.__class__.__name__
                         for p in self.input_types]
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('input_types', traits.List(traits.Str))
        c.add_trait('input_names', traits.List(traits.Str))
        c.add_trait('output_names', traits.List(traits.Str))
        c.input_names = ['inputs']
        c.output_names = ['output_%d']
        c.input_types = ['File']
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = []
        for ptype in conf_controller.input_types:
            if ptype == 'Str':
                t.append(traits.Str(traits.Undefined))
            elif ptype == 'File':
                t.append(traits.File(traits.Undefined))
            elif ptype not in (None, traits.Undefined):
                t = getattr(traits, conf_controller.param_type)()
        node = MapNode(pipeline, name, conf_controller.input_names,
                       conf_controller.output_names, input_types=t)
        return node

    def params_to_command(self):
        return ['custom_job']

    def build_job(self, name=None, referenced_input_files=[],
                  referenced_output_files=[], param_dict=None):
        from soma_workflow.custom_jobs import MapJob
        param_dict = dict(param_dict)
        param_dict['input_names'] = self.input_names
        param_dict['output_names'] = self.output_names
        for index, pname in enumerate(self.input_names):
            value = getattr(self, pname)
            param_dict[pname] = value
            output_name = self.output_names[index]
            if value not in (None, traits.Undefined):
                for i in range(len(value)):
                    opname = = output_name % i
                    param_dict[opname] = getattr(self, opname)
        job = MapJob(name=name,
                     referenced_input_files=referenced_input_files,
                     referenced_output_files=referenced_output_files,
                     param_dict=param_dict)
        return job

