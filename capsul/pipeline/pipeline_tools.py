"""
Miscellaneous pipeline handling utility functions

Functions
=========
:func:`pipeline_node_colors`
----------------------------
:func:`pipeline_link_color`
---------------------------
:func:`dot_graph_from_pipeline`
-------------------------------
:func:`dot_graph_from_workflow`
-------------------------------
:func:`save_dot_graph`
----------------------
:func:`save_dot_image`
----------------------
:func:`disable_runtime_steps_with_existing_outputs`
---------------------------------------------------
:func:`nodes_with_existing_outputs`
-----------------------------------
:func:`nodes_with_missing_inputs`
---------------------------------
:func:`where_is_plug_value_from`
--------------------------------
:func:`dump_pipeline_state_as_dict`
-----------------------------------
:func:`set_pipeline_state_from_dict`
------------------------------------
:func:`save_pipeline`
---------------------
:func:`load_pipeline_parameters`
--------------------------------
:func:`save_pipeline_parameters`
--------------------------------
:func:`is_node_enabled`
-----------------------
"""

import dataclasses
import json
import os
import sys
import tempfile

import soma.subprocess
from populse_db import json_decode, json_encode
from soma.controller import Any, Controller, undefined

# Capsul import
from capsul.application import executable
from capsul.pipeline.pipeline import Pipeline, Process, Switch
from capsul.pipeline.process_iteration import ProcessIteration


def pipeline_node_colors(pipeline, node):
    """
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
    """

    def _color_disabled(color):
        target = [0.86, 0.94, 0.86]
        new_color = (
            (color[0] + target[0]) / 2,
            (color[1] + target[1]) / 2,
            (color[2] + target[2]) / 2,
        )
        return new_color

    #     BLUE_1 = (0.7, 0.7, 0.9)
    #     BLUE_2 = (0.5, 0.5, 0.7)
    #     BLUE_3 = (0.2, 0.2, 0.4)
    #     LIGHT_BLUE_1 = (0.95, 0.95, 1.0)
    #     LIGHT_BLUE_2 = (0.85, 0.85, 0.9)
    #     LIGHT_BLUE_3 = (0.3, 0.3, 0.5)

    # for process nodes
    GREENDARK_1 = (0.1, 0.9, 0.1)  # active
    GREENDARK_2 = (0.1, 0.7, 0.1)
    GREENDARK_3 = (0.1, 0.5, 0.1)
    LIGHT_GREENDARK_1 = (0.1, 0.6, 0.1)  # not active
    LIGHT_GREENDARK_2 = (0.1, 0.5, 0.1)
    LIGHT_GREENDARK_3 = (0.1, 0.3, 0.1)

    # for inputs and outputs nodes
    SEA_1 = (0.0, 0.9, 0.85)  # active
    SEA_2 = (0.0, 0.6, 0.85)
    SEA_3 = (0.0, 0.3, 0.85)
    LIGHT_SEA_1 = (0.0, 0.5, 0.5)  # not active
    LIGHT_SEA_2 = (0.0, 0.4, 0.5)
    LIGHT_SEA_3 = (0.0, 0.3, 0.5)

    # for switch nodes
    SAND_1 = (0.8, 0.7, 0.5)
    SAND_2 = (0.7, 0.6, 0.5)
    SAND_3 = (0.5, 0.45, 0.2)
    LIGHT_SAND_1 = (0.85, 0.78, 0.48)
    LIGHT_SAND_2 = (1.0, 0.95, 0.73)
    LIGHT_SAND_3 = (0.6, 0.55, 0.3)

    # for pipeline nodes
    PURPLE_1 = (0.5, 0.4, 0.6)  # not active
    PURPLE_2 = (0.49, 0.27, 0.49)
    PURPLE_3 = (0.62, 0.36, 0.63)
    DEEP_PURPLE_1 = (0.72, 0.51, 0.74)  # active
    DEEP_PURPLE_2 = (0.52, 0.41, 0.54)
    DEEP_PURPLE_3 = (0.3, 0.31, 0.34)

    #     PURPLE_1 = (0.85, 0.8, 0.85)
    #     PURPLE_2 = (0.8, 0.75, 0.8)
    #     PURPLE_3 = (0.5, 0.45, 0.5)
    #     DEEP_PURPLE_1 = (0.8, 0.7, 0.8)
    #     DEEP_PURPLE_2 = (0.6, 0.5, 0.6)
    #     DEEP_PURPLE_3 = (0.4, 0.35, 0.4)

    # for iteration nodes
    GREEN_1 = (0.7, 0.9, 0.7)
    GREEN_2 = (0.5, 0.7, 0.5)
    GREEN_3 = (0.2, 0.4, 0.2)
    LIGHT_GREEN_1 = (0.95, 1.0, 0.95)
    LIGHT_GREEN_2 = (0.85, 0.9, 0.85)
    LIGHT_GREEN_3 = (0.3, 0.5, 0.3)

    # for attributed nodes
    SKY_1 = (0.6, 0.7, 1.0)
    SKY_2 = (0.3, 0.5, 0.8)
    SKY_3 = (0.0, 0.2, 0.5)
    LIGHT_SKY_1 = (0.8, 0.85, 1.0)
    LIGHT_SKY_2 = (0.7, 0.75, 0.9)
    LIGHT_SKY_3 = (0.2, 0.3, 0.6)

    APPLE_1 = (0.7, 0.8, 0.3)
    APPLE_2 = (0.9, 1.0, 0.5)
    APPLE_3 = (0.45, 0.5, 0.2)
    LIGHT_APPLE_1 = (0.78, 0.85, 0.48)
    LIGHT_APPLE_2 = (0.95, 1.0, 0.73)
    LIGHT_APPLE_3 = (0.55, 0.6, 0.3)

    # for custom_nodes
    ORANGE_1 = (0.92, 0.69, 0.53)
    # ORANGE_2 = (0.73, 0.4, 0.26)
    ORANGE_2 = (0.86, 0.54, 0.3)
    ORANGE_3 = (0.4, 0.2, 0.1)
    LIGHT_ORANGE_1 = (1.0, 0.93, 0.88)
    LIGHT_ORANGE_2 = (0.9, 0.8, 0.7)
    LIGHT_ORANGE_3 = (0.4, 0.3, 0.2)

    _colors = {
        "default": (
            GREENDARK_1,
            GREENDARK_2,
            GREENDARK_3,
            LIGHT_GREENDARK_1,
            LIGHT_GREENDARK_2,
            LIGHT_GREENDARK_3,
        ),
        "switch": (SAND_1, SAND_2, SAND_3, LIGHT_SAND_1, LIGHT_SAND_2, LIGHT_SAND_3),
        "pipeline": (
            DEEP_PURPLE_1,
            DEEP_PURPLE_2,
            DEEP_PURPLE_3,
            PURPLE_1,
            PURPLE_2,
            PURPLE_3,
        ),
        "pipeline_io": (SEA_1, SEA_2, SEA_3, LIGHT_SEA_1, LIGHT_SEA_2, LIGHT_SEA_3),
        "iteration": (
            GREEN_1,
            GREEN_2,
            GREEN_3,
            LIGHT_GREEN_1,
            LIGHT_GREEN_2,
            LIGHT_GREEN_3,
        ),
        "attributed": (SKY_1, SKY_2, SKY_3, LIGHT_SKY_1, LIGHT_SKY_2, LIGHT_SKY_3),
        "optional_output_switch": (
            APPLE_1,
            APPLE_2,
            APPLE_3,
            LIGHT_APPLE_1,
            LIGHT_APPLE_2,
            LIGHT_APPLE_3,
        ),
        "custom_node": (
            ORANGE_1,
            ORANGE_2,
            ORANGE_3,
            LIGHT_ORANGE_1,
            LIGHT_ORANGE_2,
            LIGHT_ORANGE_3,
        ),
    }
    if node is pipeline:
        style = "pipeline_io"
    elif isinstance(node, Switch):
        style = "switch"
    elif isinstance(node, Pipeline):
        style = "pipeline"
    elif isinstance(node, ProcessIteration):
        style = "iteration"
    elif isinstance(node, Process):
        if hasattr(node, "completion_engine"):
            style = "attributed"
        else:
            style = "default"
    else:
        style = "custom_node"
    if node.activated and node.enabled:
        color_1, color_2, color_3 = _colors[style][0:3]
    else:
        color_1, color_2, color_3 = _colors[style][3:6]
    if node in pipeline.disabled_pipeline_steps_nodes():
        color_1 = _color_disabled(color_1)
        color_2 = _color_disabled(color_2)
        color_3 = _color_disabled(color_3)
    return color_1, color_2, color_3, style


