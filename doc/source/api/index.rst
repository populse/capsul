:orphan:

.. _capsul_ref:

====================================
CAPSUL programming API documentation
====================================

See also the :ref:`capsul_guide` section for more general usage documentation.

Classes inheritance diagram
===========================

.. inheritance-diagram:: capsul.attributes capsul.attributes.attributes_factory capsul.attributes.attributes_schema capsul.attributes.completion_engine_factory capsul.attributes.completion_engine_iteration capsul.attributes.completion_engine capsul.attributes.fom_completion_engine capsul.engine capsul.engine.database_json capsul.engine.database_populse capsul.engine.database capsul.engine.module capsul.in_context capsul.in_context.fsl capsul.pipeline capsul.pipeline.pipeline capsul.pipeline.pipeline_construction capsul.pipeline.pipeline_nodes capsul.pipeline.pipeline_tools capsul.pipeline.pipeline_workflow capsul.pipeline.process_iteration capsul.pipeline.python_export capsul.pipeline.topological_sort capsul.pipeline.xml capsul.pipeline.custom_nodes capsul.pipeline.custom_nodes.strcat_node capsul.pipeline.custom_nodes.cv_node capsul.pipeline.custom_nodes.loo_node capsul.pipeline.custom_nodes.map_node capsul.pipeline.custom_nodes.reduce_node capsul.plugins capsul.process capsul.process.process capsul.process.nipype_process capsul.process.runprocess capsul.process.xml capsul.qt_apps capsul.qt_apps.utils capsul.qt_apps.utils.application capsul.qt_apps.utils.fill_treectrl capsul.qt_apps.utils.find_pipelines capsul.qt_apps.utils.window capsul.qt_gui capsul.qt_gui.board_widget capsul.qt_gui.widgets capsul.qt_gui.widgets.activation_inspector capsul.qt_gui.widgets.attributed_process_widget capsul.qt_gui.widgets.links_debugger capsul.qt_gui.widgets.pipeline_developer_view capsul.qt_gui.widgets.pipeline_file_warning_widget capsul.qt_gui.widgets.pipeline_user_view capsul.qt_gui.widgets.viewer_widget capsul.sphinxext capsul.sphinxext.layoutdocgen capsul.sphinxext.load_pilots capsul.sphinxext.pipelinedocgen capsul.sphinxext.usecasesdocgen capsul.study_config capsul.study_config.study_config capsul.study_config.config_utils capsul.study_config.memory capsul.study_config.process_instance capsul.study_config.run capsul.study_config.config_modules.attributes_config capsul.study_config.config_modules.brainvisa_config capsul.study_config.config_modules.fom_config capsul.study_config.config_modules.freesurfer_config capsul.study_config.config_modules.fsl_config capsul.study_config.config_modules.matlab_config capsul.study_config.config_modules.nipype_config capsul.study_config.config_modules.smartcaching_config capsul.study_config.config_modules.somaworkflow_config capsul.study_config.config_modules.spm_config capsul.subprocess capsul.subprocess.fsl capsul.subprocess.spm capsul.utils capsul.utils.finder capsul.utils.version_utils
    :parts: 1

.. capsul.qt_apps.main_window capsul.qt_apps.pipeline_viewer_app

Main classes and functions
==========================

:mod:`capsul.pipeline`: Pipeline
=================================

.. currentmodule:: capsul.pipeline

Pipeline Definition
-------------------

* :class:`~pipeline.Pipeline`

Node Types
----------

.. currentmodule:: capsul.pipeline.pipeline_nodes

* :class:`Node`
* :class:`ProcessNode`
* :class:`PipelineNode`
* :class:`Switch`

* :mod:`Custom nodes types <capsul.pipeline.custom_nodes>`

Plug
-----

* :class:`Plug`


:mod:`capsul.process`: Process
===============================

.. currentmodule:: capsul.process.process

Classes
-------

* :class:`Process`
* :class:`NipypeProcess`
* :class:`FileCopyProcess`


Functions
---------

.. currentmodule:: capsul.study_config.process_instance

