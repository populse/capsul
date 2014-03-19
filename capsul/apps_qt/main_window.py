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

from PySide import QtCore, QtGui, QtWebKit

from capsul.apps_qt.base.window import MyQUiLoader
from capsul.process import get_process_instance
from capsul.apps_qt.base.pipeline_widgets import SimplePipelineView
from capsul.apps_qt.base.pipeline_widgets import FullPipelineView
import capsul.apps_qt.resources as resources
from capsul.apps_qt.base.controller import ControllerWindow


class MainWindow(MyQUiLoader):
    """ CAPSULVIEW main window.
    """

    def __init__(self, pipeline_names, ui_file):
        """ Method to initialize the CAPSUL main window.

        Parameters
        ----------
        pipeline_names: list of str (mandatory)
            a list of all the proposed pipelines as string description,
            ie. caps.preprocessings.Smooth
        ui_file: str (mandatory)
            a filename containing the user interface description
        """
        # Load user interface window
        MyQUiLoader.__init__(self, ui_file)

        # Define dynamic controls
        self.controls = {QtGui.QVBoxLayout: ["simple_pipeline_layout",
                                             "sub_pipeline"],
                         QtGui.QPushButton: ["load_pipeline", ],
                         QtGui.QTabWidget: ["simple_pipeline", ],
                         QtGui.QComboBox: ["pipeline_module"],
                         QtGui.QToolButton: ["clean_bottom_layout",
                                             "controller", "run",
                                             "cahnge_view", "help"]}

        # Find dynamic controls
        self.add_controls_to_ui()

        # Connect
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

        # Set default values
        self._pipeline_names = pipeline_names
        self.path_to_pipeline_doc = ("http://neurospin-wiki.org/doc_nsap/"
                                     "html/user_guide_tree/index.html")
        self.pipelines = {}
        self.pipeline = None
        self.ui.simple_pipeline.setTabsClosable(True)
        self.ui.pipeline_module.addItem("")
        self.onSearchInPipelines("")

        # Set some tooltips
        self.ui.help.setToolTip("Active Pipeline Documentation")
        self.ui.change_view.setToolTip("Switch Pipeline Vizualisation")
        self.ui.run.setToolTip("Execute Pipeline")
        self.ui.controller.setToolTip("Active Pipeline Controller")
        self.ui.clean_bottom_layout.setToolTip("Delete Sub Pipeline View")
        self.ui.pipeline_module.setToolTip("Type to filter known pipline "
            "list or enter a valid pipeline location")

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
                          FullPipelineView):
                SimplePipelineView(self.pipeline, self.ui)
            else:
                FullPipelineView(self.pipeline, self.ui)
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

    def onLoadPipelineClicked(self):
        """ Event to load a pipeline
        """
        if self.ui.pipeline_module.lineEdit().text() != "":
            self.pipeline = get_process_instance(
                str(self.ui.pipeline_module.lineEdit().text()))
            self.pipelines[self.pipeline.name] = self.pipeline
            FullPipelineView(self.pipeline, self.ui)
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
            #path_to_active_pipeline_doc = os.path.join(
            #    os.path.dirname(self.path_to_pipeline_doc),
            #    self.pipeline.__class__.__name__)
            path_to_active_pipeline_doc = self.path_to_pipeline_doc
        else:
            path_to_active_pipeline_doc = self.path_to_pipeline_doc
        # Create and fill a QWebView
        help = QtWebKit.QWebView()
        help.load(QtCore.QUrl(path_to_active_pipeline_doc))
        help.show()
        layout.addWidget(help)

        win.setLayout(layout)
        win.exec_()

    #####################
    # Private interface #
    #####################

    def _is_active_pipeline_valid(self):
        """ Method to ceack that the active pipeline is valid

        Returns
        -------
        is_valid: bool
            True if the active pipeline is valid
        """
        return self.pipeline != None