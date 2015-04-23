##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import logging
import tempfile
import subprocess

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
try:
    from traits import api as traits
except ImportError:
    from enthought.traits import api as traits

# Capsul import
from capsul.pipeline import Pipeline, PipelineNode, Switch


def disable_node_for_downhill_pipeline(pipeline, node_name):
    '''
    Disable the selected node, and keep its downhill nodes active.

    Disable the selected node, and keep its downhill nodes active by
    exporting their inputs which come from this one on the main pipeline.

    Such exports are "temporary exports" and are recorded in nodes in a
    "temporary_exports" variable.

    This operation can be reverted using remove_temporary_exports().

    Parameters
    ----------
     pipeline: Pipeline (mandatory)
        pipeline to disbale nodes in.
    node_name: str (mandatory)
        name of the node to be disabled.
    '''
    node = pipeline.nodes[node_name]
    # check output plugs to be exported in the following nodes
    to_export = set()
    for plug_name, plug in node.plugs.iteritems():
        if plug.output:
            to_export.update(plug.links_to)
    # now check in downhill nodes
    for link_spec in to_export:
        if link_spec[2] is pipeline.pipeline_node \
                or not link_spec[2].activated:
            # links to the main node are already OK (exported as outputs).
            # inactive nodes will not export either.
            continue
        # they need to be connected (as input) to the main pipeline node
        from_main = [link for link in link_spec[3].links_from \
            if link[2] is pipeline.pipeline_node]
        if len(from_main) == 0:
            print 'adding export for', link_spec[0], '.', link_spec[1]
            pipeline.export_parameter(link_spec[0], link_spec[1],
                '%s_%s' % (link_spec[0], link_spec[1]))
            if not hasattr(link_spec[2], 'temporary_exports'):
                temp_exports = []
                link_spec[2].temporary_exports = temp_exports
            else:
                temp_exports = link_spec[2].temporary_exports
            temp_exports.append(link_spec[1])
    # disable node
    setattr(pipeline.nodes_activation, node_name, False)
    remove_temporary_exports(pipeline, node_name)


def disable_node_for_uphill_pipeline(pipeline, node_name):
    '''
    Disable the selected node, and keep its uphill nodes active.

    Disable the selected node, and keep its uphill nodes active by
    exporting their outputs which go to this one on the main pipeline.

    Such exports are "temporary exports" and are recorded in nodes in a
    "temporary_exports" variable.

    This operation can be reverted using remove_temporary_exports().

    Parameters
    ----------
     pipeline: Pipeline (mandatory)
        pipeline to disbale nodes in.
    node_name: str (mandatory)
        name of the node to be disabled.
    '''
    node = pipeline.nodes[node_name]
    # check input plugs to be exported in the preceding nodes
    to_export = set()
    for plug_name, plug in node.plugs.iteritems():
        if not plug.output:
            to_export.update(plug.links_from)
    # now check in uphill nodes
    for link_spec in to_export:
        if link_spec[2] is pipeline.pipeline_node:
            # links from the main node are already OK (exported as inputs)
            continue
        # they need to be connected (as output) from the main pipeline node
        to_main = [link for link in link_spec[3].links_to \
            if link[2] is pipeline.pipeline_node]
        if len(to_main) == 0:
            print 'addin export for', link_spec[0], '.', link_spec[1]
            pipeline.export_parameter(link_spec[0], link_spec[1],
                '%s_%s' % (link_spec[0], link_spec[1]))
            if not hasattr(link_spec[2], 'temporary_exports'):
                temp_exports = []
                link_spec[2].temporary_exports = temp_exports
            else:
                temp_exports = link_spec[2].temporary_exports
            temp_exports.append(link_spec[1])
    # disable node
    setattr(pipeline.nodes_activation, node_name, False)
    remove_temporary_exports(pipeline, node_name)


