##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import absolute_import

import xml.etree.cElementTree as ET
from ast import literal_eval

from capsul.pipeline.pipeline import Pipeline

from traits.api import Undefined, Directory

_known_values = {
    'Undefined': Undefined,
}
    
def string_to_value(string):
    value = _known_values.get(string)
    if value is None:
        try:
            value = literal_eval(string)
        except ValueError as e:
            raise ValueError('%s: %s' % (str(e), repr(string)))
    return value

class PipelineBuilder(object):
    class RegisterMethod(object):
        def __init__(self, methods, method_name):
            self.methods = methods
            self.method_name = method_name
        
        def __call__(self, *args, **kwargs):
            self.methods.append((self.method_name, args, kwargs))
    
    def __init__(self, pipeline):
        self.methods = pipeline.pipeline_definition_methods
        
    def __getattr__(self, name):
        return self.RegisterMethod(self.methods, name)

        
class DynamicPipeline(Pipeline):
    def pipeline_definition(self):
        for method_name, args, kwargs in self.pipeline_definition_methods:
            try:
                method = getattr(self, method_name)
                method(*args, **kwargs)
            except Exception as e:
                l = [repr(i) for i in args]
                l.extend('%s=%s' % (k, repr(v)) for k, v in kwargs.items())
                m = '%s(%s)' % (method_name, ', '.join(l))
                raise e.__class__('%s (in pipeline %s when calling %s)' % (e.message, self.id, m))
            

def create_xml_pipeline(module, name, xml_file):
    xml_pipeline = ET.parse(xml_file).getroot()
    version = xml_pipeline.get('capsul_xml')
    if version and version != '2.0':
        raise ValueError('Only Capsul XML 2.0 is supported, not %s' % version)

    class_kwargs = {
        '__module__': module,
        'pipeline_definition_methods': [],
        'autoexport_nodes_parameters': False,
        'output_directory': Directory(Undefined, exists=True,
                                      optional=True),
    }
    pipeline = type(name, (DynamicPipeline,), class_kwargs)
    builder = PipelineBuilder(pipeline)
    exported_parameters = set()
    
    for child in xml_pipeline:
        if child.tag == 'doc':
            pipeline.__doc__ = child.text.strip()
        elif child.tag == 'process':
            process_name = child.get('name')
            module = child.get('module')
            args = (process_name, module)
            kwargs = {}
            nipype_usedefault = []
            for process_child in child:
                if process_child.tag == 'set':
                    name = process_child.get('name')
                    value = process_child.get('value')
                    value = string_to_value(value)
                    if value is not None:
                        kwargs[name] = value
                    kwargs.setdefault('make_optional',[]).append(name)
                elif process_child.tag == 'nipype':
                    name = process_child.get('name')
                    usedefault = process_child.get('usedefault')
                    if usedefault == 'true':
                        nipype_usedefault.append(name)
                    copyfile = process_child.get('copyfile')
                    if copyfile == 'true':
                        kwargs.setdefault('inputs_to_copy', []).append(name)
                    elif copyfile == 'discard':
                        kwargs.setdefault('inputs_to_copy', []).append(name)
                        kwargs.setdefault('inputs_to_clean', []).append(name)
                else:
                    raise ValueError('Invalid tag in <process>: %s' % process_child.tag)
            builder.add_process(*args, **kwargs)
            for name in nipype_usedefault:
                builder.call_process_method(process_name, 'set_usedefault', name, True)
        elif child.tag == 'link':
            source = child.get('source')
            dest = child.get('dest')
            if '.' in source:
                if '.' in dest:
                    builder.add_link('%s->%s' % (source, dest))
                elif dest in exported_parameters:
                    builder.add_link('%s->%s' % (source, dest))
                else:
                    node, plug = source.rsplit('.', 1)
                    builder.export_parameter(node, plug, dest)
                    exported_parameters.add(dest)
            elif source in exported_parameters:
                builder.add_link('%s->%s' % (source, dest))
            else:
                node, plug = dest.rsplit('.', 1)
                builder.export_parameter(node, plug, source)
                exported_parameters.add(source)
        elif child.tag == 'processes_selection':
            pass #TODO
        elif child.tag == 'gui':
            pipeline.node_position = {}
            for gui_child in child:
                if gui_child.tag == 'position':
                    name = gui_child.get('process')
                    x = float(gui_child.get('x'))
                    y = float(gui_child.get('y'))
                    pipeline.node_position[name] = (x,y)
                elif gui_child.tag == 'zoom':
                    pipeline.scene_scale_factor = \
                        float(gui_child.get('level'))
                else:
                    raise ValueError('Invalid tag in <gui>: %s' % gui_child.tag)
        else:
            raise ValueError('Invalid tag in <pipeline>: %s' % child.tag)
    return pipeline
    
