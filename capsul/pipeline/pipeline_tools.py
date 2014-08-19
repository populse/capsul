##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
try:
    from traits import api as traits
except ImportError:
    from enthought.traits import api as traits
from capsul.pipeline import Pipeline, PipelineNode

def disable_node_for_downhill_pipeline(pipeline, node_name):
    '''
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
        # disable nodes first, so that those nodes will not have exported inputs
        setattr(pipeline.nodes_activation, node_name, False)
    # then export downhill inputs
    for node_name in disabled_nodes:
        disable_node_for_downhill_pipeline(pipeline, node_name)
    for sub_pipeline in sub_pipelines:
        disable_nodes_with_existing_outputs(sub_pipeline)


def reactivate_pipeline(pipeline):
    '''
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

