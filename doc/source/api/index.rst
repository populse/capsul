:orphan:

.. _capsul_ref:

====================================
CAPSUL programming API documentation
====================================

See also the :ref:`capsul_guide` section for more general usage documentation.

Classes inheritance diagram
===========================

.. .. inheritance-diagram:: capsul.engine capsul.engine.database_json capsul.engine.database_populse capsul.engine.database capsul.engine.module capsul.in_context capsul.in_context.fsl capsul.pipeline capsul.pipeline.pipeline capsul.pipeline.pipeline_construction capsul.pipeline.pipeline_nodes capsul.pipeline.pipeline_tools capsul.pipeline.pipeline_workflow capsul.pipeline.process_iteration capsul.pipeline.python_export capsul.pipeline.topological_sort capsul.pipeline.xml capsul.pipeline.custom_nodes capsul.pipeline.custom_nodes.strcat_node capsul.pipeline.custom_nodes.cv_node capsul.pipeline.custom_nodes.loo_node capsul.pipeline.custom_nodes.map_node capsul.pipeline.custom_nodes.reduce_node capsul.plugins capsul.process capsul.process.process capsul.process.nipype_process capsul.process.runprocess capsul.qt_apps capsul.qt_apps.utils capsul.qt_apps.utils.application capsul.qt_apps.utils.fill_treectrl capsul.qt_apps.utils.find_pipelines capsul.qt_apps.utils.window capsul.qt_gui capsul.qt_gui.board_widget capsul.qt_gui.widgets capsul.qt_gui.widgets.activation_inspector capsul.qt_gui.widgets.attributed_process_widget capsul.qt_gui.widgets.links_debugger capsul.qt_gui.widgets.pipeline_developer_view capsul.qt_gui.widgets.pipeline_file_warning_widget capsul.qt_gui.widgets.pipeline_user_view capsul.qt_gui.widgets.viewer_widget capsul.sphinxext capsul.sphinxext.layoutdocgen capsul.sphinxext.load_pilots capsul.sphinxext.pipelinedocgen capsul.sphinxext.usecasesdocgen

.. .. inheritance-diagram:: capsul.application capsul.dataset capsul.engine capsul.pipeline capsul.pipeline.pipeline capsul.pipeline.pipeline_nodes capsul.pipeline.pipeline_tools capsul.pipeline.pipeline_workflow capsul.pipeline.process_iteration capsul.pipeline.python_export capsul.pipeline.custom_nodes capsul.pipeline.custom_nodes.strcat_node capsul.pipeline.custom_nodes.cv_node capsul.pipeline.custom_nodes.loo_node capsul.pipeline.custom_nodes.map_node capsul.pipeline.custom_nodes.reduce_node capsul.process capsul.process.node capsul.process.process capsul.process.nipype_process capsul.qt_apps capsul.qt_apps.utils capsul.qt_apps.utils.application capsul.qt_apps.utils.fill_treectrl capsul.qt_apps.utils.find_pipelines capsul.qt_apps.utils.window capsul.qt_gui capsul.qt_gui.board_widget capsul.qt_gui.widgets capsul.qt_gui.widgets.activation_inspector capsul.qt_gui.widgets.attributed_process_widget capsul.qt_gui.widgets.links_debugger capsul.qt_gui.widgets.pipeline_developer_view capsul.qt_gui.widgets.pipeline_file_warning_widget capsul.qt_gui.widgets.pipeline_user_view capsul.qt_gui.widgets.settings_editor capsul.qt_gui.widgets.viewer_widget capsul.sphinxext capsul.sphinxext.layoutdocgen capsul.sphinxext.load_pilots capsul.sphinxext.pipelinedocgen capsul.sphinxext.usecasesdocgen capsul.subprocess capsul.subprocess.fsl capsul.subprocess.spm capsul.utils capsul.utils.finder capsul.utils.version_utils

.. inheritance-diagram:: capsul.application capsul.dataset capsul.engine capsul.pipeline capsul.pipeline.pipeline capsul.pipeline.pipeline_nodes capsul.pipeline.pipeline_tools capsul.pipeline.pipeline_workflow capsul.pipeline.process_iteration capsul.pipeline.python_export capsul.pipeline.custom_nodes capsul.pipeline.custom_nodes.strcat_node capsul.pipeline.custom_nodes.cv_node capsul.pipeline.custom_nodes.loo_node capsul.pipeline.custom_nodes.map_node capsul.pipeline.custom_nodes.reduce_node capsul.process capsul.process.node capsul.process.process capsul.process.nipype_process capsul.qt_gui capsul.qt_gui.widgets capsul.qt_gui.widgets.activation_inspector capsul.qt_gui.widgets.attributed_process_widget capsul.qt_gui.widgets.links_debugger capsul.qt_gui.widgets.pipeline_developer_view capsul.qt_gui.widgets.pipeline_file_warning_widget capsul.qt_gui.widgets.pipeline_user_view capsul.qt_gui.widgets.settings_editor capsul.subprocess capsul.utils capsul.utils.finder capsul.utils.version_utils
    :parts: 1

.. capsul.qt_apps.main_window capsul.qt_apps.pipeline_viewer_app

Main classes and functions
==========================

:mod:`capsul.application`: Application: configuration and execution
===================================================================

* :class:`~capsul.application.Capsul`
* :class:`~capsul.engine.Engine`


:mod:`capsul.config`: Configuration
===================================


:mod:`capsul.pipeline`: Pipeline
=================================

.. currentmodule:: capsul.pipeline

Pipeline Definition
-------------------

* :class:`~pipeline.Pipeline`

Node Types
----------

.. currentmodule:: capsul.pipeline

* :class:`~capsul.process.node.Node`
* :class:`~pipeline_nodes.Switch`

* :mod:`Custom nodes types <capsul.pipeline.custom_nodes>`

Plug
-----

* :class:`~capsul.process.node.Plug`


:mod:`capsul.process`: Process
===============================

.. currentmodule:: capsul.process.process

Classes
-------

* :class:`Process`
* :class:`NipypeProcess`
* :class:`FileCopyProcess`


:mod:`capsul.database`: Engine database
=======================================


:mod:`capsul.dataset`: Datasets definition for path completion
==============================================================

.. currentmodule:: capsul.dataset

Classes
-------

* :class:`Dataset`
* :class:`PathLayout`
* :class:`BIDSLayout`
* :class:`BrainVISALayout`


Pipeline tools
==============

.. currentmodule:: capsul.pipeline.pipeline_tools

* :func:`dot_graph_from_pipeline`
* :func:`save_dot_graph`
* :func:`save_dot_image`
* :func:`nodes_with_existing_outputs`
* :func:`nodes_with_missing_inputs`
* :func:`disable_runtime_steps_with_existing_outputs`
* :func:`where_is_plug_value_from`


GUI
===

Graphical widgets classes

.. _capsul_gui_ref:

:mod:`capsul.qt_gui.widgets`: Pipeline Viewers
----------------------------------------------

.. currentmodule:: capsul.qt_gui.widgets

* :class:`~pipeline_developer_view.PipelineDeveloperView`
* :class:`~pipeline_user_view.PipelineUserView`
* :class:`~attributed_process_widget.AttributedProcessWidget`


Graphical pipeline debugging tools
----------------------------------

* :class:`~activation_inspector.ActivationInspector`
* :class:`~links_debugger.CapsulLinkDebuggerView`


Complete modules list
=====================

.. toctree::
    :maxdepth: 1

    api
    application
    config
    database
    debug
    execution_context
    info
    process
    pipeline
    engine
    dataset
    qt_apps
    qt_gui
    schemas
    sphinxext
    ui
