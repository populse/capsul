#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import logging

# Soma import
from soma.qt_gui.qt_backend import QtCore, QtGui, QtWebKit

# Capsul import
from capsul.qt_apps.utils.window import MyQUiLoader
from capsul.qt_gui.widgets import (PipelineDevelopperView, PipelineUserView)
from capsul.process import get_process_instance
from capsul.study_config import StudyConfig
from capsul.qt_apps.utils.fill_treectrl import fill_treectrl
from capsul.qt_gui.controller_widget import ScrollControllerWidget


class CapsulMainWindow(MyQUiLoader):
    """ Capsul main window.
    """
    def __init__(self, pipeline_menu, ui_file, default_study_config=None):
        """ Method to initialize the Capsul main window class.

        Parameters
        ----------
        pipeline_menu: hierachic dict
            each key is a sub module of the module. Leafs contain a list with
            the url to the documentation.
        ui_file: str (mandatory)
            a filename containing the user interface description
        default_study_config: ordered dict (madatory)
            some parameters for the study configuration
        """
        # Inheritance: load user interface window
        MyQUiLoader.__init__(self, ui_file)

        # Class parameters
        self.pipeline_menu = pipeline_menu
        self.pipelines = {}
        self.pipeline = None
        self.path_to_pipeline_doc = {}

        # Define dynamic controls
        self.controls = {
            QtGui.QAction: ["actionHelp", "actionQuit", "actionBrowse",
                            "actionLoad", "actionChangeView",
                            "actionParameters", "actionRun",
                            "actionStudyConfig", "actionQualityControl"],
            QtGui.QTabWidget: ["display", ],
            QtGui.QDockWidget: ["dockWidgetBrowse", "dockWidgetParameters",
                                "dockWidgetStudyConfig"],
            QtGui.QWidget: ["dock_browse", "dock_parameters",
                            "dock_study_config"],
            QtGui.QTreeWidget: ["menu_treectrl", ],
            QtGui.QLineEdit: ["search", ],
        }

        # Add ui class parameter with the dynamic controls and initialize
        # default values
        self.add_controls_to_ui()
        self.ui.display.setTabsClosable(True)

        # Create the study configuration
        self.study_config = StudyConfig(default_study_config)

        # Create the controller widget associated to the study
        # configuration controller
        self.study_config_widget = ScrollControllerWidget(
            self.study_config, live=True)
        self.ui.dockWidgetStudyConfig.setWidget(self.study_config_widget)

        # Create the pipeline menu
        fill_treectrl(self.ui.menu_treectrl, self.pipeline_menu)

        # Signal for window interface
        self.ui.actionHelp.triggered.connect(self.onHelpClicked)
        self.ui.actionChangeView.triggered.connect(self.onChangeViewClicked)

        # Signal for tab widget
        self.ui.display.currentChanged.connect(self.onCurrentTabChanged)
        self.ui.display.tabCloseRequested.connect(self.onCloseTabClicked)

        # Signal for dock widget
        self.ui.actionBrowse.triggered.connect(self.onBrowseClicked)
        self.ui.actionParameters.triggered.connect(self.onParametersClicked)
        self.ui.actionStudyConfig.triggered.connect(self.onStudyConfigClicked)

        # Signal for the pipeline creation
        self.ui.search.textChanged.connect(self.onSearchClicked)
        self.ui.menu_treectrl.currentItemChanged.connect(
            self.onTreeSelectionChanged)
        self.ui.actionLoad.triggered.connect(self.onLoadClicked)

        # Set default values

        # Set some tooltips

    def show(self):
        """ Shows the widget and its child widgets.
        """
        self.ui.show()

    def add_controls_to_ui(self):
        """ Method to find dynamic controls
        """
        # Error message template
        error_message = "{0} has no attribute '{1}'"

        # Got through the class dynamic controls
        for control_type, control_item in self.controls.iteritems():

            # Get the dynamic control name
            for control_name in control_item:

                # Try to set the control value to the ui class parameter
                try:
                    value = self.ui.findChild(control_type, control_name)
                    if value is None:
                        logging.error(error_message.format(
                            type(self.ui), control_name))
                    setattr(self.ui, control_name, value)
                except:
                    logging.error(error_message.format(
                        type(self.ui), control_name))

    ###########
    # Signals #
    ###########

    def onBrowseClicked(self):
        """ Event to show / hide the browse dock widget.
        """
        # Show browse dock widget
        if self.ui.actionBrowse.isChecked():
            self.ui.dockWidgetBrowse.show()

        # Hide browse dock widget
        else:
            self.ui.dockWidgetBrowse.hide()

    def onParametersClicked(self):
        """ Event to show / hide the parameters dock widget.
        """
        # Show browse dock widget
        if self.ui.actionParameters.isChecked():
            self.ui.dockWidgetParameters.show()

        # Hide browse dock widget
        else:
            self.ui.dockWidgetParameters.hide()

    def onStudyConfigClicked(self):
        """ Event to show / hide the study config dock widget.
        """
        # Show browse dock widget
        if self.ui.actionStudyConfig.isChecked():
            self.ui.dockWidgetStudyConfig.show()

        # Hide browse dock widget
        else:
            self.ui.dockWidgetStudyConfig.hide()

    def onSearchClicked(self):
        """ Event to refresh the menu tree control that contains the pipeline
        modules.
        """
        # Clear the current tree control
        self.ui.menu_treectrl.clear()

        # Build the new filtered tree control
        fill_treectrl(self.ui.menu_treectrl, self.pipeline_menu,
                      self.ui.search.text().lower())

    def onTreeSelectionChanged(self):
        """ Event to refresh the pipeline load button status.
        """
        # Get the cuurent item
        item = self.ui.menu_treectrl.currentItem()

        # Check if we have selected a pipeline in the tree and enable / disable
        # the load button
        url = item.text(2)
        if url == "None":
            self.ui.actionLoad.setEnabled(False)
        else:
            self.ui.actionLoad.setEnabled(True)

    def onLoadClicked(self):
        """ Event to load and display a pipeline.
        """
        # Get the pipeline instance from its string description
        item = self.ui.menu_treectrl.currentItem()
        process_description = str(item.text(1) + "." + item.text(0))
        self.pipeline = get_process_instance(process_description)

        # Create the controller widget associated to the pipeline
        # controller
        pipeline_widget = ScrollControllerWidget(self.pipeline, live=True)
        self.ui.dockWidgetParameters.setWidget(pipeline_widget)

        # Store the pipeline documentation root path
        self.path_to_pipeline_doc[self.pipeline.id] = item.text(2)

        # Store the pipeline instance
        self.pipelines[self.pipeline.name] = (
            self.pipeline, pipeline_widget)

        # Create the widget
        widget = PipelineDevelopperView(self.pipeline)
        self._insert_widget_in_tab(widget)

        # Connect the subpipeline clicked signal to the
        # onLoadSubPipelineClicked slot
        widget.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)

    def onLoadSubPipelineClicked(self, name, sub_pipeline, modifiers):
        """ Event to load and display a sub pipeline.
        """
        # Store the pipeline instance in class parameters
        self.pipeline = sub_pipeline

        # Create the controller widget associated to the sub pipeline
        # controller
        pipeline_widget = ScrollControllerWidget(self.pipeline)
        self.ui.dockWidgetParameters.setWidget(pipeline_widget)

        # Store the sub pipeline instance
        self.pipelines[self.pipeline.name] = (
            self.pipeline, pipeline_widget)

        # Create the widget
        widget = PipelineDevelopperView(self.pipeline)
        self._insert_widget_in_tab(widget)

        # Connect the subpipeline clicked signal to the
        # onLoadSubPipelineClicked slot
        widget.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)

    def onCloseTabClicked(self, index):
        """ Event to close a pipeline view.
        """
        # Remove the pipeline from the intern pipeline list
        pipeline, pipeline_widget = self.pipelines[
            self.ui.display.tabText(index)]
        pipeline_widget.close()
        pipeline_widget.deleteLater()
        del self.pipelines[self.ui.display.tabText(index)]

        # Remove the table that contains the pipeline
        self.ui.display.removeTab(index)

    def onCurrentTabChanged(self, index):
        """ Event to refresh the controller controller widget when a new
        tab is selected
        """
        # If no valid tab index has been passed
        if index < 0:
            # Delete the controller widget in the dock widget
            to_remove_widget = self.ui.dockWidgetParameters.widget()
            to_remove_widget.close()
            to_remove_widget.deleteLater()

        # A new valid tab is selected
        else:
            # Get the selected pipeline widget
            pipeline, pipeline_widget = self.pipelines[
                self.ui.display.tabText(index)]

            # Set the controller widget associated to the pipeline
            # controller
            self.ui.dockWidgetParameters.setWidget(pipeline_widget)

    def onHelpClicked(self):
        """ Event to display the documentation of the active pipeline.
        """
        # Create a dialog box to display the html documentation
        win = QtGui.QDialog()
        win.setWindowTitle("Pipeline Help")

        # Build the pipeline documentation location
        # Possible since common tools generate the sphinx documentation
        if self.pipeline:

            # Generate the url to the active pipeline documentation
            path_to_active_pipeline_doc = os.path.join(
                self.path_to_pipeline_doc[self.pipeline.id], "generated",
                self.pipeline.id.split(".")[1], "pipeline",
                self.pipeline.id + ".html")

            # Create and fill a QWebView
            help = QtWebKit.QWebView()
            help.load(QtCore.QUrl(path_to_active_pipeline_doc))
            help.show()

            # Create and set a layout with the web view
            layout = QtGui.QHBoxLayout()
            layout.addWidget(help)
            win.setLayout(layout)

            # Display the window
            win.exec_()

        # No Pipeline loaded, cant't show the documentation message
        # Display a message box
        else:
            QtGui.QMessageBox.information(
                self.ui, "Information", "First load a pipeline!")

    def onChangeViewClicked(self):
        """ Event to switch between simple and full pipeline views.
        """
        # Check if a pipeline has been loaded
        if self._is_active_pipeline_valid():

            # Check the current display mode
            # Case PipelineDevelopperView
            if isinstance(self.ui.display.currentWidget(),
                          PipelineDevelopperView):

                # Switch to PipelineUserView display mode
                widget = PipelineUserView(self.pipeline)
                self._insert_widget_in_tab(widget)

            # Case PipelineUserView
            else:

                # Switch to PipelineDevelopperView display mode
                widget = PipelineDevelopperView(self.pipeline)
                self._insert_widget_in_tab(widget)

        # No pipeline loaded error
        else:
            logging.error("No active pipeline selected. "
                          "Have you forgotten to click the load pipeline "
                          "button?")

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
        for index in range(self.ui.display.count()):
            if (self.ui.display.tabText(index) ==
                    self.pipeline.name):
                already_created = True
                break
        if not already_created:
            self.ui.display.addTab(
                widget, unicode(self.pipeline.name))
            self.ui.display.setCurrentIndex(
                self.ui.display.count() - 1)
        else:
            pipeline = self.pipeline
            self.ui.display.removeTab(index)
            self.pipeline = pipeline
            self.ui.display.insertTab(
                index, widget, unicode(self.pipeline.name))
            self.ui.display.setCurrentIndex(index)

    def _is_active_pipeline_valid(self):
        """ Method to ceack that the active pipeline is valid

        Returns
        -------
        is_valid: bool
            True if the active pipeline is valid
        """
        return self.pipeline is not None
