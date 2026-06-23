# -*- coding: utf-8 -*-

from capsul.pipeline.pipeline_nodes import Node, Plug
import traits.api as traits
from . import filter_node
import glob
import os
import os.path as osp


class GlobNode(filter_node.FilterNode):
    '''
    This "inert" node builds an output list of file names from a glob
    expression (pattern matching on the filesystem).

    The main ``input`` is the glob expression (ex: ``*/*.nii.gz``). The input
    results may be modified by a filter, and the ``ouputs`` is a list of
    results.

    As in other custom nodes, the input/output link is done when the input is
    set or changed, not as an execution action: this means it works during the
    pipeline definition phase, not during workflow execution. Thus it may be
    used to feed an iteration node.

    ``filter`` is an optional input, which can be used to filter/transform
    results from the glob filesystem search. The filter string is thus supposed
    to contain a python code expression which will be called using the python
    eval() function, for each individual item of the glob search. The itm will
    be available in the ``x`` variable.

    Ex: ``os.path.basename(x).split('.', 1)[0]``
    '''

    _doc_path = 'api/pipeline.html#globnode'

    def __init__(self, pipeline, name, out_type=None):
        '''
        Parameters
        ----------
        pipeline: Pipeline
            pipeline which will hold the node
        name: str
            node name
        out_type: str
            type of indiviidual outputs in the list "outputs". By default it is
            File, but iy may be chnaged to Directory or Str (especially if a
            filter is used)

        '''
        super().__init__(pipeline, name, out_type)
        self.add_trait('input', traits.Str())
        plug = Plug(name='input')
        self.plugs['input'] = plug
        self.on_trait_change(self.update_callback, ['input'])

    def update_callback(self):
        if self.input:
            glob_expr = self.input
            res = glob.glob(glob_expr)
            self.run_filter(res)


class AttributesNode(Node):
    def __init__(self, pipeline, name):
        super().__init__(pipeline, name,
                         [],
                         [{'name': 'param', 'optional': False}])
        self.add_trait('param', traits.Any(output=True, optional=False))
        plug = Plug(name='param', output=True)
        self.plugs['param'] = plug

    def connect(self, source_plug_name, dest_node, dest_plug_name):
        from capsul.attributes.completion_engine import ProcessCompletionEngine

        print('CONNECT:', source_plug_name, dest_node, dest_plug_name)
        super().connect(source_plug_name, dest_node, dest_plug_name)
        process = getattr(dest_node, 'process', None)
        new_plugs = []
        if process is not None:
            ce = ProcessCompletionEngine.get_completion_engine(process)
            if ce is not None:
                att = ce.get_attribute_values()
                for n, t in att.user_traits().items():
                    if self.trait(n) is None:
                        self.add_trait(n, t)
                        setattr(self, n, getattr(att, n))
                        plug = Plug(name=n, output=bool(t.output))
                        self.plugs[n] = plug
                        new_plugs.append(n)
                if new_plugs:
                    self.on_trait_change(self.update_callback, new_plugs)
                to_remove = []
                for n in self.plugs:
                    if n == 'param':
                        continue
                    if att.trait(n) is None:
                        to_remove.append(n)
                for n in to_remove:
                    del self.plugs[n]
                    self.remove_trait(n)

    def disconnect(self, source_plug_name, dest_node, dest_plug_name,
                   silent=False):
        print('DISCONNECT:', source_plug_name, dest_node, dest_plug_name)
        super().disconnect(source_plug_name, dest_node, dest_plug_name, silent)

    def update_callback(self):
        from capsul.attributes.completion_engine import ProcessCompletionEngine

        links = self.plugs['param'].links_to
        print('links;', links)
        for link in links:
            print('link:', link)
            node = link[2]
            process = getattr(node, 'process', node)
            print('proc:', process)
            ce = ProcessCompletionEngine.get_completion_engine(process)
            print('ce:', ce)
            if ce is not None:
                att = ce.get_attribute_values()
                print('atts:', att.export_to_dict())
                for n in self.plugs:
                    if n == 'param':
                        continue
                    if att.trait(n) is not None:
                        print('set att:', n, ';', getattr(self, n))
                        setattr(att, n, getattr(self, n))
                ce.complete_parameters()

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        node = cls(pipeline, name)
        return node
