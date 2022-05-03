# -*- encoding: utf-8 -*-

'''
JSON IO for pipelines

Functions
=========
:func:`create_json_pipeline`
---------------------------
:func:`save_json_pipeline`
-------------------------
'''

import json
import os
from traits.api import Undefined
from soma.controller import Controller
from capsul.pipeline.pipeline_construction import PipelineConstructor


def create_json_pipeline(module, name, json_file):
    """
    Create a pipeline class given its Capsul JSON representation.

    Parameters
    ----------
    module: str (mandatory)
        name of the module for the created Pipeline class (the Python module is
        not modified).
    name: str (mandatory)
        name of the new pipeline class
    json_file: str or dict of file object (mandatory)
        name of file containing the JSON description or JSON dict.

    """
    json_filename = None
    if hasattr(json_file, 'read'):
        json_pipeline = json.load(json_file)
        json_filename = getattr(json_file, 'name', None)
    elif os.path.exists(json_file):
        with open(json_file) as f:
            json_pipeline = json.load(f)
        json_filename = json_file
    elif isinstance(json_file, (bytes, str)):
        json_pipeline = json.loads(json_file)
    else:
        json_pipeline = json_file

    class_name = json_pipeline.get('name')
    if class_name:
        if name is None:
            name = class_name
        elif name != class_name:
            raise KeyError('pipeline name (%s) and requested object name '
                           '(%s) differ.' % (class_name, name))
    elif name is None and json_filename is not None:
        name = os.path.basename(json_filename).rsplit('.', 1)[0]

    builder = PipelineConstructor(module, name)
    definition = json_pipeline['definition']

    done = set()
    # sort things to be done
    todo = ['export_parameters', 'doc', 'executables', 'processes_selections',
            'links', 'weak_links', 'plug_state', 'parameters']
    todo += [k for k in definition.keys() if k not in todo]


    for child_name in todo:
        child = definition.get(child_name)
        if child is None:
            continue

        if child_name == 'doc':
            if child is not None:
                builder.set_documentation(child.strip())
        elif child_name == 'executables':
            for process_name, process_def in child.items():
                type = process_def.get('type')
                if type == 'switch':
                    inputs = process_def.get('inputs', [])
                    outputs = process_def.get('outputs', [])
                    value = process_def.get('value')
                    optional = process_def.get('optional', ())
                    builder.add_switch(process_name, inputs, outputs, False,
                                       optional, switch_value=value)

                else:
                    # process / pipeline

                    iterate = []
                    if type == 'iterative_process':
                        iterate = process_def['iterative_parameters']

                    module = process_def.get('definition')
                    args = (process_name, module)
                    kwargs = {}
                    #nipype_usedefault = []
                    #links = []
                    #for process_child in process_def:
                        #if process_child_name == 'set':
                            #name = process_child.get('name')
                            #value = process_child.get('value')
                            #value = string_to_value(value)
                            #if value is not None:
                                #kwargs[name] = value
                            #kwargs.setdefault('make_optional', []).append(name)
                        #elif process_child_name == 'nipype':
                            #name = process_child.get('name')
                            #usedefault = process_child.get('usedefault')
                            #if usedefault == 'true':
                                #nipype_usedefault.append(name)
                            #copyfile = process_child.get('copyfile')
                            #if copyfile == 'true':
                                #kwargs.setdefault('inputs_to_copy', []).append(name)
                            #elif copyfile == 'discard':
                                #kwargs.setdefault('inputs_to_copy', []).append(name)
                                #kwargs.setdefault('inputs_to_clean', []).append(name)
                        #elif process_child_name == 'link':
                            ## internal export
                            #source = process_child.get('source')
                            #dest = process_child.get('dest')
                            #links.append([source, dest, None])
                        #else:
                            #raise ValueError('Invalid tag in <process>: %s' %
                                            #process_child_name)
                    #if links:
                        #todel = []
                        #for link in links:
                            #k = link[0]
                            #if '.' in k:
                                #k = link[1]
                            #v = kwargs.get(k)
                            #if v is not None:
                                #link[2] = v
                                #del kwargs[k]
                    if iterate:
                        kwargs['iterative_plugs'] = iterate
                        builder.add_iterative_process(*args, **kwargs)
                    else:
                        builder.add_process(*args, **kwargs)
                    #for name in nipype_usedefault:
                        #builder.call_process_method(process_name, 'set_usedefault',
                                                    #name, True)
                    #if links:
                        #for link in links:
                            #builder.add_subpipeline_link(process_name, link[0],
                                                        #link[1], value=link[2])
                    enabled = process_def.get('enabled')
                    if enabled == 'false':
                        builder.set_node_enabled(process_name, False)
        #elif child_name == 'switch':
            #switch_name = child.get('name')
            #value = child.get('switch_value')
            #kwargs = {'export_switch': False}
            #if value:
                #kwargs['switch_value'] = value
            #inputs = []
            #outputs = []
            #for process_child in child:
                #if process_child_name == 'input':
                    #name = process_child.get('name')
                    #inputs.append(name)
                #elif process_child_name == 'output':
                    #name = process_child.get('name')
                    #outputs.append(name)
                    #optional = process_child.get('optional')
                    #if optional == 'true':
                        #kwargs.setdefault('make_optional', []).append(name)
            #builder.add_switch(switch_name, inputs, outputs, **kwargs)
            #enabled = child.get('enabled')
            #if enabled == 'false':
                #builder.set_node_enabled(switch_name, False)
        #elif child_name == 'optional_output_switch':
            #switch_name = child.get('name')
            #kwargs = {}
            #input = None
            #output = None
            #for process_child in child:
                #if process_child_name == 'input':
                    #if input is not None:
                        #raise ValueError(
                            #'Several inputs in optional_output_switch')
                    #input = process_child.get('name')
                #elif process_child_name == 'output':
                    #if output is not None:
                        #raise ValueError(
                            #'Several outputs in optional_output_switch')
                    #output = process_child.get('name')
            #if input is None:
                #raise ValueError('No input in optional_output_switch')
            #builder.add_optional_output_switch(switch_name, input, output)
            #enabled = child.get('enabled')
            #if enabled == 'false':
                #builder.set_node_enabled(switch_name, False)

        #elif child_name == 'custom_node':
            #node_name = child.get('name')
            #module = child.get('module')
            #params = {}
            #kwargs = {}
            #make_optional = []
            #for process_child in child:
                #if process_child_name == 'config':
                    #for p, value in process_child.items():
                          #params[p] = string_to_value(value)
                #elif process_child_name == 'set':
                    #name = process_child.get('name')
                    #value = process_child.get('value')
                    #value = string_to_value(value)
                    #if value is not None:
                        #kwargs[name] = value
                    #make_optional.append(name)
                #else:
                    #raise ValueError('Invalid tag in <process>: %s' %
                                     #process_child_name)
            ## TODO optional plugs
            #builder.add_custom_node(node_name, module, params, make_optional,
                                    #**kwargs)

            #enabled = child.get('enabled')
            #if enabled == 'false':
                #builder.set_node_enabled(node_name, False)

        elif child_name == 'links':
            for link in child:
                builder.add_link(link, weak_link=False, allow_export=True)
        elif child_name == 'weak_links':
            for link in child:
                builder.add_link(link, weak_link=True, allow_export=True)
        elif child_name == 'processes_selections':
            for selection_parameter, selection in child.items():
                selection_groups = selection['groups']
                value = selection['value']
                builder.add_processes_selection(selection_parameter,
                                                selection_groups, value)
        elif child_name == 'pipeline_steps':
            for step_name, step_child in child.items():
                enabled = bool(step_child.get('enabled', True))
                nodes = step_child['nodes']
                builder.add_pipeline_step(step_name, nodes, enabled)
        elif child_name == 'gui':
            for gui_child_name, gui_child in child.items():
                if gui_child_name == 'position':
                    for name, position in gui_child.items():
                        builder.set_node_position(name, position[0],
                                                  position[1])
                elif gui_child_name == 'zoom':
                    builder.set_scene_scale_factor(gui_child)
                else:
                    raise ValueError('Invalid tag in <gui>: %s' %
                                     gui_child_name)
        elif child_name == 'plug_state':
            for plug_name, state in child.items():
                for key, value in state.items():
                    builder.add_plug_state(plug_name, key, value)
        elif child_name == 'parameters':
            for key, value in child.items():
                node_key = key.rsplit('.', 1)
                key = node_key[-1]
                if len(node_key) >= 2:
                    node_name = node_key[0]
                else:
                    node_name = ''
                builder.set_plug_value(node_name, key, value)
        elif child_name == 'export_parameters':
            builder.set_export_parameters(child)
        else:
            raise ValueError('Invalid tag in <pipeline>: %s' % child_name)
    return builder.pipeline