def remove_temporary_exports(pipeline, node_name):
    '''
    Remove the temporary exports made from the selected node.

    Remove the temporary exports made from the selected node through
    disable_node_for_downhill_pipeline() or disable_node_for_uphill_pipeline().

    Exports in the pipeline, corresponding links, and the "temporary_exports"
    variable from the node will be cleared.

    Parameters
    ----------
     pipeline: Pipeline (mandatory)
        pipeline to disbale nodes in.
    node_name: str (mandatory)
        name of the node to be cleaned.
    '''
    node = pipeline.nodes[node_name]
    if hasattr(node, 'temporary_exports'):
        for param in node.temporary_exports:
            plug = node.plugs[param]
            print 'removing export:', node_name, '.', param
            pipeline_param = '%s_%s' % (node_name, param)
            if plug.output:
                pipeline.remove_link(
                    '%s.%s->%s' % (node_name, param, pipeline_param))
            else:
                pipeline.remove_link(
                    '%s->%s.%s' % (pipeline_param, node_name, param))
            pipeline.remove_trait(pipeline_param)
        del dest_node.temporary_exports
        pipeline.user_traits_changed = True


def reactivate_node(pipeline, node_name, direction=3):
    '''
    Re-activate the selected node.

    Re-activate the selected node after disable_node_for_downhill_pipeline() or
    disable_node_for_uphill_pipeline(), and remove the corresponding temporary
    exports in otehr nodes.

    Parameters
    ----------
     pipeline: Pipeline (mandatory)
        pipeline to disbale nodes in.
    node_name: str (mandatory)
        name of the node to be reactivated.
    direction: int (optional)
        bit-wise combination of input (1) and output (2) temporary exports
        to be cleared. Default is both ways (3).

    To revert disable_node_for_downhill_pipeline(), the direction parameter
    should strictly be 2 (output).
    To revert disable_node_for_uphill_pipeline(), the direction parameter
    should strictly be 1 (intput).
    '''
    setattr(pipeline.nodes_activation, node_name, True)
    # clear temporary exports
    node = pipeline.nodes[node_name]
    to_unexport_in = set()
    to_unexport_out = set()
    force_update = False
    for plug_name, plug in node.plugs.iteritems():
        if plug.output and (direction & 2):
            to_unexport_out.update(plug.links_to)
        elif not plug.output and (direction & 1):
            to_unexport_in.update(plug.links_from)
    # now check in downhill nodes
    for link_spec in to_unexport_out:
        if link_spec[2] is pipeline.pipeline_node:
            # links to the main node are already OK (exported as outputs)
            continue
        if hasattr(link_spec[2], 'temporary_exports'):
            dest_node_name, param, dest_node = link_spec[0:3]
            temp_exports = dest_node.temporary_exports
            if param in temp_exports:
                print 'removing export:', dest_node_name, '.', param
                pipeline_param = '%s_%s' % (dest_node_name, param)
                pipeline.remove_link(
                    '%s->%s.%s' % (pipeline_param, dest_node_name, param))
                pipeline.remove_trait(pipeline_param)
                force_update = True
                temp_exports.remove(param)
            if len(temp_exports) == 0:
                del dest_node.temporary_exports
    # now check in uphill nodes
    for link_spec in to_unexport_in:
        if link_spec[2] is pipeline.pipeline_node:
            # links to the main node are already OK (exported as outputs)
            continue
        if hasattr(link_spec[2], 'temporary_exports'):
            source_node_name, param, source_node = link_spec[0:3]
            temp_exports = source_node.temporary_exports
            if param in temp_exports:
                print 'removing export:', source_node_name, '.', param
                pipeline_param = '%s_%s' % (source_node_name, param)
                pipeline.remove_link(
                    '%s.%s->%s' % (source_node_name, param, pipeline_param))
                pipeline.remove_trait(pipeline_param)
                force_update = True
                temp_exports.remove(param)
            if len(temp_exports) == 0:
                del source_node.temporary_exports
    if force_update:
        pipeline.user_traits_changed = True


