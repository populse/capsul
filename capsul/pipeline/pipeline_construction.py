# -*- coding: utf-8 -*-
'''
This module is an internal machinery, the user needs not to know it and bother about it. In brief it provide helper functions to build a pipeline from an IO serialization.

Classes
=======
:class:`PipelineConstructor`
----------------------------
:class:`ConstructedPipeline`
----------------------------
'''

from __future__ import absolute_import

import xml.etree.cElementTree as ET

from capsul.pipeline.pipeline import Pipeline
from capsul.process.xml import string_to_value
from capsul.process.process import ProcessMeta

from traits.api import Undefined, Directory


class PipelineConstructor(object):
    """
    A PipelineConstructor is used to build a new Pipeline class and dynamically
    constructs its contents, for instances by adding processes nodes and
    creating links between parameters. This class must be used whenever one
    wants to create a pipeline from an external source (i.e. a source that is
    not an installed Python module). For instance, the creation of a pipeline
    from an XML representation uses a PipelineConstructor.
    
    Attributes
    ----------
    `pipeline`: ConstructedPipeline derived class
        the constructed Pipeline class
    """
    
    def __init__(self, module, name):
        """
        Initialize a new empty ConstructedPipeline class that is ready to be
        customized by calling methods of the PipelineConstructor. When pipeline
        creation is done, the pipeline class can be accessed with the
        `pipeline` attribute.
        
        Parameters
        ----------
        module: str (mandatory)
            name of the module for the created Pipeline class.
        name: str (mandatory)
            name of the created Pipeline class.
        """
        class_kwargs = {
            '__module__': module,
            '_pipeline_definition_calls': [],
            'do_autoexport_nodes_parameters': False,
            'node_position': {}
        }
        self.pipeline = type(name, (ConstructedPipeline,), class_kwargs)
        # self.__calls is simply a shortcut to 
        # self.pipeline._pipeline_definition_calls
        self._calls = self.pipeline._pipeline_definition_calls
    

    def add_process(self, *args, **kwargs):
        """Adds a new process to the pipeline.
        """
        self._calls.append(('add_process', args, kwargs))
    
    
    def add_iterative_process(self, *args, **kwargs):
        """Adds a new iterative process to the pipeline.
        """
        self._calls.append(('add_iterative_process', args, kwargs))
    
    
    def call_process_method(self, *args, **kwargs):
        """ Call a method of a process previously added
        with add_process or add_itConstructedPipelineerative_process.
        """
        self._calls.append(('call_process_method', args, kwargs))

        
    def add_link(self, *args, **kwargs):
        """Add a link between pipeline processes.
        """
        self._calls.append(('add_link', args, kwargs))

    def add_subpipeline_link(self, *args, **kwargs):
        """Add a link between subpipeline processes.
        """
        self._calls.append(('add_subpipeline_link', args, kwargs))

    def export_parameter(self, *args, **kwargs):
        """Export an internal parameter to the pipeline parameters.
        """
        self._calls.append(('export_parameter', args, kwargs))


    def add_processes_selection(self, *args, **kwargs):
        """ Add processes selection to the pipeline.
        """
        self._calls.append(('add_processes_selection', args, kwargs))


    def set_documentation(self, doc):
        """ Sets the documentation of the pipeline
        """
        # Get and complement the process docstring
        docstring = ProcessMeta.complement_doc(
            self.pipeline.__class__.__name__, doc)
        self.pipeline.__doc__ = docstring


    def set_node_position(self, node_name, x, y):
        """ Set a pipeline node position.
        """
        self.pipeline.node_position[node_name] = (x, y)
    
    
    def set_scene_scale_factor(self, scale):
        """ Set global nodes view scale factor.
        """
        self.pipeline.scene_scale_factor = scale

    def add_switch(self, *args, **kwargs):
        """ Adds a switch to the pipeline
        """
        self._calls.append(('add_switch', args, kwargs))

    def add_optional_output_switch(self, *args, **kwargs):
        """ Adds an OptionalOutputswitch to the pipeline
        """
        self._calls.append(('add_optional_output_switch', args, kwargs))

    def add_custom_node(self, *args, **kwargs):
        """ Adds an custom Node subtype to the pipeline
        """
        self._calls.append(('add_custom_node', args, kwargs))


    def set_node_enabled(self, name, state):
        """ Enables or disabled a node
        """
        self._calls.append(('_set_node_enabled', (name, state), {}))

    def add_pipeline_step(self, step_name, nodes, enabled):
        """ Defines a pipeline step
        """
        self._calls.append(('add_pipeline_step', (step_name, nodes, enabled),
                            {}))

    def add_node_state(self, node_name, key, value):
        self._calls.append(('add_node_state', (node_name, key, value), {}))

    def add_plug_state(self, plug_name, key, value):
        self._calls.append(('add_plug_state', (plug_name, key, value), {}))

    def set_plug_value(self, node_name, plug_name, value):
        self._calls.append(('set_plug_value', (node_name, plug_name, value),
                            {}))

    def set_export_parameters(self, value):
        self._calls.append(('set_export_parameters', (value, ), {}))


class ConstructedPipeline(Pipeline):
    """
    Base class of all pipelines created with PipelineConstructor. It redefines
    pipeline_definition in order to "replay", at each instantiation, the method
    calls previously recorded with the PipelineConstructor.
    """
    def pipeline_definition(self):
        """
        Executes on `self`, all method calls recorded in 
        self._pipeline_definition_calls.
        """
        for method_name, args, kwargs in self._pipeline_definition_calls:
            try:
                method = getattr(self, method_name)
                method(*args, **kwargs)
            except Exception as e:
                l = [repr(i) for i in args]
                l.extend('%s=%s' % (k, repr(v)) for k, v in kwargs.items())
                m = '%s(%s)' % (method_name, ', '.join(l))
                raise RuntimeError('%s: %s (in pipeline %s when calling %s)' %
                                   (e.__class__.__name__, str(e), self.id, m))

    def add_subpipeline_link(self, node_def, source, dest, **kwargs):
        from capsul.pipeline.process_iteration import ProcessIteration

        nodes = node_def.split('.')
        proc = self
        for node in nodes:
            proc = proc.nodes[node].process
            if isinstance(proc, ProcessIteration):
                proc = proc.process
        proc.add_link('%s->%s' % (source, dest), allow_export=True, **kwargs)

    def add_node_state(self, node_name, key, value):
        node_list = node_name.split('.')
        parent = self.pipeline_node
        for name in node_list:
            parent = parent.process.nodes[name]
        if key in ('enabled', ):
            value = bool(int(value))
        setattr(parent, key, value)

    def add_plug_state(self, param_name, key, value):
        node_list = param_name.split('.')
        pname = node_list[-1]
        node_list.pop(-1)
        parent = self.pipeline_node
        for name in node_list:
            parent = parent.process.nodes[name]
        if key in ('optional', 'output', 'intput_filename', ):
            value = bool(int(value))
        setattr(parent.get_trait(pname), key, value)
        setattr(parent.plugs[pname], key, value)

    def set_plug_value(self, node_name, param_name, value):
        node_list = node_name.split('.')
        if node_list == ['']:
            node_list = []
        parent = self.pipeline_node
        for name in node_list:
            parent = parent.process.nodes[name]
        parent.set_plug_value(param_name, value)

    def set_export_parameters(self, value):
        self.do_autoexport_nodes_parameters = value
