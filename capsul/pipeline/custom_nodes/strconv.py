# -*- coding: utf-8 -*-
'''
:class:`StrConvNode`
--------------------------------
'''

from __future__ import print_function
from __future__ import absolute_import
from capsul.pipeline.pipeline_nodes import Node
from soma.controller import Controller
import traits.api as traits
import six
import sys


class StrConvNode(Node):
    '''
    This "inert" node converts the input into a string.

    '''

    _doc_path = 'api/pipeline.html#strconvnode'

    def __init__(self, pipeline, name, input_type=None):
        in_traitsl = ['input']
        out_traitsl = ['output']
        in_traits = []
        out_traits = []
        for tr in in_traitsl:
            in_traits.append({'name': tr, 'optional': True})
        for tr in out_traitsl:
            out_traits.append({'name': tr, 'optional': True})
        super(StrConvNode, self).__init__(
            pipeline, name, in_traits, out_traits)
        if input_type:
            ptype = input_type
        else:
            ptype = traits.Any(traits.Undefined)

        self.add_trait('input', ptype)
        self.trait('input').output = False
        is_output = True  # not a choice for now.
        self.add_trait('output', traits.Str(output=is_output))
        self.input = 0
        self.filter_callback('input', 0)

        self.set_callbacks()

    def set_callbacks(self, update_callback=None):
        inputs = ['input']
        if update_callback is None:
            update_callback = self.filter_callback
        for name in inputs:
            self.on_trait_change(update_callback, name)

    def filter_callback(self, name, value):
        self.output = six.text_type(self.input)

    def configured_controller(self):
        c = self.configure_controller()
        c.param_type = self.trait('input').trait_type.__class__.__name__
        return c

    @classmethod
    def configure_controller(cls):
        c = Controller()
        c.add_trait('param_type', traits.Str('Any'))
        return c

    @classmethod
    def build_node(cls, pipeline, name, conf_controller):
        t = None
        if conf_controller.param_type == 'Str':
            t = traits.Str(traits.Undefined)
        elif conf_controller.param_type == 'File':
            t = traits.File(traits.Undefined)
        elif conf_controller.param_type == 'Any':
            t = traits.Any()
        elif conf_controller.param_type not in (None, traits.Undefined):
            t = getattr(traits, conf_controller.param_type)()
        node = StrConvNode(pipeline, name, input_type=t)
        return node

    def is_job(self):
        return False

    def get_connections_through(self, plug_name, single=False):
        if not self.activated or not self.enabled:
            return []
        plug = self.plugs[plug_name]
        if plug.output:
            connected_plug_name = 'input'
        else:
            connected_plug_name = 'output'
        connected_plug = self.plugs[connected_plug_name]
        if plug.output:
            links = connected_plug.links_from
        else:
            links = connected_plug.links_to
        dest_plugs = []
        for link in links:
            if link[2] is self.pipeline.pipeline_node:
                other_end = [(link[2], link[1], link[3])]
            else:
                other_end = link[2].get_connections_through(link[1], single)
            dest_plugs += other_end
            if other_end and single:
                break
        return dest_plugs