def disable_nodes_with_existing_outputs(pipeline):
    '''
    Disable nodes in a pipeline which outputs contain existing files.
    The aim is to prevent overwriting files which have already been processed,
    and to allow downstream execution of the remaining steps of the pipeline.
    Sub-pipelines nodes are disabled the same way, recursively.
    Outputs in the main pipeline which represent existing files are set to
    optional.

    This operation can be reverted using reactivate_pipeline().

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        pipeline to disbale nodes in.
    '''
    # make optional output parameters which already exist
    node = pipeline.nodes['']
    for plug_name, plug in node.plugs.iteritems():
        if plug.output and not plug.optional:
            trait = pipeline.user_traits().get(plug_name)
            if isinstance(trait.trait_type, traits.File) \
                    or isinstance(trait.trait_type, traits.Directory):
                value = getattr(pipeline, plug_name)
                if value is not None and value is not traits.Undefined \
                        and os.path.exists(value):
                    plug.optional = True
                    if hasattr(node, 'temporary_optional_plugs'):
                        temp_optional = node.temporary_optional_plugs
                    else:
                        temp_optional = []
                        node.temporary_optional_plugs = temp_optional
                    temp_optional.append(plug_name)
    # check every output of every node
    sub_pipelines = []
    disabled_nodes = set()
    for node_name, node in pipeline.nodes.iteritems():
        if node_name == '' or not hasattr(node, 'process'):
            # main pipeline node, switch...
            continue
        process = node.process
        for plug_name, plug in node.plugs.iteritems():
            if plug.output and not plug.optional:
                trait = process.user_traits().get(plug_name)
                if isinstance(trait.trait_type, traits.File) \
                        or isinstance(trait.trait_type, traits.Directory):
                    value = getattr(process, plug_name)
                    if value is not None and value is not traits.Undefined \
                            and os.path.exists(value):
                        disabled_nodes.add(node_name)
                        break
        if isinstance(node, PipelineNode) and node_name not in disabled_nodes:
            # pipelines will be dealt recursively
            sub_pipelines.append(process)
    if disabled_nodes:
        print 'disabling nodes:', disabled_nodes
    if sub_pipelines:
        print 'checking pipelines:', sub_pipelines
    for node_name in disabled_nodes:
        # disable nodes first, so that those nodes will not have exported
        # inputs
        setattr(pipeline.nodes_activation, node_name, False)
    # then export downhill inputs
    for node_name in disabled_nodes:
        disable_node_for_downhill_pipeline(pipeline, node_name)
    for sub_pipeline in sub_pipelines:
        disable_nodes_with_existing_outputs(sub_pipeline)


def reactivate_pipeline(pipeline):
    '''
    Reactivate pipeline nodes and optional plugs.

    Reactivate pipeline nodes and optional plugs after
    disable_nodes_with_existing_outputs() have been used.
    Sub-pipelines will be processed recursively.

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        pipeline to reactive nodes in.
    '''
    node = pipeline.nodes['']
    if hasattr(node, 'temporary_optional_plugs'):
        for plug_name in node.temporary_optional_plugs:
            node.plugs[plug_name].optional = False
        del node.temporary_optional_plugs
    # check every node
    sub_pipelines = []
    for node_name, node in pipeline.nodes.iteritems():
        if node_name == '':
            continue # main pipeline
        if isinstance(node, PipelineNode):
            sub_pipelines.append(node.process)
        if not node.activated:
            reactivate_node(pipeline, node_name)
    for sub_pipeline in sub_pipelines:
        reactivate_pipeline(sub_pipeline)