def pipeline_link_color(plug, link):
    """
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
    """
    GRAY_1 = (0.7, 0.7, 0.8)
    RED_2 = (0.92, 0.51, 0.12)

    active = plug.activated and link[3].activated
    if active:
        color = RED_2
    else:
        color = GRAY_1
    weak = link[4]
    if weak:  # weak link
        style = "dotted"
    else:
        style = "solid"
    return color, style, active, weak


def dot_graph_from_pipeline(
    pipeline, nodes_sizes=None, use_nodes_pos=False, include_io=True, enlarge_boxes=0.0
):
    """
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
    """

    def _link_color(plug, link):
        if link[4]:  # weak link
            style = "dotted"
        else:
            style = "solid"
        active = plug.activated and link[3].activated
        return (0, 0, 0), style, active, link[4]

    nodes_sizes = nodes_sizes or {}
    nodes = []
    edges = {}
    has_outputs = False
    nodes_pos = pipeline.node_position
    scale = 1.0 / 67.0

    for node_name, node in pipeline.nodes.items():
        if node_name == "":
            if not include_io:
                continue
            id = "inputs"
        else:
            id = node_name
        color, bgcolor, darkcolor, style = pipeline_node_colors(pipeline, node)
        colorstr = "#%02x%02x%02x" % tuple([int(c * 255.9) for c in darkcolor])
        bgcolorstr = "#%02x%02x%02x" % tuple([int(c * 255.9) for c in bgcolor])
        node_props = {"color": colorstr, "fillcolor": bgcolorstr}
        if style == "switch":
            node_props.update({"shape": "house", "orientation": 270.0})
        else:
            node_props.update({"shape": "box"})
        if use_nodes_pos:
            pos = nodes_pos.get(id)
            if pos is not None:
                node_props.update({"pos": "%f,%f" % (pos[0] * scale, -pos[1] * scale)})
        size = nodes_sizes.get(id)
        if size is not None:
            node_props.update(
                {
                    "width": (size[0] + enlarge_boxes) * scale,
                    "height": (size[1] + enlarge_boxes) * scale,
                    "fixedsize": "true",
                }
            )
        if node_name != "":
            nodes.append((id, node_name, node_props))
        has_inputs = False
        for plug_name, plug in node.plugs.items():
            if (plug.output and node_name != "") or (
                not plug.output and node_name == ""
            ):
                if node_name == "":
                    has_inputs = True
                links = plug.links_to
                for link in links:
                    color, style, active, weak = pipeline_link_color(plug, link)
                    dest = link[0]
                    if dest == "":
                        if not include_io:
                            continue
                        dest = "outputs"
                        has_outputs = True
                    edge = (id, dest)
                    old_edge = edges.get(edge)
                    if old_edge is not None:
                        # use strongest color/style
                        if not old_edge[2]:
                            weak = False
                            style = old_edge[0]["style"]
                        if old_edge[1]:
                            active = True
                            color = old_edge[0]["color"]
                    if isinstance(color, tuple):
                        color = "#%02x%02x%02x" % tuple([int(c * 255.9) for c in color])
                    props = {"color": color, "style": style}
                    edges[edge] = (props, active, weak)
        if node_name == "" and include_io:
            main_node_props = dict(node_props)
            if has_inputs:
                nodes.append(("inputs", "inputs", node_props))
    if has_outputs:
        size = nodes_sizes.get("outputs")
        for prop in ("width", "height", "fixedsize"):
            if prop in main_node_props:
                del main_node_props[prop]
        if size is not None:
            main_node_props.update(
                {
                    "width": (size[0] + enlarge_boxes) * scale,
                    "height": (size[1] + enlarge_boxes) * scale,
                    "fixedsize": "true",
                }
            )
        nodes.append(("outputs", "outputs", main_node_props))

    return (nodes, edges)


