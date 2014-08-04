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
from capsul.apps_qt.base.window import MyQUiLoader
from capsul.apps_qt.base.pipeline_widgets import (
    PipelineDevelopperView, PipelineUserView)
import capsul.apps_qt.resources as resources
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
        # Inheritance: load user interface window
        MyQUiLoader.__init__(self, ui_file)

        # Create the study configuration
        self.study_config = StudyConfig(default_study_config)

        # Define dynamic controls
        self.controls = {
            QtGui.QAction: ["actionHelp", "actionQuit", "actionBrowse",
                            "actionLoad", "actionChangeView",
                            "actionParameters", "actionRun",
                            "actionStudyConfig", "actionQualityControl"],
            QtGui.QTableWidget: ["display", ],
            QtGui.QDockWidget: ["dockWidgetBrowse", "dockWidgetParameters",
                                "dockWidgetStudyConfig"],
            QtGui.QWidget: ["dock_browse", "dock_parameters",
                            "dock_study_config"],
            QtGui.QTreeWidget: ["menu_treectrl", ],
            QtGui.QLineEdit: ["search", ],            
        }

        # Add ui class parameter with the dynamic controls
        self.add_controls_to_ui()

        # Signal for dock widget
        self.ui.actionBrowse.triggered.connect(self.onBrowseClicked)
        self.ui.actionParameters.triggered.connect(self.onParametersClicked)
        self.ui.actionStudyConfig.triggered.connect(self.onStudyConfigClicked)

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
