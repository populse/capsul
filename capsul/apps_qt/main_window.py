#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
import logging

from capsul.apps_qt.qt_backend import QtCore, QtGui, QtWebKit

from capsul.apps_qt.base.window import MyQUiLoader
from capsul.apps_qt.base.pipeline_widgets import (
    PipelineDevelopperView, PipelineUserView)
import capsul.apps_qt.resources as resources
from capsul.apps_qt.base.controller import ControllerWindow
from capsul.apps_qt.base.board import BoardWindow

from capsul.process import get_process_instance
from capsul.study_config import StudyConfig


class CapsulMainWindow(MyQUiLoader):
    """ CAPSULVIEW main window.
    """

    def __init__(self, pipeline_names, ui_file, default_study_config=None):
        """ Method to initialize the CAPSUL main window.

        Parameters
        ----------
        pipeline_names: list of tuple (mandatory)
            a list of all the proposed pipelines as string description,
            ie. caps.preprocessings.Smooth and the corresponding
            documentation url.
        ui_file: str (mandatory)
            a filename containing the user interface description
        default_study_config: ordered dict (madatory)
            some parameters for the study configuration
        """
        # Load user interface window
        MyQUiLoader.__init__(self, ui_file)

        # Create the study configuration
        self.study_config = StudyConfig(default_study_config)

        # Define dynamic controls
        self.controls = {QtGui.QVBoxLayout: ["simple_pipeline_layout",
                                             "sub_pipeline"],
                         QtGui.QPushButton: ["load_pipeline", ],
                         QtGui.QTabWidget: ["simple_pipeline", ],
                         QtGui.QComboBox: ["pipeline_module"],
                         QtGui.QToolButton: ["clean_bottom_layout",
                                             "controller", "run",
                                             "cahnge_view", "help",
                                             "study_config", "view_result"]}

        # Find dynamic controls
        self.add_controls_to_ui()

        # Connect
        self.ui.study_config.clicked.connect(
            self.onCreateStudyConfigControllerClicked)
        self.ui.change_view.clicked.connect(self.onChangeViewClicked)
        self.ui.run.clicked.connect(self.onRunClicked)
        self.ui.controller.clicked.connect(self.onCreateControllerClicked)
        self.ui.simple_pipeline.currentChanged.connect(
            self.onTabSelectionChanged)
        self.ui.load_pipeline.clicked.connect(self.onLoadPipelineClicked)
        self.ui.simple_pipeline.tabCloseRequested.connect(
            self.onCloseTabClicked)
        self.ui.clean_bottom_layout.clicked.connect(
            self.onCleanBottomLayoutClicked)
        self.ui.help.clicked.connect(self.onHelpClicked)
        self.ui.pipeline_module.editTextChanged.connect(
            self.onSearchInPipelines)
        self.ui.view_result.clicked.connect(self.onViewResultClicked)

        # Set default values
        self._pipeline_names = [x[0] for x in pipeline_names]
        self.path_to_pipeline_doc = dict(item for item in pipeline_names)
        self.pipelines = {}
        self.pipeline = None
        self.ui.simple_pipeline.setTabsClosable(True)
        self.ui.pipeline_module.addItem("")
        self.onSearchInPipelines("")

        # Set some tooltips
        self.ui.help.setToolTip("Active Pipeline Documentation")
        self.ui.view_result.setToolTip("Active Pipeline Result Board")
        self.ui.change_view.setToolTip("Switch Pipeline Vizualisation")
        self.ui.run.setToolTip("Execute Pipeline")
        self.ui.controller.setToolTip("Active Pipeline Controller")
        self.ui.clean_bottom_layout.setToolTip("Delete Sub Pipeline View")
        self.ui.pipeline_module.setToolTip(
            "Type to filter known pipline list or enter a valid pipeline "
            "location")

    def show(self):
        """ Shows the widget and its child widgets.
        """
        self.ui.show()

    def add_controls_to_ui(self):
        """ Method to find dynamic controls
        """
        for control_type in self.controls.keys():
            for control_name in self.controls[control_type]:
                try:
                    value = self.ui.findChild(control_type, control_name)
                    setattr(self.ui, control_name, value)
                except:
                    logging.error("{0} has no attribute"
                                  "'{1}'".format(type(self.ui), control_name))

    ###########
    # Signals #
    ###########

    def onViewResultClicked(self):
        """ Event to create a result board
        """
        if self._is_active_pipeline_valid():
            ui_file = os.path.join(resources.__path__[0],
                                   "controller_viewer.ui")
            self.board_window = BoardWindow(self.pipeline, ui_file,
                                            self.study_config)
            self.board_window.show()
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

    def onSearchInPipelines(self, text):
        """ Event to filter the pipelines
        """
        matches = [module_name for module_name in self._pipeline_names
                   if text.lower() in module_name.lower()]
        if matches and not text == matches[0]:
            while self.ui.pipeline_module.count() > 1:
                self.ui.pipeline_module.removeItem(1)
            self.ui.pipeline_module.addItems(matches)

    def onChangeViewClicked(self):
        """ Event to switch between simple and full pipeline views
        """
        if self._is_active_pipeline_valid():
            if isinstance(self.ui.simple_pipeline.currentWidget(),
                          PipelineDevelopperView):
                widget = PipelineUserView(self.pipeline)
                self._insert_widget_in_tab(widget)
            else:
                widget = PipelineDevelopperView(self.pipeline)
                self._insert_widget_in_tab(widget)
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

    def onLoadSubPipelineClicked(self, sub_pipeline):
        """ Event to load a sub pipeline
        """
        # Store the pipeline instance
        self.pipeline = sub_pipeline

        # Store the pipeline instance
        self.pipelines[self.pipeline.name] = self.pipeline

        # Create the widget
        widget = PipelineDevelopperView(self.pipeline)
        self._insert_widget_in_tab(widget)

        # Connect the subpipeline clicked signal to the
        # onLoadSubPipelineClicked slot
        widget.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)

    def onLoadPipelineClicked(self):
        """ Event to load a pipeline
        """
        if self.ui.pipeline_module.lineEdit().text() != "":
            # Get the pipeline instance from its string description
            self.pipeline = get_process_instance(
                str(self.ui.pipeline_module.lineEdit().text()))

            # Store the pipeline instance
            self.pipelines[self.pipeline.name] = self.pipeline

            # Create the widget
            widget = PipelineDevelopperView(self.pipeline)
            self._insert_widget_in_tab(widget)

            # Connect the subpipeline clicked signal to the
            # onLoadSubPipelineClicked slot
            widget.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)
        else:
            logging.error("No pipeline selected.")

    def onCloseTabClicked(self, index):
        """ Event to close a pipeline view
        """
        del self.pipelines[self.ui.simple_pipeline.tabText(index)]
        self.ui.simple_pipeline.removeTab(index)

    def onCleanBottomLayoutClicked(self):
        """ Event to clean the bub pipeline layout
        """
        while self.ui.sub_pipeline.count() != 0:
            b = self.ui.sub_pipeline.takeAt(0)
            b.widget().close()

    def onTabSelectionChanged(self, index):
        """ Event to update context when the user select
        a new tab
        """
        index = self.ui.simple_pipeline.currentIndex()
        pipeline_name = self.ui.simple_pipeline.tabText(index)
        if pipeline_name:
            self.pipeline = self.pipelines[pipeline_name]
            self.onCleanBottomLayoutClicked()
        else:
            self.pipeline = None

    def onCreateStudyConfigControllerClicked(self):
        """ Event to create a controller for the active pipeline
        """
        ui_file = os.path.join(resources.__path__[0],
                               "controller_viewer.ui")
        self.controller_window = ControllerWindow(self.study_config, ui_file)
        self.controller_window.show()

    def onCreateControllerClicked(self):
        """ Event to create a controller for the active pipeline
        """
        if self._is_active_pipeline_valid():
            ui_file = os.path.join(resources.__path__[0],
                                   "controller_viewer.ui")
            self.controller_window = ControllerWindow(self.pipeline, ui_file)
            self.controller_window.show()
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

    def onRunClicked(self):
        """ Event to execute the active pipeline
        """
        if self._is_active_pipeline_valid():
            logging.info("PARAMETERS of pipeline {0}".format(
                self.pipeline.name))
            for plug_name, plug in self.pipeline.nodes[""].plugs.iteritems():
                logging.info("-- plug name: {0} - plug value {1}".format(
                    plug_name,
                    self.pipeline.nodes[""].get_plug_value(plug_name)))

            self.study_config.run(self.pipeline)
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

    def onHelpClicked(self):
        """ Event to print the documentation of the active pipeline
        """
        win = QtGui.QDialog()
        win.setWindowTitle("Pipeline Help")
        layout = QtGui.QHBoxLayout()

        # Build Pipeline documentation location
        if self.pipeline:
            # Generate the url to the active pipeline documentation
            path_to_active_pipeline_doc = os.path.join(
                self.path_to_pipeline_doc[self.pipeline.id],
                self.pipeline.id.split(".")[1] + "_tree",
                "generated", "pipeline", self.pipeline.id + ".html")

            # Create and fill a QWebView
            help = QtWebKit.QWebView()
            help.load(QtCore.QUrl(path_to_active_pipeline_doc))
            help.show()
            layout.addWidget(help)

            win.setLayout(layout)
            win.exec_()
        else:
            # No Pipeline loaded, cant't show the documentation message
            QtGui.QMessageBox.information(
                self.ui, "Information", "First load a pipeline!")

    #####################
    # Private interface #
    #####################

    def _insert_widget_in_tab(self, widget):
        """ Insert a new widget or replace an existing widget.

        Parameters
        ----------
        widget: a widget (mandatory)
            the widget we want to draw
        """
        # add the widget if new
        # otherwise, recreate the widget
        already_created = False
        index = 0
        for index in range(self.ui.simple_pipeline.count()):
            if (self.ui.simple_pipeline.tabText(index) ==
                    self.pipeline.name):
                already_created = True
                break
        if not already_created:
            self.ui.simple_pipeline.addTab(
                widget, unicode(self.pipeline.name))
            self.ui.simple_pipeline.setCurrentIndex(
                self.ui.simple_pipeline.count() - 1)
        else:
            pipeline = self.pipeline
            self.ui.simple_pipeline.removeTab(index)
            self.pipeline = pipeline
            self.ui.simple_pipeline.insertTab(
                index, widget, unicode(self.pipeline.name))
            self.ui.simple_pipeline.setCurrentIndex(index)

    def _is_active_pipeline_valid(self):
        """ Method to ceack that the active pipeline is valid

        Returns
        -------
        is_valid: bool
            True if the active pipeline is valid
        """
        return self.pipeline is not None