* :func:`get_process_instance`


Configuration and execution
===========================

:mod:`capsul.engine`: Configuration and execution
-------------------------------------------------

This new system will replace :mod:`capsul.study_config` in Capsul v3.

.. currentmodule:: capsul.engine

Classes:
++++++++

* :class:`CapsulEngine`


Functions:
++++++++++

* :func:`capsul_engine`


:mod:`capsul.study_config`: Study Configuration
-----------------------------------------------

.. currentmodule:: capsul.study_config

Study Configuration:
++++++++++++++++++++

* :class:`~study_config.StudyConfig`
* :class:`~memory.Memory`


Configuration Modules:
++++++++++++++++++++++

.. currentmodule:: capsul.study_config.config_modules

* :class:`somaworkflow_config.SomaWorkflowConfig`
* :class:`matlab_config.MatlabConfig`
* :class:`spm_config.SPMConfig`
* :class:`fsl_config.FSLConfig`
* :class:`freesurfer_config.FreeSurferConfig`
* :class:`nipype_config.NipypeConfig`
* :class:`brainvisa_config.BrainVISAConfig`
* :class:`fom_config.FomConfig`
* :class:`attributes_config.AttributesConfig`
* :class:`smartcaching_config.SmartCachingConfig`


:mod:`capsul.attributes`: Attributes and processes completion
=============================================================

See also the user doc :doc:`../user_guide_tree/advanced_usage`.

.. currentmodule:: capsul.attributes

Classes
-------

* :class:`~completion_engine.ProcessCompletionEngine`
* :class:`~completion_engine.PathCompletionEngine`
* :class:`~completion_engine.ProcessCompletionEngineFactory`
* :class:`~completion_engine.PathCompletionEngine`
* :class:`~completion_engine_iteration.ProcessCompletionEngineIteration`
* :class:`~fom_completion_engine.FomProcessCompletionEngine`
* :class:`~fom_completion_engine.FomProcessCompletionEngineIteration`
* :class:`~fom_completion_engine.FomPathCompletionEngine`
* :class:`~attributes_schema.AttributesSchema`
* :class:`~attributes_schema.ProcessAttributes`
* :class:`~attributes_schema.EditableAttributes`


Running external software
=========================

:mod:`capsul.in_context`
------------------------

The new system which will be used in Capsul v3 is based on :class:`~capsul.engine.CapsulEngine` and is the module:

:mod:`~capsul.in_context`


:mod:`capsul.subprocess`
------------------------

This module is obsolete and will be replaced by :mod:`~capsul.in_process`. It is still used in Capsul v2 when using :class:`~caspul.study_config.study_config.StudyConfig`.


:mod:`capsul.subprocess.fsl` Classes:
+++++++++++++++++++++++++++++++++++++

.. currentmodule:: capsul.subprocess.fsl

* :class:`Popen`


:mod:`capsul.subprocess.fsl` Functions:
+++++++++++++++++++++++++++++++++++++++

* :func:`fsl_command_with_environment`
* :func:`check_fsl_configuration`
* :func:`check_configuration_values`
* :func:`auto_configuration`
* :func:`call`
* :func:`check_call`
* :func:`check_output`


.. currentmodule:: capsul.subprocess.spm

:mod:`capsul.subprocess.spm` Classes:
+++++++++++++++++++++++++++++++++++++

* :class:`Popen`

:mod:`capsul.subprocess.spm` Functions:
+++++++++++++++++++++++++++++++++++++++

* :func:`find_spm`
* :func:`check_spm_configuration`
* :func:`check_configuration_values`
* :func:`auto_configuration`
* :func:`spm_command`
* :func:`call`
* :func:`check_call`
* :func:`check_output`


Workflow conversion
===================

.. currentmodule:: capsul.pipeline.pipeline_workflow

* :func:`workflow_from_pipeline`
* :func:`workflow_run`

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
    process
    pipeline
    engine
    study_config
    attributes
    in_context
    subprocess
    utils
    plugins
    qt_gui
    qt_apps
    sphinxext