def pipeline_node_colors(pipeline, node):
    '''
    Node color to display boxes in GUI and graphviz graphs. Depending on the
    node type (process, pipeline, switch) and its activation, colors will
    differ.

    Parameters
    ----------
    pipeline: Pipeline
        the pipeline the node belongs to
    node: Node
        the node to be colored

    Returns
    -------
    colors: tuple
        (box_color, background_fill_color, dark_color, style). Colors are
        3-tuples of float values between 0. and 1. style is "default",
        "switch" or "pipeline".
    '''
    def _color_disabled(self, color):
        target = [0.86, 0.94, 0.86]
        new_color = ((color[0] + target[0]) / 2,
                     (color[1] + target[1]) / 2,
                     (color[2] + target[2]) / 2)
        return new_color

    BLUE_1 = (0.7, 0.7, 0.9)
    BLUE_2 = (0.5, 0.5, 0.7)
    BLUE_3 = (0.2, 0.2, 0.4)
    LIGHT_BLUE_1 = (0.95, 0.95, 1.0)
    LIGHT_BLUE_2 = (0.85, 0.85, 0.9)
    LIGHT_BLUE_3 = (0.3, 0.3, 0.5)

    #GRAY_1 = (0.7, 0.7, 0.8, 1)
    #GRAY_2 = (0.4, 0.4, 0.4, 1)
    #LIGHT_GRAY_1 = (0.7, 0.7, 0.8, 1)
    #LIGHT_GRAY_2 = (0.6, 0.6, 0.7, 1)

    SAND_1 = (0.8, 0.7, 0.3)
    SAND_2 = (1., 0.9, 0.5)
    SAND_3 = (0.5, 0.45, 0.2)
    LIGHT_SAND_1 = (0.85, 0.78, 0.48)
    LIGHT_SAND_2 = (1., 0.95, 0.73)
    LIGHT_SAND_3 = (0.6, 0.55, 0.3)

    PURPLE_1 = (0.85, 0.8, 0.85)
    PURPLE_2 = (0.8, 0.75, 0.8)
    PURPLE_3 = (0.5, 0.45, 0.5)
    DEEP_PURPLE_1 = (0.8, 0.7, 0.8)
    DEEP_PURPLE_2 = (0.6, 0.5, 0.6)
    DEEP_PURPLE_3 = (0.4, 0.35, 0.4)

    _colors = {
        'default': (BLUE_1, BLUE_2, BLUE_3, LIGHT_BLUE_1, LIGHT_BLUE_2,
                    LIGHT_BLUE_3),
        'switch': (SAND_1, SAND_2, SAND_3, LIGHT_SAND_1, LIGHT_SAND_2,
                   LIGHT_SAND_3),
        'pipeline': (DEEP_PURPLE_1, DEEP_PURPLE_2, DEEP_PURPLE_3, PURPLE_1,
                     PURPLE_2, PURPLE_3),
    }
    if isinstance(node, Switch):
        style = 'switch'
    elif isinstance(node, PipelineNode) and node is not pipeline.pipeline_node:
        style = 'pipeline'
    else:
        style = 'default'
    if node.activated and node.enabled:
        color_1, color_2, color_3 = _colors[style][0:3]
    else:
        color_1, color_2, color_3 = _colors[style][3:6]
    # TODO: reactivate this later when disabled_pipeline_steps_nodes() exists
    #if node in pipeline.disabled_pipeline_steps_nodes():
        #color_1 = _color_disabled(color_1)
        #color_2 = _color_disabled(color_2)
        #color_3 = _color_disabled(color_3)
    return color_1, color_2, color_3, style


def pipeline_link_color(plug, link):
    '''
    Link color and style for graphical display and graphviz graphs.

    Parameters
    ----------
    plug: Plug
        the plug the link belong to
    link: link tuple (5 values)
        link to color

    Returns
    -------
    link_props: tuple
        (color, style, active, weak) where color is a RGB tuple of float values
        (between 0. and 1.), style is a string ("solid", "dotted"), active and
        weak are booleans.
    '''
    GRAY_1 = (0.7, 0.7, 0.8)
    RED_2 = (0.92, 0.51, 0.12)

    active = plug.activated and link[3].activated
    if active:
        color = RED_2
    else:
        color = GRAY_1
    weak = link[4]
    if weak:  # weak link
        style = 'dotted'
    else:
        style = 'solid'
    return color, style, active, weak


