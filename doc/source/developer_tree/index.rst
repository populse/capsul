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

Pipeline nodes sorting and workflow helper

.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    topological_sort.GraphNode
    topological_sort.Graph

Nodes
-----

Iterative node building blocks.

.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    pipeline_iterative.IterativeManager
    pipeline_iterative.IterativePipeline


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
    run._run_process
    run.set_output_dir
    run_with_cache._joblib_run_process
    spm_cache_utils.local_map
    spm_cache_utils.copy_resources
    spm_cache_utils.last_timestamp