def dot_graph_from_workflow(
    pipeline, nodes_sizes=None, use_nodes_pos=False, enlarge_boxes=0.0
):
    """
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
    """

    nodes_sizes = nodes_sizes or {}
    graph = pipeline.workflow_graph()
    nodes = []
    edges = {}
    scale = 1.0 / 67.0

    for n in graph._nodes:
        node = pipeline.nodes[n]
        color, bgcolor, darkcolor, style = pipeline_node_colors(pipeline, node)
        colorstr = "#%02x%02x%02x" % tuple([int(c * 255.9) for c in darkcolor])
        bgcolorstr = "#%02x%02x%02x" % tuple([int(c * 255.9) for c in bgcolor])
        node_props = {"color": colorstr, "fillcolor": bgcolorstr}
        if style == "switch":
            node_props.update({"shape": "house", "orientation": 270.0})
        else:
            node_props.update({"shape": "box"})
        if use_nodes_pos:
            pos = pipeline.node_position.get(n)
            if pos is not None:
                node_props.update({"pos": "%f,%f" % (pos[0] * scale, -pos[1] * scale)})
        size = nodes_sizes.get(n)
        if size is not None:
            node_props.update(
                {
                    "width": (size[0] + enlarge_boxes) * scale,
                    "height": (size[1] + enlarge_boxes) * scale,
                    "fixedsize": "true",
                }
            )
        nodes.append((n, n, node_props))
    for n, v in graph._links:
        edge = (n, v)
        props = {"color": "#eb821e", "style": "solid"}
        edges[edge] = (props, True, False)

    return (nodes, edges)


def save_dot_graph(dot_graph, filename, **kwargs):
    """
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
    """

    def _str_repr(item):
        if isinstance(item, str):
            return '"%s"' % item
        return repr(item)

    fileobj = open(filename, "w")
    props = {"rankdir": "LR"}
    props.update(kwargs)
    propsstr = " ".join(
        ["=".join([aname, _str_repr(val)]) for aname, val in props.items()]
    )
    rankdir = props["rankdir"]

    fileobj.write("digraph {%s;\n" % propsstr)
    nodesep = 20.0  # in qt scale space
    scale = 1.0 / 67.0
    for id, node, props in dot_graph[0]:
        if rankdir == "TB" and "orientation" in props:
            props = dict(props)
            props["orientation"] -= 90
        attstr = " ".join(
            ["=".join([aname, _str_repr(val)]) for aname, val in props.items()]
        )
        if len(props) != 0:
            attstr = " " + attstr
        fileobj.write(f'  {id} [label="{node}" style="filled"{attstr}];\n')
    for edge, descr in dot_graph[1].items():
        props = descr[0]
        attstr = " ".join(
            ["=".join([aname, _str_repr(val)]) for aname, val in props.items()]
        )
        fileobj.write(f'  "{edge[0]}" -> "{edge[1]}" [{attstr}];\n')
    fileobj.write("}\n")


def save_dot_image(
    pipeline,
    filename,
    nodes_sizes=None,
    use_nodes_pos=False,
    include_io=True,
    enlarge_boxes=0.0,
    workflow=False,
    format=None,
    **kwargs,
):
    """
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
    """
    nodes_sizes = nodes_sizes or {}
    if workflow:
        dgraph = dot_graph_from_workflow(
            pipeline,
            nodes_sizes=nodes_sizes,
            use_nodes_pos=use_nodes_pos,
            enlarge_boxes=enlarge_boxes,
        )
    else:
        dgraph = dot_graph_from_pipeline(
            pipeline,
            nodes_sizes=nodes_sizes,
            use_nodes_pos=use_nodes_pos,
            include_io=include_io,
            enlarge_boxes=enlarge_boxes,
        )
    tempf = tempfile.mkstemp()
    os.close(tempf[0])
    dot_filename = tempf[1]
    save_dot_graph(dgraph, dot_filename, **kwargs)
    if format is None:
        ext = filename.split(".")[-1]
        formats = {"txt": "plain"}
        format = formats.get(ext, ext)
    cmd = ["dot", "-T%s" % ext, "-o", filename, dot_filename]
    soma.subprocess.check_call(cmd)
    os.unlink(dot_filename)


def disable_runtime_steps_with_existing_outputs(pipeline):
    """
    Disable steps in a pipeline which outputs contain existing files. This
    disabling is the "runtime steps disabling" one (see
    :py:class:`capsul.pipeline.Pipeline`), not the node disabling with
    activation propagation, so it doesn't affect the actual pipeline state.
    The aim is to prevent overwriting files which have already been processed,
    and to allow downstream execution of the remaining steps of the pipeline.

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        pipeline to disable nodes in.
    """
    steps = getattr(pipeline, "pipeline_steps", Controller())
    for field in steps.fields():
        step = field.name
        if not getattr(steps, step):
            continue  # already inactive
        for node_name in field.nodes:
            node = pipeline.nodes[node_name]
            if not node.enabled or not node.activated:
                continue  # node not active anyway
            process = node
            for param in node.plugs:
                pfield = process.field(param)
                if pfield.metadata().get("write", False) and pfield.is_path():
                    value = getattr(process, param, undefined)
                    if (
                        value is not None
                        and value is not undefined
                        and os.path.exists(value)
                    ):
                        # check special case when the output is also an input
                        # (of the same node)
                        disable = True
                        for t in process.fields():
                            n = t.name
                            if not t.metadata().get("write", False) and t.is_path():
                                v = getattr(process, n, undefined)
                                if v == value:
                                    disable = False
                                    break  # found in inputs
                        if disable:
                            # disable step
                            print(
                                "disable step",
                                step,
                                "because of:",
                                node_name,
                                ".",
                                param,
                            )
                            setattr(steps, step, False)
                            # no need to iterate other nodes in same step
                            break


