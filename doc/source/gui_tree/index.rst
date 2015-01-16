:orphan:

######
GUI
######

The exact GUI description of all functions and classes, as given by 
the docstrings.

**User guide:** See the :ref:`capsul_guide` section for further details.

.. _capsul_gui_ref:

:mod:`capsul.qt_apps`: Application
==================================

.. currentmodule:: capsul.qt_apps

Classes
-------
.. autosummary::
    :toctree: generated/capsul-apps/
    :template: class.rst

    main_window.CapsulMainWindow
    pipeline_viewer_app.PipelineViewerApp


:mod:`capsul.qt_apps.utils`: Utils
==================================

.. currentmodule:: capsul.qt_apps.utils

Classes
-------
.. autosummary::
    :toctree: generated/capsul-apps-utils/
    :template: class.rst

    application.Application
    window.MyQUiLoader


Functions
---------
.. autosummary::
    :toctree: generated/capsul-apps-utils/
    :template: function.rst

    find_pipelines.find_pipelines
    fill_treectrl.fill_treectrl
    fill_treectrl.add_tree_nodes
    fill_treectrl.search_in_menu


:mod:`capsul.qt_gui`: Controller Widgets
========================================

.. currentmodule:: capsul.qt_gui

Classes
-------
.. autosummary::
    :toctree: generated/capsul-gui/
    :template: class.rst

    controller_widget.ScrollControllerWidget
    controller_widget.ControllerWidget    

.. currentmodule:: capsul.qt_gui.controls

Controls
--------
.. autosummary::
    :toctree: generated/capsul-gui-controls/
    :template: class.rst

    Str.StrControlWidget
    File.FileControlWidget
    Bool.BoolControlWidget
    Float.FloatControlWidget
    Directory.DirectoryControlWidget
    Enum.EnumControlWidget
    Int.IntControlWidget
    List.ListControlWidget


:mod:`capsul.qt_gui.widgets`: Pipeline Viewers
==============================================

.. currentmodule:: capsul.qt_gui.widgets

Classes
-------
.. autosummary::
    :toctree: generated/capsul-gui-widgets/
    :template: class.rst

    full_pipeline_widgets.PipelineDevelopperView
    workflow_widget.PipelineUserView

