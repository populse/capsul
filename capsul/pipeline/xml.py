##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import absolute_import

import xml.etree.cElementTree as ET

from soma.sorted_dictionary import OrderedDict

from capsul.process.xml import string_to_value
from capsul.pipeline.pipeline_construction import PipelineConstructor


def create_xml_pipeline(module, name, xml_file):
    """
    Create a pipeline class given its Capsul XML 2.0 representation.
    
    Parameters
    ----------
    module: str (mandatory)
        name of the module for the created Pipeline class (the Python module is
        not modified).
    name: str (mandatory)
        name of the new pipeline class
    xml_file: str (mandatory)
        name of file containing the XML description.
    
    """
    xml_pipeline = ET.parse(xml_file).getroot()
    version = xml_pipeline.get('capsul_xml')
    if version and version != '2.0':
        raise ValueError('Only Capsul XML 2.0 is supported, not %s' % version)

    builder = PipelineConstructor(module, name)
    exported_parameters = set()
    
    for child in xml_pipeline:
        if child.tag == 'doc':
            builder.set_documentation(child.text.strip())
        elif child.tag == 'process':
            process_name = child.get('name')
            module = child.get('module')
            args = (process_name, module)
            kwargs = {}
            nipype_usedefault = []
            iterate = []
            for process_child in child:
                if process_child.tag == 'set':
                    name = process_child.get('name')
                    value = process_child.get('value')
                    value = string_to_value(value)
                    if value is not None:
                        kwargs[name] = value
                    kwargs.setdefault('make_optional', []).append(name)
                elif process_child.tag == 'iterate':
                    name = process_child.get('name')
                    iterate.append(name)
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
                    raise ValueError('Invalid tag in <process>: %s' %
                                     process_child.tag)
            if iterate:
                kwargs['iterative_plugs'] = iterate
                builder.add_iterative_process(*args, **kwargs)
            else:
                builder.add_process(*args, **kwargs)
            for name in nipype_usedefault:
                builder.call_process_method(process_name, 'set_usedefault',
                                            name, True)
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
            selection_parameter = child.get('name')
            selection_groups = OrderedDict()
            for select_child in child:
                if select_child.tag == 'processes_group':
                    group_name = select_child.get('name')
                    group = selection_groups[group_name] = []
                    for group_child in select_child:
                        if group_child.tag == 'process':
                            group.append(group_child.get('name'))
                        else:
                            raise ValueError('Invalid tag in <processes_group>'
                                             '<process>: %s' % group_child.tag)
                else:
                    raise ValueError('Invalid tag in <processes_selection>: %s'
                                     % select_child.tag)
            builder.add_processes_selection(selection_parameter,
                                            selection_groups)
        elif child.tag == 'gui':
            for gui_child in child:
                if gui_child.tag == 'position':
                    name = gui_child.get('name')
                    x = float(gui_child.get('x'))
                    y = float(gui_child.get('y'))
                    builder.set_node_position(name, x, y)
                elif gui_child.tag == 'zoom':
                    builder.set_scene_scale_factor(
                        float(gui_child.get('level')))
                else:
                    raise ValueError('Invalid tag in <gui>: %s' %
                                     gui_child.tag)
        else:
            raise ValueError('Invalid tag in <pipeline>: %s' % child.tag)
    return builder.pipeline