def dot_graph_from_pipeline(pipeline, nodes_sizes={}, use_nodes_pos=False,
                            include_io=True, enlarge_boxes=0.):
    '''
    Build a graphviz/dot-compatible representation of the pipeline.
    The pipeline representation uses one link between two given boxes:
    parameters are not represented.

    This is different from the workflow graph, as given by
    :py:meth:`capsul.pipeline.Pipeline.workflow_graph`, in that the full graph
    is represented here, including disabled nodes.

    To build a workflow graph, see :py:func:`dot_graph_from_workflow`.

    Parameters
    ----------
    pipeline: Pipeline
        pipeline to convert to a dot graph
    nodes_sizes: dict (optional)
        nodes sizes may be specified here, keys are node names, and values are
        tuples (width, height). Special "inputs" and "outputs" keys represent
        the global inputs/outputs blocks of the pipeline.
    use_nodes_pos: bool (optional)
        if True, nodes positions in the pipeline.node_position variable will
        be used to force nodes positions in the graph.
    include_io: bool (optional)
        If True, build a node for the pipeline inputs and a node for the
        pipeline outputs. If False, these nodes will not be generated, and
        their links ignored.
    enlarge_boxes: float (optional)
        when nodes sizes are specified, enlarge them by this amount to produce
        bigger boxes

    Returns
    -------
    dot_graph: tuple
        a (nodes, edges) tuple, where nodes is a list of node tuples
        (id, node_name, props) and edges is a dict, where
        keys are (source_node_id, dest_node_id), and values are tuples
        (props, active, weak). In both cases props is a dictionary of
        properties.
        This representation is simple and is meant to feed
        :py:func:`save_dot_graph`
    '''

    def _link_color(plug, link):
        if link[4]:  # weak link
            style = 'dotted'
        else:
            style = 'solid'
        active = plug.activated and link[3].activated
        return (0, 0, 0), style, active, link[4]

    nodes = []
    edges = {}
    has_outputs = False
    nodes_pos = pipeline.node_position
    scale = 1. / 67.

    for node_name, node in pipeline.nodes.iteritems():
        if node_name == '':
            if not include_io:
                continue
            id = 'inputs'
        else:
            id = node_name
        color, bgcolor, darkcolor, style = pipeline_node_colors(pipeline, node)
        colorstr = '#%02x%02x%02x' % tuple([int(c * 255.9) for c in darkcolor])
        bgcolorstr = '#%02x%02x%02x' % tuple([int(c * 255.9) for c in bgcolor])
        node_props = {'color': colorstr, 'fillcolor': bgcolorstr}
        if style == 'switch':
            node_props.update({'shape': 'house', 'orientation': 270.})
        else:
            node_props.update({'shape': 'box'})
        if use_nodes_pos:
            pos = nodes_pos.get(id)
            if pos is not None:
                node_props.update({'pos': '%f,%f' % (pos[0] * scale,
                                                     -pos[1] * scale)})
        size = nodes_sizes.get(id)
        if size is not None:
            node_props.update({'width': (size[0] + enlarge_boxes) * scale,
                               'height': (size[1] + enlarge_boxes) * scale,
                               'fixedsize': 'true'})
        if node_name != '':
            nodes.append((id, node_name, node_props))
        has_inputs = False
        for plug_name, plug in node.plugs.iteritems():
            if (plug.output and node_name != '') \
                    or (not plug.output and node_name == ''):
                if node_name == '':
                    has_inputs = True
                links = plug.links_to
                for link in links:
                    color, style, active, weak = pipeline_link_color(
                        plug, link)
                    dest = link[0]
                    if dest == '':
                        if not include_io:
                            continue
                        dest = 'outputs'
                        has_outputs = True
                    edge = (id, dest)
                    old_edge = edges.get(edge)
                    if old_edge is not None:
                        # use stongest color/style
                        if not old_edge[2]:
                            weak = False
                            style = old_edge[0]['style']
                        if old_edge[1]:
                            active = True
                            color = old_edge[0]['color']
                    if isinstance(color, tuple):
                        color = '#%02x%02x%02x' \
                            % tuple([int(c * 255.9) for c in color])
                    props = {'color': color, 'style': style}
                    edges[edge] = (props, active, weak)
        if node_name == '' and include_io:
            main_node_props = dict(node_props)
            if has_inputs:
                nodes.append(('inputs', 'inputs', node_props))
    if has_outputs:
        print 'has_outputs'
        size = nodes_sizes.get('outputs')
        for prop in ('width', 'height', 'fixedsize'):
            if main_node_props.has_key(prop):
                del main_node_props[prop]
        if size is not None:
            main_node_props.update({'width': size[0], 'height': size[1],
                                    'fixedsize': 'true'})
        nodes.append(('outputs', 'outputs', main_node_props))

    return (nodes, edges)