def nodes_with_existing_outputs(
    pipeline, exclude_inactive=True, recursive=False, exclude_inputs=True
):
    """
    Checks nodes in a pipeline which outputs contain existing files on the
    filesystem. Such nodes, maybe, should not run again. Only nodes which
    actually produce outputs are selected this way (switches are skipped).

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        pipeline to disable nodes in.
    exclude_inactive: bool (optional)
        if this option is set, inactive nodes will not be checked
        nor returned in the list. Inactive means disabled, not active, or in a
        disabled runtime step.
        Default: True
    recursive: bool (optional)
        if this option is set, sub-pipelines will not be returned as a whole
        but will be parsed recursively to select individual leaf nodes.
        Default: False
    exclude_inputs: bool (optional, default: True)
        Some processes or pipelines have input/output files: files taken as
        inputs which are re-written as outputs, or may carry an input file to
        the outputs through a switch selection (in the case of preprocessing
        steps, for instance).
        If this option is set, such outputs which also appear in the same node
        inputs will not be listed in the existing outputs, so that they will
        not be erased by a cleaning operation, and will not prevent execution
        of these nodes.

    Returns
    -------
    selected_nodes: dict
        keys: node names
        values: list of pairs (param_name, file_name)
    """
    selected_nodes = {}
    if exclude_inactive:
        steps = getattr(pipeline, "pipeline_steps", Controller())
        disabled_nodes = set()
        for field in steps.fields():
            step = field.name
            if not getattr(steps, step, undefined):
                disabled_nodes.update(field.nodes)

    # nodes = pipeline.nodes.items()
    nodes = list(pipeline.nodes.items())
    while nodes:
        node_name, node = nodes.pop(0)
        if node_name == "" or not isinstance(node, Process):
            # main pipeline node, switch...
            continue
        if (
            not node.enabled
            or not node.activated
            or (exclude_inactive and node_name in disabled_nodes)
        ):
            continue
        process = node
        if recursive and isinstance(process, Pipeline):
            nodes += [
                (f"{node_name}.{new_name}", new_node)
                for new_name, new_node in process.nodes.items()
                if new_name != ""
            ]
            continue
        plug_list = []
        input_files_list = set()
        for plug_name, plug in node.plugs.items():
            field = process.field(plug_name)
            if field.is_path() or field.type is Any:
                value = getattr(process, plug_name, undefined)
                if (
                    isinstance(value, str)
                    and os.path.exists(value)
                    and value not in input_files_list
                ):
                    if plug.output:
                        plug_list.append((plug_name, value))
                    elif exclude_inputs:
                        input_files_list.add(value)
        if exclude_inputs:
            new_plug_list = [
                item for item in plug_list if item[1] not in input_files_list
            ]
            plug_list = new_plug_list
        if plug_list:
            selected_nodes[node_name] = plug_list
    return selected_nodes


def nodes_with_missing_inputs(pipeline, recursive=True):
    """
    Checks nodes in a pipeline which inputs contain invalid inputs.
    Inputs which are files non-existing on the filesystem (so, which cannot
    run), or have missing mandatory inputs, or take as input a temporary file
    which should be the output from another disabled node, are recorded.

    Parameters
    ----------
    pipeline: Pipeline (mandatory)
        pipeline to disable nodes in.
    recursive: bool (optional)
        if this option is set, sub-pipelines will not be returned as a whole
        but will be parsed recursively to select individual leaf nodes. Note
        that if not set, a pipeline is regarded as a process, but pipelines may
        not use all their inputs/outputs so the result might be inaccurate.
        Default: True

    Returns
    -------
    selected_nodes: dict
        keys: node names
        values: list of pairs (param_name, file_name)
    """
    selected_nodes = {}
    steps = getattr(pipeline, "pipeline_steps", Controller())
    disabled_nodes = set()
    for field in steps.fields():
        step = field.name
        if not getattr(steps, step, undefined):
            disabled_nodes.update(
                [pipeline.nodes[node_name] for node_name in field.nodes]
            )

    # nodes = pipeline.nodes.items()
    nodes = list(pipeline.nodes.items())
    while nodes:
        node_name, node = nodes.pop(0)
        if node_name == "" or not hasattr(node, "process"):
            # main pipeline node, switch...
            continue
        if not node.enabled or not node.activated or node in disabled_nodes:
            continue
        process = node.process
        if recursive and isinstance(process, Pipeline):
            nodes += [
                ("%s.%s" % (node_name, new_name), new_node)
                for new_name, new_node in process.nodes.items()
                if new_name != ""
            ]
            continue
        for plug_name, plug in node.plugs.items():
            if not plug.output:
                if process.field(plug_name).is_path():
                    value = getattr(process, plug_name, undefined)
                    keep_me = False
                    if value in (None, undefined, "") or not os.path.exists(value):
                        # check where this file comes from
                        (
                            origin_node,
                            origin_param,
                            origin_parent,
                        ) = where_is_plug_value_from(plug, recursive)
                        if origin_node is not None and (
                            origin_node in disabled_nodes
                            or origin_parent in disabled_nodes
                        ):
                            # file coming from another disabled node
                            # if not value or value is undefined:
                            ## temporary one
                            # print('TEMP: %s.%s' % (node_name, plug_name))
                            # value = None
                            keep_me = True
                        elif origin_node is None:
                            # unplugged: does not come from anywhere else
                            if value or not plug.optional:
                                # non-empty value, non-existing file
                                # or mandatory, empty value
                                keep_me = True
                        # the rest is a plugged input from another process,
                        # or an optional empty value
                    if keep_me:
                        plug_list = selected_nodes.setdefault(node_name, [])
                        plug_list.append((plug_name, value))
    return selected_nodes


