##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function
from __future__ import absolute_import

import os
import six
import sys


def save_py_pipeline(pipeline, py_file):
    '''
    Save a pipeline in an Python source file

    Parameters
    ----------
    pipeline: Pipeline instance
        pipeline to save
    py_file: str
        .py file to save the pipeline in
    '''
    # imports are done locally to avoid circular imports
    from capsul.api import Process, Pipeline
    from capsul.pipeline.pipeline_nodes import ProcessNode, Switch, \
        OptionalOutputSwitch
    from capsul.pipeline.process_iteration import ProcessIteration
    from capsul.process.process import NipypeProcess
    from traits.api import Undefined

    def _write_process(process, pyf, name, enabled):
        mod = process.__module__
        # if process is a function with XML decorator, we need to
        # retreive the original function name.
        func = getattr(process, '_function', None)
        if func:
            classname = func.__name__
        else:
            classname = process.__class__.__name__
        procname = '.'.join((mod, classname))
        print('        self.add_process("%s", "%s")' % (name, procname),
              file=pyf)
        #if isinstance(process, NipypeProcess):
            ## WARNING: not sure I'm doing the right things for nipype. To be
            ## fixed if needed.
            #for param in process.inputs_to_copy:
                #elem = ET.SubElement(procnode, 'nipype')
                #elem.set('name', param)
                #if param in proces.inputs_to_clean:
                    #elem.set('copyfile', 'discard')
                #else:
                    #elem.set('copyfile', 'true')
                #np_input = getattr(process._nipype_interface.inputs, param)
                #if np_input:
                    #use_default = getattr(np_input, 'usedefault', False) # is it that?
                    #if use_default:
                        #elem.set('use_default', 'true')
            #for param, np_input in \
                    #six.iteritems(process._nipype_interface.inputs.__dict__):
                #use_default = getattr(np_input, 'usedefault', False) # is it that?
                #if use_default and param not in process.inputs_to_copy:
                    #elem = ET.SubElement(procnode, 'nipype')
                    #elem.set('name', param)
                    #elem.set('use_default', 'true')

    def _write_iteration(process_iter, pyf, name, enabled):
        process = process_iter.process
        mod = process.__module__
        # if process is a function with XML decorator, we need to
        # retreive the original function name.
        func = getattr(process, '_function', None)
        if func:
            classname = func.__name__
        else:
            classname = process.__class__.__name__
        procname = '.'.join((mod, classname))

        iteration_params = ', '.join(process_iter.iterative_parameters)
        # TODO: optional plugs, non-exported plugs...
        print('        self.add_iterative_process("%s", "%s", '
              'iterative_plugs=%s)'
              % (name, procname, process_iter.iterative_parameters),
              file=pyf)

    def _write_switch(switch, pyf, name, enabled):
        inputs = set()
        outputs = []
        optional = []
        opt_in = []
        for plug_name, plug in six.iteritems(switch.plugs):
            if plug.output:
                outputs.append(plug_name)
                if plug.optional:
                    optional.append(plug_name)
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 \
                        and name_parts[0] not in inputs:
                    inputs.add(name_parts[0])
                    if plug.optional:
                        opt_in.append(name_parts[0])
        optional_p = ''
        if len(optional) != 0:
            optional_p = ', make_optional=%s' % repr(optional)
        value_p = ''
        inputs = list(inputs)
        if switch.switch != inputs[0]:
            value_p = ', switch_value=%s' % repr(switch.switch)
        print('        self.add_switch("%s", %s, %s%s%s, export_switch=False)'
              % (name, repr(inputs), repr(outputs), optional_p, value_p),
              file=pyf)

    def _write_optional_output_switch(switch, pyf, name, enabled):
        output = None
        input = None
        for plug_name, plug in six.iteritems(switch.plugs):
            if plug.output:
                output = plug_name
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 and name_parts[0] != '_none':
                    input = name_parts[0]
        if not name and output:
            name = output
        if not output or output == name:
            print('        self.add_optional_output_switch("%s", "%s")'
                  % (name, input), file=pyf)
        else:
            print('        self.add_optional_output_switch("%s", "%s", "%s")'
                  % (name, input, output), file=pyf)

    def _write_processes(pipeline, pyf):
        print('        # nodes', file=pyf)
        for node_name, node in six.iteritems(pipeline.nodes):
            if node_name == "":
                continue
            if isinstance(node, OptionalOutputSwitch):
                _write_optional_output_switch(node, pyf, node_name,
                                              node.enabled)
            elif isinstance(node, Switch):
                _write_switch(node, pyf, node_name, node.enabled)
            elif isinstance(node, ProcessNode) \
                    and isinstance(node.process, ProcessIteration):
                _write_iteration(node.process, pyf, node_name, node.enabled)
            else:
                _write_process(node.process, pyf, node_name, node.enabled)

    def _write_processes_selections(pipeline, pyf):
        selection_parameters = []
        if hasattr(pipeline, 'processes_selection'):
            print('\n        # processes selection', file=pyf)
            for selector_name, groups \
                    in six.iteritems(pipeline.processes_selection):
                print('        self.add_processes_selection("%s", %s)'
                      % (selector_name, repr(groups)), file=pyf)
        return selection_parameters

    def _write_export(pipeline, pyf, param_name):
        plug = pipeline.pipeline_node.plugs[param_name]
        if plug.output:
            link = list(plug.links_from)[0]
        else:
            link = list(plug.links_to)[0]
        node_name, plug_name = link[:2]
        if param_name == plug_name:
            param_name = ''
        else:
            param_name = ', "%s"' % param_name
        weak_link = ''
        if link[-1]:
            weak_link = ', weak_link=True'
        print('        self.export_parameter("%s", "%s"%s%s)'
              % (node_name, plug_name, param_name, weak_link), file=pyf)
        return node_name, plug_name

    def _write_links(pipeline, pyf):
        exported = set()
        print('\n        # links', file=pyf)
        for node_name, node in six.iteritems(pipeline.nodes):
            for plug_name, plug in six.iteritems(node.plugs):
                if (node_name == "" and not plug.output) \
                        or (node_name != "" and plug.output):
                    links = plug.links_to
                    for link in links:
                        exported_plug = None
                        if node_name == "":
                            src = plug_name
                            if src not in exported:
                                exported_plug = _write_export(pipeline, pyf,
                                                              src)
                                exported.add(src)
                        else:
                            src = "%s.%s" % (node_name, plug_name)
                        if link[0] == "":
                            dst = link[1]
                            if dst not in exported:
                                exported_plug = _write_export(pipeline, pyf,
                                                              dst)
                                exported.add(dst)
                        else:
                            dst = "%s.%s" % (link[0], link[1])
                        if not exported_plug \
                                or '.'.join(exported_plug) not in (src, dst):
                            weak_link = ''
                            if link[-1]:
                                weak_link = ', weak_link=True'
                            print('        self.add_link("%s->%s"%s)'
                                  % (src, dst, weak_link), file=pyf)

    def _write_steps(pipeline, pyf):
        steps = pipeline.trait('pipeline_steps')
        if steps and getattr(pipeline, 'pipeline_steps', None):
            print('\n        # pipeline steps', file=pyf)
            for step_name, step \
                    in six.iteritems(pipeline.pipeline_steps.user_traits()):
                enabled = getattr(pipeline.pipeline_steps, step_name)
                if not enabled:
                    step_node.set('enabled', 'false')
                nodes = step.nodes
                print('        self.add_pipeline_step("%s", %s)'
                      % (step_name, repr(nodes)), file=pyf)

    def _write_nodes_positions(pipeline, pyf):
        node_position = getattr(pipeline, "node_position", None)
        if node_position:
            print('\n        # nodes positions', file=pyf)
            print('        self.node_position = {', file=pyf)
            for node_name, pos in six.iteritems(pipeline.node_position):
                if not isinstance(pos, (list, tuple)):
                    # pos is probably a QPointF
                    pos = (pos.x(), pos.y())
                print('            "%s": %s,' % (node_name, repr(pos)),
                      file=pyf)
            print('        }', file=pyf)
        if hasattr(pipeline, "scene_scale_factor"):
            print('        self.scene_scale_factor = %s'
                  % repr(pipeline.scene_scale_factor), file=pyf)

    def _write_doc(pipeline, pyf):
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
            if docstr.strip() == '':
                docstr = ''
            if docstr:
                doc = docstr.split('\n')
                docstr = '\n'.join([repr(x)[1:-1] for x in doc])
                print('    \"\"\"%s    \"\"\"' % docstr, file=pyf)

    def _write_values(pipeline, pyf):
        first = True
        for param_name, trait in six.iteritems(pipeline.user_traits()):
            if param_name not in pipeline.pipeline_node.plugs:
                continue
            # default cannot be set after trait creation
            #if trait.default:
                #if first:
                    #first = False
                    #print('\n        # default and initial values', file=pyf)
                #print('        self.trait("%s").default = %s'
                      #% (param_name, repr(trait.default)), file=pyf)
            value = getattr(pipeline, param_name)
            if value != trait.default and value not in (None, '', Undefined):
                if first:
                    first = False
                    print('\n        # default and initial values', file=pyf)
                print('        self.%s = %s'
                      % (param_name, repr(value)), file=pyf)

    class_name = type(pipeline).__name__

    pyf = open(py_file, 'w')

    print('from capsul.api import Pipeline', file=pyf)
    print(file=pyf)
    print(file=pyf)
    print('class %s(Pipeline):' % class_name, file=pyf)

    _write_doc(pipeline, pyf)

    print(file=pyf)
    print('    def pipeline_definition(self):', file=pyf)

    _write_processes(pipeline, pyf)
    _write_links(pipeline, pyf)
    _write_processes_selections(pipeline, pyf)
    _write_steps(pipeline, pyf)
    _write_values(pipeline, pyf)
    _write_nodes_positions(pipeline, pyf)

    print('\n        self.do_autoexport_nodes_parameters = False', file=pyf)



