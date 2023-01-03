# -*- coding: utf-8 -*-
'''
Classes
=======

:class:`CapsulMainWindow`
-------------------------
'''

# System import
from __future__ import absolute_import
import os
import logging
import six
from six.moves import range

# Define the logger
logger = logging.getLogger(__name__)

# Soma import
from soma.qt_gui.qt_backend import QtCore, QtGui, QtWebKit
from soma.qt_gui.controller_widget import ScrollControllerWidget

# Capsul import
from capsul.qt_apps.utils.window import MyQUiLoader
from capsul.qt_apps.utils.fill_treectrl import fill_treectrl
from capsul.qt_gui.widgets import (PipelineDeveloperView, PipelineUserView)
from capsul.qt_gui.board_widget import BoardWidget
from capsul.api import get_process_instance
from capsul.pipeline.process_iteration import ProcessIteration
from capsul.study_config.study_config import StudyConfig


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
        default_study_config: ordered dict (mandatory)
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
                                "dockWidgetStudyConfig", "dockWidgetBoard"],
            QtGui.QWidget: ["dock_browse", "dock_parameters",
                            "dock_study_config", "dock_board"],
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
        self.ui.actionQualityControl.triggered.connect(self.onQualityControlClicked)

        # Initialize properly the visibility of each dock widget
        self.onBrowseClicked()
        self.onParametersClicked()
        self.onStudyConfigClicked()
        self.onQualityControlClicked()

        # Signal for the pipeline creation
        self.ui.search.textChanged.connect(self.onSearchClicked)
        self.ui.menu_treectrl.currentItemChanged.connect(
            self.onTreeSelectionChanged)
        self.ui.actionLoad.triggered.connect(self.onLoadClicked)

        # Signal for the execution
        self.ui.actionRun.triggered.connect(self.onRunClicked)

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
        for control_type, control_item in six.iteritems(self.controls):

            # Get the dynamic control name
            for control_name in control_item:

                # Try to set the control value to the ui class parameter
                try:
                    value = self.ui.findChild(control_type, control_name)
                    if value is None:
                        logger.error(error_message.format(
                            type(self.ui), control_name))
                    setattr(self.ui, control_name, value)
                except Exception:
                    logger.error(error_message.format(
                        type(self.ui), control_name))

    ###########################################################################
    # Slots   
    ###########################################################################

    def onRunClicked(self):
        """ Event to execute the process/pipeline.
        """
        self.study_config.run(self.pipeline, executer_qc_nodes=True, verbose=1)

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
        # Show parameters dock widget
        if self.ui.actionParameters.isChecked():
            self.ui.dockWidgetParameters.show()

        # Hide parameters dock widget
        else:
            self.ui.dockWidgetParameters.hide()

    def onStudyConfigClicked(self):
        """ Event to show / hide the study config dock widget.
        """
        # Show study configuration dock widget
        if self.ui.actionStudyConfig.isChecked():
            self.ui.dockWidgetStudyConfig.show()

        # Hide study configuration dock widget
        else:
            self.ui.dockWidgetStudyConfig.hide()

    def onQualityControlClicked(self):
        """ Event to show / hide the board dock widget.
        """
        # Create and show board dock widget
        if self.ui.actionQualityControl.isChecked():

            # Create the board widget associated to the pipeline controller
            # Create on the fly in order to get the last status
            # ToDo: add callbacks
            if self.pipeline is not None:
                # board_widget = BoardWidget(
                #     self.pipeline, parent=self.ui.dockWidgetParameters,
                #     name="board")
                board_widget = ScrollControllerWidget(
                    self.pipeline, name="outputs", live=True,
                    hide_labels=False, select_controls="outputs",
                    disable_controller_widget=True)
                #board_widget.setEnabled(False)
                self.ui.dockWidgetBoard.setWidget(board_widget)

            # Show the board widget
            self.ui.dockWidgetBoard.show()

        # Hide board dock widget
        else:
            self.ui.dockWidgetBoard.hide()

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
        if item is None:
            return

        # Check if we have selected a pipeline in the tree and enable / disable
        # the load button
        url = item.text(2)
        if url == "None":
            self.ui.actionLoad.setEnabled(False)
        else:
            self.ui.actionLoad.setEnabled(True)

    def onRunStatus(self):
        """ Event to refresh the run button status.

        When all the controller widget controls are correctly filled, enable
        the user to execute the pipeline.
        """
        # Get the controller widget
        controller_widget = self.ui.dockWidgetParameters.widget().controller_widget

        # Get the controller widget status
        is_valid = controller_widget.is_valid()

        # Depending on the controller widget status enable / disable
        # the run button
        self.ui.actionRun.setEnabled(is_valid)

    def onLoadClicked(self):
        """ Event to load and display a pipeline.
        """
        # Get the pipeline instance from its string description
        item = self.ui.menu_treectrl.currentItem()
        description_list = [str(x) for x in [item.text(1), item.text(0)]
                            if x != ""]
        process_description = ".".join(description_list)
        self.pipeline = get_process_instance(process_description)

        # Create the controller widget associated to the pipeline
        # controller
        pipeline_widget = ScrollControllerWidget(
            self.pipeline, live=True, select_controls="inputs")
        self.ui.dockWidgetParameters.setWidget(pipeline_widget)

        # Add observer to refresh the run button
        controller_widget = pipeline_widget.controller_widget
        for control_name, control \
                in six.iteritems(controller_widget._controls):

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # Add the new callback
            control_class.add_callback(self.onRunStatus, control_instance)

        # Refresh manually the run button status the first time
        self.onRunStatus()

        # Store the pipeline documentation root path
        self.path_to_pipeline_doc[self.pipeline.id] = item.text(2)

        # Store the pipeline instance
        self.pipelines[self.pipeline.name] = (
            self.pipeline, pipeline_widget)

        # Create the widget
        widget = PipelineDeveloperView(self.pipeline)
        self._insert_widget_in_tab(widget)

        # Connect the subpipeline clicked signal to the
        # onLoadSubPipelineClicked slot
        widget.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)

    def onLoadSubPipelineClicked(self, name, sub_pipeline, modifiers):
        """ Event to load and display a sub pipeline.
        """
        # Store the pipeline instance in class parameters
        self.pipeline = self.pipeline.nodes[name].process

        # Create the controller widget associated to the sub pipeline
        # controller: if the sub pipeline is a ProcessIteration, disable
        # the correspondind controller widget since this pipeline is generated
        # on the fly an is not directly synchronized with the rest of the
        # pipeline.
        is_iterative_pipeline = False
        if isinstance(self.pipeline, ProcessIteration):
            is_iterative_pipeline = True
        pipeline_widget = ScrollControllerWidget(
            self.pipeline, live=True, select_controls="inputs",
            disable_controller_widget=is_iterative_pipeline)
        self.ui.dockWidgetParameters.setWidget(pipeline_widget)

        # Store the sub pipeline instance
        self.pipelines[self.pipeline.name] = (
            self.pipeline, pipeline_widget)

        # Create the widget
        widget = PipelineDeveloperView(self.pipeline)
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
            self.ui.actionRun.setEnabled(False)

        # A new valid tab is selected
        else:
            # Get the selected pipeline widget
            self.pipeline, pipeline_widget = self.pipelines[
                self.ui.display.tabText(index)]

            # Set the controller widget associated to the pipeline
            # controller
            self.ui.dockWidgetParameters.setWidget(pipeline_widget)

            # Refresh manually the run button status the first time
            self.onRunStatus()

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

        # No Pipeline loaded, can't show the documentation message
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
            # Case PipelineDeveloperView
            if isinstance(self.ui.display.currentWidget(),
                          PipelineDeveloperView):

                # Switch to PipelineUserView display mode
                widget = PipelineUserView(self.pipeline)
                self._insert_widget_in_tab(widget)

            # Case PipelineUserView
            else:

                # Switch to PipelineDeveloperView display mode
                widget = PipelineDeveloperView(self.pipeline)
                self._insert_widget_in_tab(widget)

        # No pipeline loaded error
        else:
            logger.error("No active pipeline selected. "
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
        # Search if the tab corresponding to the widget has already been created
        already_created = False
        index = 0

        # Go through all the tabs
        for index in range(self.ui.display.count()):

            # Check if we have a match: the tab name is equal to the current
            #pipeline name
            if (self.ui.display.tabText(index) == self.pipeline.name):
                already_created = True
                break

        # If no match found, add a new tab with the widget
        if not already_created:
            self.ui.display.addTab(
                widget, six.text_type(self.pipeline.name))
            self.ui.display.setCurrentIndex(
                self.ui.display.count() - 1)

        # Otherwise, replace the widget from the match tab
        else:
            # Delete the tab
            self.ui.display.removeTab(index)

            # Insert the new tab
            self.ui.display.insertTab(
                index, widget, six.text_type(self.pipeline.name))

            # Set the corresponding index
            self.ui.display.setCurrentIndex(index)



    def _is_active_pipeline_valid(self):
        """ Method to ceack that the active pipeline is valid

        Returns
        -------
        is_valid: bool
            True if the active pipeline is valid
        """
        return self.pipeline is not None
