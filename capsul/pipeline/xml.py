##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import absolute_import

import os
import six
import sys
import xml.etree.cElementTree as ET

from soma.sorted_dictionary import OrderedDict

from capsul.process.xml import string_to_value
from capsul.pipeline.pipeline_construction import PipelineConstructor

from traits.api import Undefined

if sys.version_info[0] >= 3:
    unicode = str


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
        name of file containing the XML description or XML string.
    
    """
    if os.path.exists(xml_file):
        xml_pipeline = ET.parse(xml_file).getroot()
    else:
        xml_pipeline = ET.fromstring(xml_file)
    version = xml_pipeline.get('capsul_xml')
    if version and version != '2.0':
        raise ValueError('Only Capsul XML 2.0 is supported, not %s' % version)

    class_name = xml_pipeline.get('name')
    if class_name:
        if name is None:
            name = class_name
        elif name != class_name:
            raise KeyError('pipeline name (%s) and requested object name '
                           '(%s) differ.' % (class_name, name))
    elif name is None:
        name = os.path.basename(xml_file).rsplit('.', 1)[0]

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
            iteration = child.get('iteration')
            if iteration:
                iterate = [x.strip() for x in iteration.split(',')]
            for process_child in child:
                if process_child.tag == 'set':
                    name = process_child.get('name')
                    value = process_child.get('value')
                    value = string_to_value(value)
                    if value is not None:
                        kwargs[name] = value
                    kwargs.setdefault('make_optional', []).append(name)
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
            enabled = child.get('enabled')
            if enabled == 'false':
                builder.set_node_enabled(process_name, False)
        elif child.tag == 'switch':
            switch_name = child.get('name')
            value = child.get('switch_value')
            kwargs = {'export_switch': False}
            if value:
                kwargs['switch_value'] = value
            inputs = []
            outputs = []
            for process_child in child:
                if process_child.tag == 'input':
                    name = process_child.get('name')
                    inputs.append(name)
                elif process_child.tag == 'output':
                    name = process_child.get('name')
                    outputs.append(name)
                    optional = process_child.get('optional')
                    if optional == 'true':
                        kwargs.setdefault('make_optional', []).append(name)
            builder.add_switch(switch_name, inputs, outputs, **kwargs)
            enabled = child.get('enabled')
            if enabled == 'false':
                builder.set_node_enabled(switch_name, False)
        elif child.tag == 'optional_output_switch':
            switch_name = child.get('name')
            kwargs = {}
            input = None
            output = None
            for process_child in child:
                if process_child.tag == 'input':
                    if input is not None:
                        raise ValueError(
                            'Several inputs in optional_output_switch')
                    input = process_child.get('name')
                elif process_child.tag == 'output':
                    if output is not None:
                        raise ValueError(
                            'Several outputs in optional_output_switch')
                    output = process_child.get('name')
            if input is None:
                raise ValueError('No input in optional_output_switch')
            builder.add_optional_output_switch(switch_name, input, output)
            enabled = child.get('enabled')
            if enabled == 'false':
                builder.set_node_enabled(switch_name, False)
        elif child.tag == 'link':
            source = child.get('source')
            dest = child.get('dest')
            weak_link = child.get('weak_link')
            if weak_link == 'true':
                weak_link = True
            else:
                weak_link = False
            if '.' in source:
                if '.' in dest:
                    builder.add_link('%s->%s' % (source, dest),
                                     weak_link=weak_link)
                elif dest in exported_parameters:
                    builder.add_link('%s->%s' % (source, dest),
                                     weak_link=weak_link)
                else:
                    node, plug = source.rsplit('.', 1)
                    builder.export_parameter(node, plug, dest,
                                             weak_link=weak_link)
                    exported_parameters.add(dest)
            elif source in exported_parameters:
                builder.add_link('%s->%s' % (source, dest))
            else:
                node, plug = dest.rsplit('.', 1)
                builder.export_parameter(node, plug, source,
                                         weak_link=weak_link)
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
        elif child.tag == 'pipeline_steps':
            for step_child in child:
                step_name = step_child.get('name')
                enabled = step_child.get('enabled')
                if enabled == 'false':
                    enabled = False
                else:
                    enabled = True
                nodes = []
                for step_node in step_child:
                    nodes.append(step_node.get('name'))
                builder.add_pipeline_step(step_name, nodes, enabled)
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


def save_xml_pipeline(pipeline, xml_file):
    '''
    Save a pipeline in an XML file

    Parameters
    ----------
    pipeline: Pipeline instance
        pipeline to save
    xml_file: str
        XML file to save the pipeline in
    '''
    # imports are done locally to avoid circular imports
    from capsul.api import Process, Pipeline
    from capsul.pipeline.pipeline_nodes import ProcessNode, Switch, \
        OptionalOutputSwitch
    from capsul.pipeline.process_iteration import ProcessIteration
    from capsul.process.process import NipypeProcess

    def _write_process(process, parent, name):
        procnode = ET.SubElement(parent, 'process')
        mod = process.__module__
        # if process is a function with XML decorator, we need to
        # retreive the original function name.
        func = getattr(process, '_function', None)
        if func:
            classname = func.__name__
        else:
            classname = process.__class__.__name__
        procnode.set('module', "%s.%s" % (mod, classname))
        procnode.set('name', name)
        if isinstance(process, NipypeProcess):
            # WARNING: not sure I'm doing the right things for nipype. To be
            # fixed if needed.
            for param in process.inputs_to_copy:
                elem = ET.SubElement(procnode, 'nipype')
                elem.set('name', param)
                if param in proces.inputs_to_clean:
                    elem.set('copyfile', 'discard')
                else:
                    elem.set('copyfile', 'true')
                np_input = getattr(process._nipype_interface.inputs, param)
                if np_input:
                    use_default = getattr(np_input, 'usedefault', False) # is it that?
                    if use_default:
                        elem.set('use_default', 'true')
            for param, np_input in \
                    six.iteritems(process._nipype_interface.inputs.__dict__):
                use_default = getattr(np_input, 'usedefault', False) # is it that?
                if use_default and param not in process.inputs_to_copy:
                    elem = ET.SubElement(procnode, 'nipype')
                    elem.set('name', param)
                    elem.set('use_default', 'true')
        # set initial values
        for param_name, trait in six.iteritems(process.user_traits()):
            if param_name not in ('nodes_activation', 'selection_changed'):
                value = getattr(process, param_name)
                if value not in (None, Undefined, '', []):
                    value = repr(value)
                    elem = ET.SubElement(procnode, 'set')
                    elem.set('name', param_name)
                    elem.set('value', value)
        return procnode

    def _write_iteration(process_iter, parent, name):
        procnode = _write_process(process_iter.process, parent, name)
        iteration_params = ', '.join(process_iter.iterative_parameters)
        procnode.set('iteration', iteration_params)
        return procnode

    def _write_switch(switch, parent, name):
        swnode = ET.SubElement(parent, 'switch')
        swnode.set('name', name)
        inputs = set()
        for plug_name, plug in six.iteritems(switch.plugs):
            if plug.output:
                elem = ET.SubElement(swnode, 'output')
                elem.set('name', plug_name)
                if plug.optional:
                    elem.set('optional', 'true')
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 \
                        and name_parts[0] not in inputs:
                    inputs.add(name_parts[0])
                    elem = ET.SubElement(swnode, 'input')
                    elem.set('name', name_parts[0])
                    if plug.optional:
                        elem.set('optional', 'true')
        swnode.set('switch_value', unicode(switch.switch))
        return swnode

    def _write_optional_output_switch(switch, parent, name):
        swnode = ET.SubElement(parent, 'optional_output_switch')
        swnode.set('name', name)
        for plug_name, plug in six.iteritems(switch.plugs):
            if plug.output:
                elem = ET.SubElement(swnode, 'output')
                elem.set('name', plug_name)
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2:
                    input = name_parts[0]
                    if input != '_none':
                        elem = ET.SubElement(swnode, 'input')
                        elem.set('name', name_parts[0])
                        if plug.optional:
                            elem.set('optional', 'true')
        return swnode

    def _write_processes(pipeline, root):
        for node_name, node in six.iteritems(pipeline.nodes):
            if node_name == "":
                continue
            if isinstance(node, OptionalOutputSwitch):
                xmlnode = _write_optional_output_switch(node, root, node_name)
            elif isinstance(node, Switch):
                xmlnode = _write_switch(node, root, node_name)
            elif isinstance(node, ProcessNode) \
                    and isinstance(node.process, ProcessIteration):
                xmlnode = _write_iteration(node.process, root, node_name)
            else:
                xmlnode = _write_process(node.process, root, node_name)
            if not node.enabled:
                xmlnode.set('enabled', 'false')

    def _write_processes_selections(pipeline, root):
        selection_parameters = []
        if hasattr(pipeline, 'processes_selection'):
            for selector_name, groups \
                    in six.iteritems(pipeline.processes_selection):
                selection_parameters.append(selector_name)
                sel_node = ET.SubElement(root, 'processes_selection')
                sel_node.set('name', selector_name)
                for group_name, group in six.iteritems(groups):
                    grp_node = ET.SubElement(sel_node, 'processes_group')
                    grp_node.set('name', group_name)
                    for node in group:
                        proc_node = ET.SubElement(grp_node, 'process')
                        proc_node.set('name', node)
        return selection_parameters

    def _write_links(pipeline, root):
        for node_name, node in six.iteritems(pipeline.nodes):
            for plug_name, plug in six.iteritems(node.plugs):
                if (node_name == "" and not plug.output) \
                        or (node_name != "" and plug.output):
                    links = plug.links_to
                    for link in links:
                        if node_name == "":
                            src = plug_name
                        else:
                            src = "%s.%s" % (node_name, plug_name)
                        if link[0] == "":
                            dst = link[1]
                        else:
                            dst = "%s.%s" % (link[0], link[1])
                        linkelem = ET.SubElement(root, 'link')
                        linkelem.set('source', src)
                        linkelem.set('dest', dst)
                        if link[-1]:
                            linkelem.set('weak_link', "true")

    def _write_steps(pipeline, root):
        steps = pipeline.trait('pipeline_steps')
        steps_node = None
        if steps and getattr(pipeline, 'pipeline_steps', None):
            steps_node = ET.SubElement(root, 'pipeline_steps')
            for step_name, step \
                    in six.iteritems(pipeline.pipeline_steps.user_traits()):
                step_node = ET.SubElement(steps_node, 'step')
                step_node.set('name', step_name)
                enabled = getattr(pipeline.pipeline_steps, step_name)
                if not enabled:
                    step_node.set('enabled', 'false')
                nodes = step.nodes
                for node in nodes:
                    node_item = ET.SubElement(step_node, 'node')
                    node_item.set('name', node)
        return steps_node

    def _write_nodes_positions(pipeline, root):
        gui = None
        if hasattr(pipeline, "node_position") and pipeline.node_position:
            gui = ET.SubElement(root, 'gui')
            for node_name, pos in six.iteritems(pipeline.node_position):
                node_pos = ET.SubElement(gui, 'position')
                node_pos.set('name', node_name)
                node_pos.set('x', unicode(pos[0]))
                node_pos.set('y', unicode(pos[1]))
        return gui

    def _write_doc(pipeline, root):
        if hasattr(pipeline, "__doc__"):
            docstr = pipeline.__doc__
            if docstr == Pipeline.__doc__:
                docstr = ""  # don't use the builtin Pipeline help
            else:
                # remove automatically added doc
                splitdoc = docstr.split('\n')
                notepos = [i for i, x in enumerate(splitdoc[:-2])
                              if x.endswith('.. note::')]
                autodocpos = None
                if notepos:
                    for i in notepos:
                        if splitdoc[i+2].find(
                                "* Type '{0}.help()'".format(
                                    pipeline.__class__.__name__)) != -1:
                            autodocpos = i
                if autodocpos is not None:
                    # strip empty trailing lines
                    while autodocpos >= 1 \
                            and splitdoc[autodocpos - 1].strip() == '':
                        autodocpos -= 1
                    docstr = '\n'.join(splitdoc[:autodocpos]) + '\n'
        else:
            docstr = ''
        if docstr.strip() == '':
            docstr = ''
        doc = ET.SubElement(root, 'doc')
        doc.text = docstr
        return doc

    root = ET.Element('pipeline')
    root.set('capsul_xml', '2.0')
    class_name = pipeline.__class__.__name__
    if pipeline.__class__ is Pipeline:
        # if directly a Pipeline, then use a default new name
        class_name = 'CustomPipeline'
    root.set('name', class_name)

    _write_doc(pipeline, root)
    _write_processes(pipeline, root)
    _write_links(pipeline, root)
    _write_processes_selections(pipeline, root)
    _write_steps(pipeline, root)
    gui_node = _write_nodes_positions(pipeline, root)

    if hasattr(pipeline, "scene_scale_factor"):
        if gui_node is None:
            gui_node = ET.SubElement(root, 'gui')
        scale_node = ET.SubElement(gui_node, 'zoom')
        scale_node.set('level', unicode(pipeline.scene_scale_factor))

    tree = ET.ElementTree(root)
    tree.write(xml_file)

