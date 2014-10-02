:orphan:

######
API
######

The exact API of all functions and classes, as given by the docstrings.

.. _capsul_ref:

:mod:`capsul.pipeline`: Pipeline
=================================

.. automodule:: capsul.pipeline
   :no-members:
   :no-inherited-members:

**User guide:** See the :ref:`capsul_guide` section for further details.

.. currentmodule:: capsul.pipeline

Pipeline Definition
--------------------
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    pipeline.Pipeline

Node Types
-----------
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    pipeline_nodes.Node
    pipeline_nodes.ProcessNode
    pipeline_nodes.PipelineNode
    pipeline_nodes.Switch
    pipeline_nodes.Switch
    pipeline_nodes.IterativeNode

Plug
-----
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    pipeline.Plug

Workflow conversion
-------------------
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: function.rst

    pipeline_workflow.workflow_from_pipeline
    pipeline_workflow.local_workflow_run

    pipeline_tools.disable_node_for_downhill_pipeline
    pipeline_tools.disable_node_for_uphill_pipeline
    pipeline_tools.disable_nodes_with_existing_outputs
    pipeline_tools.reactivate_node
    pipeline_tools.reactivate_pipeline
    pipeline_tools.remove_temporary_exports


:mod:`capsul.process`: Process
===============================

.. automodule:: capsul.process
    :no-members:
    :no-inherited-members:

**User guide:** See the :ref:`capsul_guide` section for further details.

.. currentmodule:: capsul.process

Classes
-------

.. autosummary::
    :toctree: generated/capsul-process/
    :template: class_process.rst

    process.Process
    nipype_process.NipypeProcess

    :template: class.rst

    process.ProcessResult
    process_with_fom.ProcessWithFom

Functions
---------

.. autosummary::
    :toctree: generated/capsul-process/
    :template: function.rst

    loader.get_process_instance


:mod:`capsul.study_config`: Study Configuration
===============================================

.. automodule:: capsul.study_config
   :no-members:
   :no-inherited-members:

**User guide:** See the :ref:`capsul_guide` section for further details.

.. currentmodule:: capsul.study_config

.. autosummary::
    :toctree: generated/capsul-studyconfig/
    :template: class.rst

    study_config.StudyConfig

:doc:`pipeline_tools`
=====================

.. autosummary::
    :toctree: generated/capsul-pipeline_tools/
    :template: function.rst