def dot_graph_from_workflow(pipeline, nodes_sizes={}, use_nodes_pos=False,
                            enlarge_boxes=0.):
    '''
    Build a graphviz/dot-compatible representation of the pipeline workflow.

    This is different from the pipeline graph, as obtained
    by:py:func:`dot_graph_from_pipeline`, since only used parts are visible
    here: switches and disabled branches are removed.

    Parameters
    ----------
    pipeline: Pipeline
        pipeline to convert to a dot graph
    nodes_sizes: dict (optional)
        nodes sizes may be specified here, keys are node names, and values are
        tuples (width, height). Special "inputs" and "outputs" keys represent
        the global inputs/outputs blocks of the pipeline.
    use_nodes_pos: bool (optional)
        if True, nodes positions in the pipeline.node_position variable will
        be used to force nodes positions in the graph.
    enlarge_boxes: float (optional)
        when nodes sizes are specified, enlarge them by this amount to produce
        bigger boxes

    Returns
    -------
    dot_graph: tuple
        a (nodes, edges) tuple, where nodes is a list of node tuples
        (id, node_name, props) and edges is a dict, where
        keys are (source_node_id, dest_node_id), and values are tuples
        (props, active, weak). In both cases props is a dictionary of
        properties.
        This representation is simple and is meant to feed
        :py:func:`save_dot_graph`
    '''

    graph = pipeline.workflow_graph()
    nodes = []
    edges = {}

    for n in graph._nodes:
        node = pipeline.nodes[n]
        color, bgcolor, darkcolor, style = pipeline_node_colors(pipeline, node)
        colorstr = '#%02x%02x%02x' % tuple([int(c * 255.9) for c in darkcolor])
        bgcolorstr = '#%02x%02x%02x' % tuple([int(c * 255.9) for c in bgcolor])
        node_props = {'color': colorstr, 'fillcolor': bgcolorstr}
        if style == 'switch':
            node_props.update({'shape': 'house', 'orientation': 270.})
        else:
            node_props.update({'shape': 'box'})
        if use_nodes_pos:
            pos = nodes_pos.get(id)
            if pos is not None:
                node_props.update({'pos': '%f,%f' % (pos[0] * scale,
                                                     -pos[1] * scale)})
        size = nodes_sizes.get(id)
        if size is not None:
            node_props.update({'width': (size[0] + enlarge_boxes) * scale,
                               'height': (size[1] + enlarge_boxes) * scale,
                               'fixedsize': 'true'})
        nodes.append((n, n, node_props))
    for n, v in graph._links:
        edge = (n, v)
        props = {'color': '#eb821e', 'style': 'solid'}
        edges[edge] = (props, True, False)

    return (nodes, edges)


