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

:mod:`capsul.engine.database_json`: JSON Database
=================================================

.. currentmodule:: capsul.engine.database_json

.. automodule:: capsul.engine.database_json


:mod:`capsul.engine`: Capsul Configuration
================================================

.. currentmodule:: capsul.engine

.. autosummary::
    :toctree: generated/capsul-engine/
    :template: class.rst

    CapsulEngine
    database.DatabaseEngine

.. autosummary::
    :toctree: generated/capsul-engine/
    :template: function.rst
    
    capsul_engine
    database_factory


:mod:`capsul.subprocess`: Running external software
===================================================

.. currentmodule:: capsul.subprocess.fsl

.. autosummary::
    :toctree: generated/capsul-subprocess/
    :template: class.rst

.. autosummary::
    :toctree: generated/capsul-subprocess/
    :template: function.rst

.. currentmodule:: capsul.subprocess.spm

.. autosummary::
    :toctree: generated/capsul-subprocess/
    :template: class.rst

.. autosummary::
    :toctree: generated/capsul-subprocess/
    :template: function.rst