def where_is_plug_value_from(plug, recursive=True):
    """
    Find where the given (input) plug takes its value from.
    It has to be the output of an uphill process, or be unconnected.
    Looking for it may involve ascending through switches or pipeline walls.

    Parameters
    ----------
    plug: Plug instance (mandatory)
        the plug to find source connection with
    recursive: bool (optional)
        if this option is set, sub-pipelines will not be returned as a whole
        but will be parsed recursively to select individual leaf nodes. Note
        that if not set, a pipeline is regarded as a process, but pipelines may
        not use all their inputs/outputs so the result might be inaccurate.
        Default: True

    Returns
    -------
    node: Node
        origin pipeline node. May be None if the plug was not connected to an
        active source.
    param_name: string
        origin plug name in the origin node. May be None if node is None
    parent: Node
        Top-level parent node of the origin node. Useful to determine if the
        origin node is in a runtime pipeline step, which only records top-level
        nodes.
    """
    links = [link + (None,) for link in plug.links_from]
    while links:
        node_name, param_name, node, in_plug, weak, parent = links.pop(0)
        if not node.activated or not node.enabled:
            # disabled nodes are not influencing
            continue
        if isinstance(node, Pipeline):
            if not recursive:
                return node, param_name, parent
            else:  # recursive
                # either output from a sibling sub_pipeline
                # or input from parent pipeline
                # but it is handled the same way.
                # check their inputs
                # just if sibling, keep them as parent
                if in_plug.output and parent is None:
                    new_parent = node
                else:
                    new_parent = parent
                links += [link + (new_parent,) for link in in_plug.links_from]
        else:
            other_end = node.get_connections_through(param_name, single=True)
            if other_end:
                return other_end[0][0], other_end[0][1], parent
    # not found
    return None, None, None


def find_plug_connection_sources(plug, pipeline=None):
    """
    A bit like :func:`where_is_plug_value_from` but looks for all incoming
    connection sources

    Returns
    -------
    sources:  list
        [(node, param_name, parent_node), ...]
    """
    sources = []
    links = [link + (pipeline,) for link in plug.links_from]
    while links:
        node_name, param_name, node, in_plug, weak, parent = links.pop(0)
        if not node.activated or not node.enabled:
            # disabled nodes are not influencing
            continue
        if isinstance(node, Pipeline):
            if not in_plug.links_from:
                # get out of the pipeline: keep it
                sources.append((node, param_name, parent))
                continue
            # either output from a sibling sub_pipeline
            # or input from parent pipeline
            # but it is handled the same way.
            # check their inputs
            # just if sibling, keep them as parent
            if in_plug.output and parent in (None, pipeline):
                new_parent = node
            else:
                new_parent = parent
            links += [link + (new_parent,) for link in in_plug.links_from]
        else:
            other_end = node.get_connections_through(param_name, single=False)
            for src in other_end:
                if not src[2].output and node is pipeline and not src[2].links_from:
                    # main pipeline input, keep it
                    sources.append((src[0], src[1], node))
                elif src[2] is in_plug:
                    # don't get through its node: keep the node as source
                    sources.append((src[0], src[1], node))
                elif src[2].output and not isinstance(src[0], Pipeline):
                    # sub-pipeline output: inspect it
                    links.append((None, src[1], src[0], src[2], False, node))
                elif not src[2].output or isinstance(src[0], Pipeline):
                    # input side of a non-opaque node: inspect its links
                    links += [link + (node,) for link in src[2].links_from]
                else:
                    print("unhandle case in find_plug_connection_sources")
                    print("node:", src[0], ", param:", src[1])

    return sources


def find_plug_connection_destinations(plug, pipeline=None):
    """
    A bit like :func:`find_plug_connection_sources` but the other way

    Returns
    -------
    dest:  list
        [(node, param_name, parent_node), ...]
    """
    dest = []
    links = [link + (pipeline,) for link in plug.links_to]
    while links:
        node_name, param_name, node, in_plug, weak, parent = links.pop(0)
        if not node.activated or not node.enabled:
            # disabled nodes are not influencing
            continue
        if isinstance(node, Pipeline):
            if not in_plug.links_to:
                # get out of the pipeline: keep it
                dest.append((node, param_name, parent))
                continue
            # either input from a sibling sub_pipeline
            # or output from parent pipeline
            # but it is handled the same way.
            # check their inputs
            # just if sibling, keep them as parent
            if not in_plug.output and parent in (None, pipeline):
                new_parent = node
            else:
                new_parent = parent
            links += [link + (new_parent,) for link in in_plug.links_to]
        else:
            other_end = node.get_connections_through(param_name, single=False)
            for dst in other_end:
                if dst[2].output and node is pipeline and not dst[2].links_to:
                    # main pipeline output, keep it
                    dest.append((dst[0], dst[1], node))
                elif dst[2] is in_plug:
                    # don't get through its node: keep the node as dest
                    dest.append((dst[0], dst[1], node))
                elif not dst[2].output and not isinstance(dst[0], Pipeline):
                    # sub-pipeline input: inspect it
                    links.append((None, dst[1], dst[0], dst[2], False, node))
                elif dst[2].output or isinstance(dst[0], Pipeline):
                    # output side of a non-opaque node: inspect its links
                    links += [link + (node,) for link in dst[2].links_to]
                else:
                    print("unhandle case in find_plug_connection_sources")
                    print("node:", dst[0], ", param:", dst[1])

    return dest


