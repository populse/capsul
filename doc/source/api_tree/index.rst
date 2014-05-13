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

Plug
-----
.. autosummary::
    :toctree: generated/capsul-pipeline/
    :template: class.rst

    pipeline.Plug


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


:mod:`capsul.controller`: Traits
================================

.. automodule:: capsul.controller
   :no-members:
   :no-inherited-members:

.. currentmodule:: capsul.controller

.. autosummary::
    :toctree: generated/capsul-traits/
    :template: function.rst

    trait_utils.trait_ids


