'''
:class:`LeaveOneOutNode`
------------------------
'''


from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class LeaveOneOutNode(Node):
    '''
    This "inert" node excludes one input from the list of inputs, to allow
    leave-one-out applicatons.
    The "outputs" may be either an output trait (to serve as inputs to
    other nodes), or an input trait (to assign output values to other nodes).
    '''

    def __init__(self, pipeline, name, is_output=True, input_type=None,
                 test_is_output=True):
        in_traitsl = ['inputs', 'index']
        if is_output:
            out_traitsl = ['train']
        else:
            out_traitsl = []
            in_traitsl.append('train')
        if test_is_output:
            out_traitsl.append('test')
        else:
            in_traitsl.append('test')
        in_traits = []
        out_traits = []
        for tr in in_traitsl:
            in_traits.append({'name': tr, 'optional': True})
        for tr in out_traitsl:
            out_traits.append({'name': tr, 'optional': True})
        super(LeaveOneOutNode, self).__init__(pipeline, name, in_traits,
                                              out_traits)
        if input_type:
            ptype = input_type
        else:
            ptype = traits.Any(traits.Undefined)

        self.add_trait('inputs', traits.List(ptype, output=False))
        self.add_trait('index', traits.Int(0))
        self.add_trait('train', traits.List(ptype, output=is_output))
        self.add_trait('test', ptype)
        self.trait('test').output = test_is_output
        self.trait('train').inner_traits[0].output = is_output

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ['inputs', 'index']
        if update_callback is None:
            update_callback = self.exclude_callback
        self.on_trait_change(update_callback, inputs)

    def exclude_callback(self, name):
        if name == 'test':
            self.index = self.inputs.index(self.test)
        else:
            result = [x for i, x in enumerate(self.inputs) if i != self.index]
            self.train =  result
            self.test = self.inputs[self.index]

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = \
            self.trait('inputs').inner_traits[0].trait_type.__class__.__name__
        c.is_output = self.trait('train').output
        c.test_is_output = self.trait('test').output
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('param_type', traits.Str('Str'))
        c.add_trait('is_output', traits.Bool(True))
        c.add_trait('test_is_output', traits.Bool(True))
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
        node = LeaveOneOutNode(pipeline, name, conf_controller.is_output,
                               input_type=t, test_is_output=conf_controller.test_is_output)
        return node

    def params_to_command(self):
        return ['custom_job']

    def build_job(self, name=None, referenced_input_files=[],
                  referenced_output_files=[], param_dict=None):
        from soma_workflow.custom_jobs import LeaveOneOutJob
        job = LeaveOneOutJob(name=name,
                             referenced_input_files=referenced_input_files,
                             referenced_output_files=referenced_output_files,
                             param_dict=param_dict)
        return job

