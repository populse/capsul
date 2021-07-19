# -*- coding: utf-8 -*-
'''
:class:`CrossValidationFoldNode`
--------------------------------
'''


from __future__ import absolute_import
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import sys

class CrossValidationFoldNode(Node):
    '''
    This "inert" node filters a list to separate it into (typically) learn and
    test sublists.

    The "outputs" are "train" and "test" output traits.
    '''

    _doc_path = 'api/pipeline.html#crossvalidationfoldnode'

    def __init__(self, pipeline, name, input_type=None):
        in_traitsl = ['inputs', 'fold', 'nfolds']
        out_traitsl = ['train', 'test']
        in_traits = []
        out_traits = []
        for tr in in_traitsl:
            in_traits.append({'name': tr, 'optional': True})
        for tr in out_traitsl:
            out_traits.append({'name': tr, 'optional': True})
        super(CrossValidationFoldNode, self).__init__(
            pipeline, name, in_traits, out_traits)
        if input_type:
            ptype = input_type
        else:
            ptype = traits.Any(traits.Undefined)

        self.add_trait('inputs', traits.List(ptype, output=False))
        self.add_trait('fold', traits.Int())
        self.add_trait('nfolds', traits.Int(10))
        is_output = True  # not a choice for now.
        self.add_trait('train', traits.List(ptype, output=is_output))
        self.add_trait('test', traits.List(ptype, output=is_output))

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ['inputs', 'fold', 'nfolds']
        if update_callback is None:
            update_callback = self.filter_callback
        for name in inputs:
            self.on_trait_change(update_callback, name)

    def filter_callback(self):
        n = len(self.inputs) // self.nfolds
        ninc = len(self.inputs) % self.nfolds
        begin = self.fold * n + min((ninc, self.fold))
        end = min((self.fold + 1) * n + min((ninc, self.fold + 1)),
                  len(self.inputs))
        self.train = self.inputs[:begin] + self.inputs[end:]
        self.test =  self.inputs[begin:end]

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.trait('inputs').inner_traits[0].trait_type.__class__.__name__
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('param_type', traits.Str('Str'))
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
        node = CrossValidationFoldNode(pipeline, name, input_type=t)
        return node

    def params_to_command(self):
        return ['custom_job']

    def build_job(self, name=None, referenced_input_files=[],
                  referenced_output_files=[], param_dict=None):
        from soma_workflow.custom_jobs \
            import CrossValidationFoldJob
        if param_dict is None:
            param_dict = {}
        else:
            param_dict = dict(param_dict)
        param_dict['inputs'] = self.inputs
        param_dict['train'] = self.train
        param_dict['test'] = self.test
        param_dict['nfolds'] = self.nfolds
        param_dict['fold'] = self.fold
        job = CrossValidationFoldJob(
            name=name,
            referenced_input_files=referenced_input_files,
            referenced_output_files=referenced_output_files,
            param_dict=param_dict)
        return job