def save_dot_graph(dot_graph, filename, **kwargs):
    '''
    Write a graphviz/dot input file, which can be used to generate an
    image representation of the graph, or to make dot automatically
    position nodes.

    Parameters
    ----------
    dot_graph: dot graph
        representation of the pipeline, obatained using
        :py:func:`dot_graph_from_pipeline`
    filename: string
        file name to save the dot definition in
    **kwargs: additional attributes for the dot graph
      like nodesep=0.1 or rankdir="TB"
    '''
    def _str_repr(item):
        if isinstance(item, basestring):
            return '"%s"' % item
        return repr(item)

    fileobj = open(filename, 'w')
    props = {'rankdir': 'LR'}
    props.update(kwargs)
    propsstr = ' '.join(['='.join([aname, _str_repr(val)])
                           for aname, val in props.iteritems()])
    rankdir = props['rankdir']

    fileobj.write('digraph {%s;\n' % propsstr)
    nodesep = 20. # in qt scale space
    scale = 1. / 67.
    for id, node, props in dot_graph[0]:
        if rankdir == 'TB' and 'orientation' in props:
            props = dict(props)
            props['orientation'] -= 90
        attstr = ' '.join(['='.join([aname, _str_repr(val)])
                           for aname, val in props.iteritems()])
        if len(props) != 0:
            attstr = ' ' + attstr
        fileobj.write('  %s [label=%s style="filled"%s];\n'
            % (id, node, attstr))
    for edge, descr in dot_graph[1].iteritems():
        props = descr[0]
        attstr = ' '.join(['='.join([aname, _str_repr(val)])
                           for aname, val in props.iteritems()])
        fileobj.write('  %s -> %s [%s];\n'
            % (edge[0], edge[1], attstr))
    fileobj.write('}\n')


def save_dot_image(pipeline, filename, nodes_sizes={}, use_nodes_pos=False,
                   include_io=True, enlarge_boxes=0., workflow=False,
                   format=None, **kwargs):
    '''
    Save a dot/graphviz image of the pipeline in a file.

    It may use either the complete pipeline graph (with switches and disabled
    branches), or the workflow, hiding disabled parts (see the workflow
    parameter).

    Basically combines :py:func:`dot_graph_from_pipeline` or
    :py:func:`dot_graph_from_workflow`, and :py:func:`save_dot_graph`, then
    runs the `dot <http://www.graphviz.org>`_ command, which has to be
    installed and available on the system.

    Parameters
    ----------
    pipeline: Pipeline
        pipeline to convert to a dot graph
    filename: string
        file name to save the dot definition in.
    nodes_sizes: dict (optional)
        nodes sizes may be specified here, keys are node names, and values are
        tuples (width, height). Special "inputs" and "outputs" keys represent
        the global inputs/outputs blocks of the pipeline.
    use_nodes_pos: bool (optional)
        if True, nodes positions in the pipeline.node_position variable will
        be used to force nodes positions in the graph.
    include_io: bool (optional)
        If True, build a node for the pipeline inputs and a node for the
        pipeline outputs. If False, these nodes will not be generated, and
        their links ignored.
    enlarge_boxes: float (optional)
        when nodes sizes are specified, enlarge them by this amount to produce
        bigger boxes
    workflow: bool (optional)
        if True, the workflow corresponding to the current pipeline state will
        be used instead of the complete graph: disabled parts will be hidden.
    format: string (optional)
        dot output format (see `dot <http://www.graphviz.org>`_ command doc).
        If not specified, guessed from the file name extension.
    **kwargs: additional attributes for the dot graph
      like nodesep=0.1 or rankdir="TB"
    '''
    if workflow:
        dgraph = dot_graph_from_workflow(
            pipeline, nodes_sizes=nodes_sizes, use_nodes_pos=use_nodes_pos,
            enlarge_boxes=enlarge_boxes)
    else:
        dgraph = dot_graph_from_pipeline(
            pipeline, nodes_sizes=nodes_sizes, use_nodes_pos=use_nodes_pos,
            include_io=include_io, enlarge_boxes=enlarge_boxes)
    tempf = tempfile.mkstemp()
    os.close(tempf[0])
    dot_filename = tempf[1]
    save_dot_graph(dgraph, dot_filename, **kwargs)
    if format is None:
        ext = filename.split('.')[-1]
        formats = {'txt': 'plain'}
        format = formats.get(ext, ext)
    cmd = ['dot', '-T%s' % ext, '-o', filename, dot_filename]
    subprocess.check_call(cmd)
    os.unlink(dot_filename)