def dump_pipeline_state_as_dict(pipeline):
    """
    Get a pipeline state (parameters values, nodes activation, selected
    steps... in a dictionary.

    The returned dict may contain sub-pipelines state also.

    The dict may be saved, and used to restore a pipeline state, using
    :py:func:`set_pipeline_state_from_dict`.

    Note that :py:meth:`pipeline.asdict <soma.controller.controller.Controller.asdict>`
    would almost do the job, but does not include the recursive aspect.

    Parameters
    ----------
    pipeline: Pipeline (or Process) instance
        pipeline (or process) to get state from

    Returns
    -------
    state_dict: dict
        pipeline state
    """

    def should_keep_value(node, plug, components):
        """
        Tells if a plug has already been taken into account in the plugs graph.

        Also filters out switches outputs, which should rather be set via their
        inputs.

        To do so, a connected components map has to be built for the plugs
        graph, which is done is a semi-lazy way in components.

        Parameters
        ----------
        node: Node
            pipeline node the pluge belongs to
        plug: Plug
            the plug to test
        components: list of sets of plugs
            connected components will be added to this components list.

        Returns
        -------
        True if the plug value is a "new" one and should be recorded in the
        pipeline state. Otherwise it should be discarded (set from another
        connected plug).
        """

        def _component(plug, components):
            for comp in components:
                if plug in comp:
                    return comp
            return None

        comp = _component(plug, components)
        if comp:
            # already done
            return False
        comp = set()
        todo = []
        todo.append(plug)
        allowed = True
        # propagate
        while todo:
            plug = todo.pop(0)
            comp.add(plug)
            # switches outputs should not be set (they will be through their
            # inputs)
            if plug.output and isinstance(node, Switch):
                allowed = False
            todo += [link[3] for link in plug.links_from if link[3] not in comp]
            todo += [link[3] for link in plug.links_to if link[3] not in comp]
        components.append(comp)
        return allowed

    def prune_empty_dicts(state_dict):
        """
        Remove empty dictionaries, and nodes containing empty dicts in pipeline
        state dictionary

        Parameters
        ----------
        state_dict: dict
            the state_dict is parsed, and modified.
        """
        if state_dict.get("nodes") is None:
            return
        todo = [(state_dict, None, None, True)]
        while todo:
            current_dict, parent, parent_key, recursive = todo.pop(0)
            nodes = current_dict.get("nodes")
            modified = False
            if nodes:
                if len(nodes) == 0:
                    del current_dict["nodes"]
                    modified = True
                elif recursive:
                    todo = [
                        (value, nodes, key, True) for key, value in nodes.items()
                    ] + todo
                    modified = True
            if len(current_dict) == 0 and parent is not None:
                del parent[parent_key]
            elif modified:
                todo.append((current_dict, parent, parent_key, False))

    state_dict = {}
    nodes = [(None, pipeline, state_dict)]
    components = []
    while nodes:
        node_name, node, current_dict = nodes.pop(0)
        proc = node
        node_dict = proc.asdict()
        # filter out forbidden and already used plugs
        for plug_name, plug in node.plugs.items():
            if plug_name in node_dict and not should_keep_value(node, plug, components):
                del node_dict[plug_name]
        if node_name is None:
            if len(node_dict) != 0:
                current_dict["state"] = node_dict
            child_dict = current_dict
        else:
            child_dict = {}
            current_dict.setdefault("nodes", {})[node_name] = child_dict
            if len(node_dict) != 0:
                child_dict["state"] = node_dict
        if hasattr(proc, "nodes"):
            nodes += [
                (child_node_name, child_node, child_dict)
                for child_node_name, child_node in proc.nodes.items()
                if child_node_name != ""
            ]

    prune_empty_dicts(state_dict)
    return state_dict


def set_pipeline_state_from_dict(pipeline, state_dict):
    """
    Set a pipeline (or process) state from a dict description.

    State includes parameters values, nodes activation, steps selection etc.
    The state is generally taken using :py:func:`dump_pipeline_state_as_dict`.

    Parameters
    ----------
    pipeline: Pipeline or Process instance
        process to set state in
    state_dict: dict (mapping object)
        state dictionary
    """
    nodes = [(pipeline, state_dict)]
    while nodes:
        node, current_dict = nodes.pop(0)
        proc = node
        proc.import_dict(current_dict.get("state", {}))
        sub_nodes = current_dict.get("nodes")
        if sub_nodes:
            nodes += [
                (proc.nodes[node_name], sub_dict)
                for node_name, sub_dict in sub_nodes.items()
            ]


def save_pipeline(pipeline, filename):
    """
    Save the pipeline either in JSON or .py source file
    """
    from capsul.pipeline.python_export import save_py_pipeline

    formats = {".py": save_py_pipeline, ".json": save_json_pipeline}

    saved = False
    for ext, writer in formats.items():
        if filename.endswith(ext):
            writer(pipeline, filename)
            saved = True
            break
    if not saved:
        # fallback to py
        save_py_pipeline(pipeline, filename)


def save_json_pipeline(pipeline, filename):
    json_def = pipeline.json()
    if hasattr(filename, "write"):
        json.dump(json_def, filename)
    else:
        with open(filename, "w") as f:
            json.dump(json_def, f)


def load_pipeline_parameters(filename, pipeline):
    """
    Loading and setting pipeline parameters (inputs and outputs) from a Json file.
    """

    if filename:
        with open(filename, "r", encoding="utf8") as file:
            dic = json.load(file)

        if "pipeline_parameters" not in dic:
            raise KeyError(f'No "pipeline_parameters" key found in {filename}.')

        pipeline.import_json(json_decode(dic["pipeline_parameters"]))
        pipeline.update_nodes_and_plugs_activation()


def save_pipeline_parameters(filename, pipeline):
    """
    Saving pipeline parameters (inputs and outputs) to a Json file.
    """

    if filename:
        # Generating the dictionary
        param_dic = json_encode(pipeline.json()["parameters"])

        # In the future, more information may be added to this dictionary
        dic = {}
        dic["pipeline_parameters"] = param_dic

        # Saving the dictionary in the Json file
        with open(filename, "w", encoding="utf8") as file:
            json.dump(dic, file)


def find_node(pipeline, node):
    """Find the given node in the pipeline or a sub-pipeline

    Returns
    -------
    node_chain: list
        list of node names in the pipeline going through sub-pipelines to the
        given node
    """
    nodes = []
    pipelines = [(pipeline, [])]
    while pipelines:
        n, names = pipelines.pop(0)
        for sk, sn in n.nodes.items():
            if node is sn:
                return names + [sk]
            if sn is not n and isinstance(sn, Pipeline):
                pipelines.append((sn, names + [sk]))

    raise KeyError("Node %s not found in the pipeline %s" % (node.name, pipeline.name))


