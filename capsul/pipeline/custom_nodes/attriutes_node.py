# -*- coding: utf-8 -*-

from capsul.pipeline.pipeline_nodes import Node, Plug
import traits.api as traits
from soma.utils.weak_proxy import get_ref


class AttributesNode(Node):
    ''' Thsi special node allows to input completion attributes for a given
    process.

    Use it this way:

    - instantiate an AttributesNoes
    - connect its "param" plug to an input parameter of a process which has a
      completion system (FOM for instance). The completion attributes of the
      linked process will then be exposed as inputs in the AttributesNode.
    - whenever an attribute value changes on the node, then the completion
      system of the linked processs is triggered with the updated attribute
        values.

    It is possible to link attributes to upstream nodes which will provide
    attribute values, like GlobNode or CSVFilterNode, and this is especially
    useful when the linked process is an iterative node: then attributes lists
    will be provided to the iteration. This is a way to automate iteration from
    a CSV file (for instance a BIDS ``participants.tsv`` file).

    Always keep in mind that this node (as most custom nodes) will run at
    pipeline parameters assignation time, not at pipeline (workflow) run time.
    '''

    def __init__(self, pipeline, name):
        super().__init__(pipeline, name,
                         [],
                         [{'name': 'param', 'optional': False}])
        self.add_trait('param', traits.Any(output=True, optional=False))
        plug = Plug(name='param', output=True)
        self.plugs['param'] = plug

    def connect(self, source_plug_name, dest_node, dest_plug_name):
        from capsul.attributes.completion_engine import ProcessCompletionEngine

        super().connect(source_plug_name, dest_node, dest_plug_name)
        process = getattr(dest_node, 'process', None)
        new_plugs = []
        if process is not None:
            ce = ProcessCompletionEngine.get_completion_engine(process)
            if ce is not None:
                att = ce.get_attribute_values()
                for n, t in att.user_traits().items():
                    if self.trait(n) is None:
                        t2 = att._clone_trait(t)
                        t2.optional = True
                        self.add_trait(n, t2)
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
        # print('DISCONNECT:', source_plug_name, dest_node, dest_plug_name)
        super().disconnect(source_plug_name, dest_node, dest_plug_name, silent)

    def update_callback(self):
        from capsul.attributes.completion_engine import ProcessCompletionEngine

        links = self.plugs['param'].links_to
        done_nodes = set()
        for link in links:
            node = link[2]
            process = get_ref(getattr(node, 'process', node))
            if process in done_nodes:
                continue
            done_nodes.add(process)
            ce = ProcessCompletionEngine.get_completion_engine(process)
            if ce is not None:
                att = ce.get_attribute_values()
                for n in self.plugs:
                    if n == 'param':
                        continue
                    if att.trait(n) is not None:
                        setattr(att, n, getattr(self, n))
                ce.complete_parameters()

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        node = cls(pipeline, name)
        return node
