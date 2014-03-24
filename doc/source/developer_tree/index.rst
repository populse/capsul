:orphan:

###########################
Contributing Documentation
###########################

Useful information for advanced users.

.. _capsul_dev:

:mod:`capsul.pipeline`: Pipeline
=================================

.. automodule:: capsul.pipeline
   :no-members:
   :no-inherited-members:

**API:** See the :ref:`capsul_ref` section for API details.

.. currentmodule:: capsul.pipeline

Workflow Definition
--------------------
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    topological_sort.GraphNode
    topological_sort.Graph


:mod:`capsul.controller`: Controller
=====================================

.. automodule:: capsul.controller
   :no-members:
   :no-inherited-members:

.. currentmodule:: capsul.controller

Controller Definition
---------------------
.. autosummary::
    :toctree: generated/capsul-controller/
    :template: class.rst

    controller.Controller
    controller.MetaController
    controller.ControllerFactories


:mod:`capsul.process`: Process
===============================

.. automodule:: capsul.process
   :no-members:
   :no-inherited-members:

.. currentmodule:: capsul.process

.. autosummary::
    :toctree: generated/capsul-process/
    :template: class.rst

    process.NipypeProcess

.. autosummary::
    :toctree: generated/capsul-process/
    :template: function.rst

    nipype_process.nipype_factory


:mod:`capsul.study_config`: Study Configuration
================================================

.. automodule:: capsul.study_config
   :no-members:
   :no-inherited-members:


.. currentmodule:: capsul.study_config

.. autosummary::
    :toctree: generated/capsul-studyconfig/
    :template: function.rst

    config_utils.environment
    config_utils.find_spm
    memory._run_process
    memory._joblib_run_process
    spm_memory_utils.local_map
    spm_memory_utils.copy_resources
    spm_memory_utils.last_timestamp
    pipeline_workflow.workflow_from_pipeline
    pipeline_workflow.local_workflow_run