def save_json_pipeline(pipeline, json_file):
    '''
    Save a pipeline in an JSON file

    Parameters
    ----------
    pipeline: Pipeline instance
        pipeline to save
    json_file: str or file-like object
        JSON file to save the pipeline in
    '''
    # imports are done locally to avoid circular imports
    from capsul.api import Process, Pipeline
    from capsul.pipeline.pipeline_nodes import ProcessNode, Switch, \
        OptionalOutputSwitch, PipelineNode
    from capsul.pipeline.process_iteration import ProcessIteration
    from capsul.process.process import NipypeProcess
    from capsul.study_config.process_instance import get_process_instance

    def _write_process(node, parent, name, dont_write_plug_values=set(),
                       init_plug_values={}):
        process = node.process
        procnode = {}
        if isinstance(process, NipypeProcess):
            mod = process._nipype_interface.__module__
            classname = process._nipype_interface.__class__.__name__
        else:
            mod = process.__module__
            # if process is a function with XML decorator, we need to
            # retrieve the original function name.
            func = getattr(process, '_function', None)
            if func:
                classname = func.__name__
            else:
                classname = process.__class__.__name__
                if classname == 'Pipeline':
                    # don't accept the base Pipeline class
                    classname = name
                    if '.' in class_name:
                        classname = classname[:classname.index('.')]
                    classname = classname[0].upper() + class_name[1:]
        procnode['definition'] = "%s.%s" % (mod, classname)
        procnode['type'] = 'process'
        parent.setdefault('executables', {})[name] = procnode

        try:
            proc_copy = get_process_instance("%s.%s" % (mod, classname))
        except Exception:
            proc_copy = process  # don't duplicate, don't test differences
        # set initial values
        dont_write_plug_values = set(dont_write_plug_values)
        dont_write_plug_values.update(('nodes_activation',
                                       'selection_changed'))

        _write_states(parent, name, node, proc_copy)

        params = {}

        for param_name, trait in process.user_traits().items():
            if param_name not in proc_copy.traits():
                continue
            if param_name not in dont_write_plug_values:
                if param_name in init_plug_values:
                    value = init_plug_values[param_name]
                else:
                    value = getattr(process, param_name)
                if value not in (None, Undefined, '', []) \
                        or (trait.optional
                            and not proc_copy.trait(param_name).optional):
                    if isinstance(value, Controller):
                        value_repr = dict(value.export_to_dict())
                    else:
                        value_repr = value
                    full_pname = param_name
                    if name:
                        full_pname = '.'.join((name, param_name))
                    params[full_pname] = value_repr
        if params:
            parent.setdefault('parameters', {}).update(params)

        return procnode

    def _write_states(root, name, node, proc_copy):
        # check that sub-nodes enable and plugs optional states are the
        # expected ones
        todo = [(name, node, ProcessNode(node.pipeline, node.name, proc_copy))]
        while todo:
            self_str, snode, cnode = todo.pop(0)
            if not snode.enabled:
                item = {'enabled': False}
                root.setdefault('state', {})[self_str] = item

            # if the node is a (sub)pipeline, and this pipeline has additional
            # exported traits compared to the its base module/class instance
            # (proc_copy),  then we must use explicit exports/links inside it
            if isinstance(snode, PipelineNode):
                sproc = snode.process
                cproc = cnode.process
                for param_name, trait in sproc.user_traits().items():
                    optional = None
                    if param_name not in cproc.traits():
                        # param added, not in the original process
                        is_input = not trait.output
                        if (is_input and sproc.pipeline_node.plugs[
                                    param_name].links_to) \
                                or (not is_input
                                    and sproc.pipeline_node.plugs[
                                        param_name].links_from):
                            if is_input:
                                for link in sproc.pipeline_node.plugs[
                                        param_name].links_to:
                                    if link[4]:
                                        links = root.setdefault('weak_links',
                                                                [])
                                    else:
                                        links = root.setdefault('links', [])
                                    link_el = '%s.%s->%s' % (
                                        self_str, param_name,
                                        '.'.join((self_str, link[0], link[1])))
                                    links.append(link_el)
                            else:
                                for link in sproc.pipeline_node.plugs[
                                        param_name].links_from:
                                    if link[4]:
                                        links = root.setdefault('weak_links',
                                                                [])
                                    else:
                                        links = root.setdefault('links', [])
                                    link_el = '%s->%s.%s' % (
                                        '.'.join((self_str, link[0], link[1])),
                                        self_str, param_name)
                                    links.append(link_el)

            for param_name, plug in snode.plugs.items():
                trait = snode.get_trait(param_name)
                ctrait = cnode.get_trait(param_name)
                optional = None
                if param_name not in cnode.plugs \
                        or trait.optional != ctrait.optional:
                    optional = trait.optional
                if optional is not None:
                    item = {'optional': bool(optional)}
                    states = root.setdefault('plug_state', {})
                    states['%s.%s' % (self_str, param_name)] = item

            if isinstance(snode, PipelineNode):
                for node_name, snode in snode.process.nodes.items():
                    scnode = cnode.process.nodes[node_name]

                    if node_name == '':
                        continue
                    todo.append(('%s.%s' % (self_str, node_name), snode,
                                 scnode))

    def _write_switch(switch, parent, name):
        swnode = {'type': 'switch'}
        mod = switch.__module__
        classname = switch.__class__.__name__
        swnode['definition'] = "%s.%s" % (mod, classname)

        inputs = set()
        outputs = []
        optional = []
        for plug_name, plug in switch.plugs.items():
            if plug.output:
                outputs.append(plug_name)
                if plug.optional:
                    optional.append(plug_name)
            else:
                name_parts = plug_name.split("_switch_")
                if len(name_parts) == 2 and name_parts[0] not in inputs:
                    inputs.add(name_parts[0])
                    if plug.optional:
                        optional.append(plug_name)
        swnode['value'] = str(switch.switch)
        swnode['inputs'] = sorted(inputs)
        swnode['outputs'] = outputs
        if optional:
            swnode['optional'] = optional
        parent.setdefault('executables', {})[name] = swnode
        return swnode

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
        root['doc'] = docstr
        return docstr

    def _write_processes(pipeline, root):
        for node_name, node in pipeline.nodes.items():
            if node_name == "":
                continue
            if isinstance(node, OptionalOutputSwitch):
                xmlnode = _write_optional_output_switch(node, root, node_name)
            elif isinstance(node, Switch):
                xmlnode = _write_switch(node, root, node_name)
            elif isinstance(node, ProcessNode) \
                    and isinstance(node.process, ProcessIteration):
                xmlnode = _write_iteration(node, root, node_name)
            elif isinstance(node, ProcessNode):
                xmlnode = _write_process(node, root, node_name)
            else:
                xmlnode = _write_custom_node(node, root, node_name)
            if not node.enabled:
                xmlnode.set('enabled', 'false')

    def _write_links(pipeline, root):
        for node_name, node in pipeline.nodes.items():
            for plug_name, plug in node.plugs.items():
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
                        linkelem = '%s->%s' % (src, dst)
                        if link[-1]:
                            links = root.setdefault('weak_links', [])
                        else:
                            links = root.setdefault('links', [])
                        links.append(linkelem)

    def _write_steps(pipeline, root):
        steps = pipeline.trait('pipeline_steps')
        steps_node = None
        if steps and getattr(pipeline, 'pipeline_steps', None):
            steps_node = {}
            for step_name, step \
                    in pipeline.pipeline_steps.user_traits().items():
                step_node = {}
                enabled = getattr(pipeline.pipeline_steps, step_name)
                if not enabled:
                    step_node['enabled'] = False
                nodes = step.nodes
                node_items = []
                for node in nodes:
                    node_items.append(node)
                step_node['nodes'] = node_items
                steps_node[step_name] = step_node
        if steps_node:
            root['pipeline_steps'] = steps_node
        return steps_node

    def _write_nodes_positions(pipeline, root):
        gui = {}
        if hasattr(pipeline, "node_position") and pipeline.node_position:
            gui = {}
            for node_name, pos in pipeline.node_position.items():
                if hasattr(pos, 'x'):
                    # it's a QPointF
                    node_pos = [float(pos.x()), float(pos.y())]
                else:
                    # it's a python iterable
                    node_pos = [float(pos[0]), float(pos[1])]
                gui[node_name] = node_pos

        if hasattr(pipeline, "scene_scale_factor"):
            gui['zoom'] = float(pipeline.scene_scale_factor)

        if gui:
            root['gui'] = gui

        return gui

    def _write_processes_selections(pipeline, root):
        selection_parameters = []
        if hasattr(pipeline, 'processes_selection'):
            for selector_name, groups in pipeline.processes_selection.items():
                selection_parameters.append(selector_name)
                sel_node = {}
                sel_node['groups'] = dict(groups)
                sel_node['value'] = getattr(pipeline, selector_name)
                root.setdefault('processes_selections',
                                {})[selector_name] = sel_node
        return selection_parameters


    root = {'type': 'custom_pipeline'}
    class_name = pipeline.__class__.__name__
    if pipeline.__class__ is Pipeline:
        # if directly a Pipeline, then use a default new name
        class_name = 'CustomPipeline'
    root['name'] = class_name

    definition = {'export_parameters': False}
    root['definition'] = definition

    _write_doc(pipeline, definition)
    _write_processes(pipeline, definition)
    _write_links(pipeline, definition)
    _write_processes_selections(pipeline, definition)
    _write_steps(pipeline, definition)
    _write_nodes_positions(pipeline, definition)

    if isinstance(json_file, str):
        json_filename = json_file
        with open(json_filename, 'w') as json_file:
            json.dump(root, json_file, indent=4)
    else:
        json.dump(root, json_file, indent=4)
