:orphan:

###########################
Contributing Documentation
###########################

Useful information for advanced users.

**API:** See the :ref:`capsul_ref` section for API details.

.. _capsul_dev:

:mod:`capsul.pipeline`: Pipeline
=================================

.. currentmodule:: capsul.pipeline

Workflow Definition
--------------------

Pipeline nodes sorting and workflow helper

.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    topological_sort.GraphNode
    topological_sort.Graph


:mod:`capsul.process`: Process
===============================

.. currentmodule:: capsul.process

.. autosummary::
    :toctree: generated/capsul-process/
    :template: function.rst

    nipype_process.nipype_factory


:mod:`capsul.study_config`: Study Configuration
================================================

.. currentmodule:: capsul.study_config

.. autosummary::
    :toctree: generated/capsul-studyconfig/
    :template: class.rst

    memory.MemorizedProcess
    memory.UnMemorizedProcess

.. autosummary::
    :toctree: generated/capsul-studyconfig/
    :template: function.rst

    config_utils.environment
    run.run_process

.. currentmodule:: capsul.study_config.config_modules

.. autosummary::
    :toctree: generated/capsul-studyconfig/
    :template: function.rst

    spm_config.find_spm

