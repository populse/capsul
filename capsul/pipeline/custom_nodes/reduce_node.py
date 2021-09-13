# -*- coding: utf-8 -*-
'''
:class:`ReduceNode`
------------------------
'''

from __future__ import print_function

from __future__ import absolute_import
from capsul.pipeline.pipeline_nodes import Node, Plug
from soma.controller import Controller
import traits.api as traits
import sys
from six.moves import range
from six.moves import zip


class ReduceNode(Node):
    '''
    Reduce node: converts series of inputs into lists. Typically a series of
    inputs named ``input_0`` .. ``input_<n>`` will be output as a single list
    named ``outputs``.

    Several input series can be handled by the node, and input names can be
    customized.

    * The numbers of inputs for each series is given as the ``lengths`` input
      parameter. It is typically linked from the output of a
      :class:`~capsul.pipeline.custom_nodes.map_node.MapNode`.
    * Input parameters names patterns are given as the ``input_names``
      parameter. It is a list of patterns, each containing a ``"%d"`` pattern
      for the input number. The default value is ``['input_%d']``.
    * Output parameters names are given as the ``output_names`` parameter. The
      default is ``['outputs']``.

    '''

    _doc_path = 'api/pipeline.html#reducenode'

    def __init__(self, pipeline, name, input_names=['input_%d'],
                 output_names=['outputs'], input_types=None):
        in_traits = [{'name': 'lengths', 'optional': True},
                     {'name': 'skip_empty', 'optional': True}]
        out_traits = []

        if input_types:
            ptypes = input_types
        else:
            ptypes = [traits.File(traits.Undefined, output=False)] \
                * len(input_names)
        self.input_types = ptypes

        for tr in output_names:
            out_traits.append({'name': tr, 'optional': False})
        super(ReduceNode, self).__init__(pipeline, name, in_traits, out_traits)

        for tr, ptype in zip(output_names, ptypes):
            self.add_trait(tr,
                           traits.List(traits.Either(ptype, traits.Undefined),
                                       output=True))
        self.add_trait('lengths', traits.List(traits.Int(), output=False,
                                              desc='lists lengths'))
        self.add_trait('skip_empty',
                       traits.Bool(
                          False, output=False,
                          desc='remove empty (Undefined, None, empty strings) '
                          'from the output lists'))
        self.input_names = input_names
        self.output_names = output_names
        self.lengths = [0] * len(input_names)

        self.set_callbacks()

        self.lengths = [1] * len(input_names)

    def set_callbacks(self):
        self.on_trait_change(self.resize_callback, 'lengths')
        self.on_trait_change(self.reduce_callback, 'skip_empty')

    def resize_callback(self, obj, name, old_value, value):
        if old_value in (None, traits.Undefined):
            old_value = [0] * len(self.input_names)
        if value in (None, traits.Undefined):
            value = [0] * len(self.input_names)

        # remove former callback
        inputs = []
        for i, pname_p in enumerate(self.input_names):
            inputs += [pname_p % j for j in range(old_value[i])]
        self.on_trait_change(self.reduce_callback, inputs, remove=True)

        # adjust sizes
        for in_index in range(len(value)):
            ptype = self.input_types[in_index]
            pname_p = self.input_names[in_index]
            oval = old_value[in_index]
            val = value[in_index]
            if oval > val:
                for i in range(oval - 1, val - 1, -1):
                    pname = pname_p % i
                    self.remove_trait(pname)
                    if pname in self.plugs:
                        # remove links to this plug
                        plug = self.plugs[pname]
                        to_del = []
                        for link in plug.links_from:
                            linkd = (link[2], link[1], self, pname)
                            to_del.append(linkd)
                        for linkd in to_del:
                            self.pipeline.remove_link(linkd)
                    del self.plugs[pname]
            for i in range(oval, val):
                pname =  pname_p % i
                ptype2 = self._clone_trait(
                    ptype, {'output': False, 'optional': False})
                self.add_trait(pname, ptype2)
                plug = Plug(name=pname, optional=False, output=False)
                self.plugs[pname] = plug
                plug.on_trait_change(
                    self.pipeline.update_nodes_and_plugs_activation, "enabled")
            if oval != val:
                ovalue = [getattr(self, pname_p % i) for i in range(val)]
                if isinstance(ptype,
                              (traits.Str, traits.File, traits.Directory)):
                    # List trait doesn't accept Undefined as items
                    ovalue = [v # if v not in (None, traits.Undefined) else ''
                              for v in ovalue]
                setattr(self, self.output_names[in_index], ovalue)

        # setup new callback
        inputs = []
        for i, pname_p in enumerate(self.input_names):
            inputs += [pname_p % j for j in range(value[i])]
        self.on_trait_change(self.reduce_callback, inputs)

    def reduce_callback(self, obj, name, old_value, value):
        # find out which input pattern is used
        in_index = None
        for index, pname_p in enumerate(self.input_names):
            for i in range(self.lengths[index]):
                pname = pname_p % i
                if name == pname:
                    in_index = index
                    break
            if in_index is not None:
                break
        if in_index is None:
            in_indices = range(len(self.input_names))
        else:
            in_indices = [in_index]
        for in_index in in_indices:
            output = self.output_names[in_index]
            value = [getattr(self, pname_p % i)
                    for i in range(self.lengths[in_index])]
            if self.skip_empty:
                value = [v for v in value
                         if v not in (None, traits.Undefined, '')]
            elif isinstance(self.input_types[in_index],
                          (traits.Str, traits.File, traits.Directory)):
                # List trait doesn't accept Undefined as items
                value = [v # if v not in (None, traits.Undefined) else traits.Undefined
                         for v in value]
            setattr(self, output, value)

    def configured_controller(self):
        c = self.configure_controller()
        c.input_names = self.input_names
        c.output_names = self.output_names
        c.input_types = [(p.trait_type.__class__.__name__ if p.trait_type
                            else p.__class__.__name__)
                         for p in self.input_types]
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('input_types', traits.List(traits.Str))
        c.add_trait('input_names', traits.List(traits.Str))
        c.add_trait('output_names', traits.List(traits.Str))
        c.input_names = ['input_%d']
        c.output_names = ['outputs']
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
            elif ptype not in (None, traits.Undefined, 'None', 'NoneType',
                               '<undefined>'):
                t.append(getattr(traits, ptype)())
        node = ReduceNode(pipeline, name, conf_controller.input_names,
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
        param_dict['lengths'] = self.lengths
        for index, pname_p in enumerate(self.input_names):
            for i in range(self.lengths[index]):
                pname = pname_p % i
                param_dict[pname] = getattr(self, pname)
            output_name = self.output_names[index]
            value = getattr(self, output_name)
            if value not in (None, traits.Undefined):
                param_dict[output_name] = value
        job = MapJob(name=name,
                     referenced_input_files=referenced_input_files,
                     referenced_output_files=referenced_output_files,
                     param_dict=param_dict)
        return job