def nodes_full_names(executable):
    # build node -> full name map
    todo = [("", executable)]
    node_names = {}
    while todo:
        name, node = todo.pop(0)
        node_names[node] = name
        prefix = f"{name}." if name else ""
        if isinstance(node, Pipeline):
            todo += [
                (f"{prefix}{nn}", n) for nn, n in node.nodes.items() if n is not node
            ]
        elif isinstance(node, ProcessIteration):
            todo.append((f"{prefix}{node.process.name}", node.process))
    return node_names


def is_node_enabled(pipeline, node_name=None, node=None):
    """Checks if the given node is enabled in the pipeline.
    It may be disabled if it has its ``enabled`` or ``activated`` properties set to False, or if it is part of a disabled step.
    The node may be given as a Node instance, or its name in the pipeline.
    """
    names = [node_name]
    if node is None:
        node = pipeline.nodes[node_name]

    if not node.enabled or not node.activated:
        return False

    elif node_name is None:
        # probably a node of a sub-pipeline
        names = find_node(pipeline, node)

    p = pipeline
    for name in names:
        steps = getattr(p, "pipeline_steps", Controller())
        for field in steps.fields():
            step = field.name
            if not getattr(steps, step, undefined) and name in field.nodes:
                return False
        p = p.nodes[name]

    # not disabled ? OK then it's enabled
    return True


def write_fake_process(process, filename, sleep_time=0):
    """Write a "fake process" with same class name and parameters as the input
    process, but with a fake execution function meant for tests.
    """

    auto_fields = {"activated", "enabled", "node_type"}
    meta_forbidden = {"order", "path_type", "class_field"}

    with open(filename, "w") as f:
        f.write(
            """from capsul.api import Process
import os
from soma.controller import File, Directory, undefined, Literal
"""
        )

        imports = set()
        for field in process.fields():
            name = field.name
            if name in auto_fields:
                continue

            t_str = field.type_str()
            t_str = t_str.split("[", 1)[0]
            t_str = t_str.split("(", 1)[0]
            if "." in t_str:
                imp_str = t_str.rsplit(".", 1)[0]
                if imp_str not in imports:
                    imports.add(imp_str)
                    # hack for pydantic v2: use v1
                    if imp_str == "pydantic":
                        f.write(
                            "try:\n"
                            "    import pydantic.v1 as pydantic\n"
                            "except ImportError:\n"
                            "    import pydantic\n"
                        )
                    else:
                        f.write("import %s\n" % imp_str)

        f.write(
            """

class %s(Process):
    def __init__(self, **kwargs):
        super(%s, self).__init__(**kwargs)
        self.name = '%s'

"""
            % (process.__class__.__name__, process.__class__.__name__, process.name)
        )

        for field in process.fields():
            name = field.name
            if name in auto_fields:
                continue

            t_str = field.type_str()
            meta = {
                k: v for k, v in field.metadata().items() if k not in meta_forbidden
            }
            has_default = False
            if field.default not in (undefined, dataclasses.MISSING):
                meta["default"] = field.default
                has_default = True
            elif field.default_factory != dataclasses.MISSING:
                # difficult/implssible to replicate...
                class def_fac:
                    def __init__(self, value):
                        self.value = value

                    def __repr__(self):
                        return "lambda: %s" % repr(self.value)

                meta["default_factory"] = def_fac(field.default_factory())
                has_default = True
            value = getattr(process, name, undefined)
            if has_default and "optional" not in meta:
                meta["optional"] = True
            meta_str = ""
            if meta:
                meta_str = ", ".join(f"{k}={v!r}" for k, v in meta.items())
                meta_str = ", " + meta_str
            f.write(f'        self.add_field("{name}", {t_str}{meta_str})\n')
            if value is not undefined:
                f.write(f"        self.{name} = {value!r}\n")

        f.write(
            """
    def execute(self, context):
        outputs = []
        for field in self.fields():
            name = field.name
            if isinstance(field.type, File):
                if field.write:
                    outputs.append(name)
                    continue
                filename = getattr(self, name, undefined)
                if filename not in (None, undefined, ''):
                    if not os.path.exists(filename):
                        raise ValueError(
                          'Input parameter: %s, file %s does not exist'
                          % (name, repr(filename)))

"""
        )
        if sleep_time != 0:
            f.write("        import time\n")
            f.write("        time.sleep(%f)\n\n" % sleep_time)
        f.write(
            """        for name in outputs:
            field = self.field(name)
            filename = getattr(self, name, undefined)
            if filename not in (None, undefined, ''):
                with open(filename, 'w') as f:
                    f.write('class: %s\\n' % self.__class__.__name__)
                    f.write('name: %s\\n' % self.name)
                    f.write('parameter: %s\\n' % name)
"""
        )


