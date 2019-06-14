:orphan:

.. _capsul_ref:

====================================
CAPSUL programming API documentation
====================================

See also the :ref:`capsul_guide` section for more general usage documentation.

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

Plug
-----

* :class:`Plug`

Workflow conversion
-------------------

.. currentmodule:: capsul.pipeline.pipeline_workflow

* :func:`workflow_from_pipeline`
* :func:`workflow_run`

.. currentmodule:: capsul.pipeline.pipeline_tools

* :func:`pipeline_node_colors`
* :func:`pipeline_link_color`
* :func:`dot_graph_from_pipeline`
* :func:`save_dot_graph`
* :func:`save_dot_image`
* :func:`nodes_with_existing_outputs`
* :func:`nodes_with_missing_inputs`
* :func:`disable_runtime_steps_with_existing_outputs`
* :func:`where_is_plug_value_from`

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


:mod:`capsul.study_config`: Study Configuration
===============================================

.. currentmodule:: capsul.study_config

Study Configuration
-------------------

* :class:`~study_config.StudyConfig`
* :class:`~memory.Memory`

Configuration Modules
---------------------

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


:mod:`capsul.engine`: Configuration and execution
=================================================

.. currentmodule:: capsul.engine

Classes
-------

* :class:`CapsulEngine`


Functions
---------

* :func:`capsul_engine`


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


:mod:`capsul.subprocess`: Running external software
===================================================

:mod:`capsul.subprocess.fsl` Classes
------------------------------------

.. currentmodule:: capsul.subprocess.fsl

* :class:`Popen`


:mod:`capsul.subprocess.fsl` Functions
--------------------------------------

* :func:`fsl_command_with_environment`
* :func:`check_fsl_configuration`
* :func:`check_configuration_values`
* :func:`auto_configuration`
* :func:`call`
* :func:`check_call`
* :func:`check_output`


.. currentmodule:: capsul.subprocess.spm

:mod:`capsul.subprocess.spm` Classes
------------------------------------

* :class:`Popen`

:mod:`capsul.subprocess.spm` Functions
--------------------------------------

* :func:`find_spm`
* :func:`check_spm_configuration`
* :func:`check_configuration_values`
* :func:`auto_configuration`
* :func:`spm_command`
* :func:`call`
* :func:`check_call`
* :func:`check_output`


GUI
===

Graphical widgets classes

.. _capsul_gui_ref:

:mod:`capsul.qt_gui.widgets`: Pipeline Viewers
----------------------------------------------

.. currentmodule:: capsul.qt_gui.widgets

* :class:`~pipeline_developper_view.PipelineDevelopperView`
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