def write_fake_pipeline(pipeline, module_name, dirname, sleep_time=0):
    """Write a "fake pipeline" with same class name, structure, and parameters
    as the input pipeline, but replacing its processes with "fake" processes
    which do not actually do a real job while executing.

    This is meant for tests, to mimic a "real" pipeline structure without its
    dependencies.

    :warning:`This function actually modifies the input pipeline, which is
    transformed into a fake one.`
    """

    meta_forbidden = {"order", "path_type", "class_field"}

    def replace_pipeline_node(old_node, new_node, parent):
        for plug_name, plug in old_node.plugs.items():
            for link in plug.links_from:
                new_plug = new_node.plugs[plug_name]
                new_plug.links_from.add(link)
                for olink in set(link[3].links_to):
                    if olink[3] is plug:
                        nolink = (olink[0], olink[1], new_node, new_plug, olink[4])
                        link[3].links_to.remove(olink)
                        link[3].links_to.add(nolink)
            for link in plug.links_to:
                new_plug = new_node.plugs[plug_name]
                new_plug.links_to.add(link)
                for olink in set(link[3].links_from):
                    if olink[3] is plug:
                        nolink = (olink[0], olink[1], new_node, new_plug, olink[4])
                        link[3].links_from.remove(olink)
                        link[3].links_from.add(nolink)

    def replace_node(node, module_name, dirname, done, parent, node_name):
        basename = node.__class__.__name__.lower()
        modname = ".".join([module_name, basename])
        filename = os.path.join(dirname, "%s.py" % basename)
        if modname not in done:
            done.add(modname)
            write_fake_process(node, filename, sleep_time=sleep_time)
        try:
            new_proc = executable(filename)
        except Exception:
            print("Failed to reload node:", filename)
            raise
        new_proc.__class__.__module__ = modname

        # fix fields state (if modified)
        for field in node.fields():
            name = field.name
            new_field = new_proc.field(name)
            if new_field is None:
                new_proc.add_field(name, field)
                continue
            meta = {
                k: v for k, v in field.metadata().items() if k not in meta_forbidden
            }
            meta.update(
                {
                    k: getattr(field, k)
                    for k in new_field.metadata()
                    if k not in meta and hasattr(field, k)
                }
            )
            for k, v in meta.items():
                setattr(new_proc.field(name), k, v)
            # set back old value
            setattr(new_proc, name, getattr(node, name, undefined))

        if parent is not None and node_name is not None:
            parent.nodes[node_name] = new_proc
            replace_pipeline_node(node, new_proc, parent)

        return new_proc

    sys.path.insert(0, dirname)
    dirname = os.path.join(dirname, module_name.rsplit(".")[-1])
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(os.path.join(dirname, "__init__.py"), "w"):
        pass

    nodes = [
        (pipeline, node[0], node[1]) for node in pipeline.nodes.items() if node[0] != ""
    ]
    done = set()
    pipelines = [pipeline]
    while nodes:
        parent, node_name, node = nodes.pop(0)
        if not isinstance(node, Process):
            continue
        if isinstance(node, Pipeline):
            if node.__class__ not in done:
                nodes += [(node, n[0], n[1]) for n in node.nodes.items() if n[0] != ""]
                node.__class__.__module__ = ".".join(
                    [module_name, node.__class__.__name__.lower()]
                )
                done.add(node.__class__)
                pipelines.append(node)
        elif isinstance(node, ProcessIteration):
            proc = node.process
            if isinstance(proc, Pipeline):
                nodes += [(proc, n[0], n[1]) for n in proc.nodes.items() if n[0] != ""]
            else:
                new_node = replace_node(proc, module_name, dirname, done, None, None)
                node.process = new_node
        else:
            replace_node(node, module_name, dirname, done, parent, node_name)

    for pipeline in reversed(pipelines):
        filename = os.path.join(dirname, "%s.py" % pipeline.__class__.__name__.lower())
        save_pipeline(pipeline, filename)

    del sys.path[0]


def topological_sort_nodes(nodes):
    """Sort nodes topologically according to their links.
    All linked nodes must be in the nodes list: if switched or pipelines are
    removed, the sort will be broken.

    In the output list, pipeline nodes will appear twice, in tuples:

    (pipeline, 0) is the position of the input plugs of the pipeline

    (pipeline, 1) is the position of the output plugs of the pipeline

    nodes inside the pipeline will logically be between both.
    """
    nsort = []
    done = set()
    todo = list(nodes)
    while todo:
        node = todo.pop(0)
        if node in done:
            continue

        i = -1
        cont = False
        for plug in node.plugs.values():
            if not plug.output:
                for ld in plug.links_from:
                    n = ld[2]
                    n0 = n
                    if isinstance(n, Pipeline):
                        if not ld[3].output:
                            n = (n, 0)  # begin of pipeline
                        else:
                            n = (n, 1)  # end of pipeline
                    if n in done:
                        ni = nsort.index(n)  # WARNING: expensive search
                        if ni > i:
                            i = ni
                    else:
                        todo.insert(0, n0)
                        cont = True
                        break
                if cont:
                    break
        if cont:
            continue

        # print('insert', node.full_name, ':', i+1)
        # if i >= 0:
        # print('    after', nsort[i].full_name if not isinstance(nsort[i], tuple) else (nsort[i][0].full_name, nsort[i][1]) )
        if isinstance(node, Pipeline):
            nsort.insert(i + 1, (node, 0))
            nsort.insert(i + 2, (node, 1))
            done.add((node, 0))
            done.add((node, 1))
        else:
            nsort.insert(i + 1, node)
        done.add(node)
    return nsort


def propagate_meta(executable, nodes=None):
    """Propagate metadata from processes output plugs to downstream
    switches and upper level pipelines plugs, recursively in topological order.

    If ``nodes`` is provided, it should be the nodes list already in
    topological order. It may be passed if reused in order to avoid
    calling :func:`topological_sort_nodes` several times.
    """
    if isinstance(executable, ProcessIteration):
        if isinstance(executable.process, Pipeline):
            propagate_meta(executable.process)
        for pname in executable.iterative_parameters:
            f = executable.process.field(pname)
            fo = executable.field(pname)
            # copy field metadata
            for k, v in f.metadata().items():
                setattr(fo, k, v)
        return

    if nodes is None:
        nodes = topological_sort_nodes(executable.all_nodes())
    for node in nodes:
        if isinstance(node, Switch):
            node.propagate_fields_metadata()
        if isinstance(node, tuple):
            if node[1] == 0:
                # pipeline inputs
                continue
            node = node[0]
        if isinstance(node, ProcessIteration):
            propagate_meta(node)
        for pname, plug in node.plugs.items():
            if plug.output:
                f = node.field(pname)
                for ld in plug.links_to:
                    n = ld[2]
                    p = ld[1]
                    fo = n.field(p)
                    if fo.is_output():
                        # copy field metadata
                        for k, v in f.metadata().items():
                            setattr(fo, k, v)
