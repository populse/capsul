#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging

from capsul.apps_qt.qt_backend import QtGui
from capsul.apps_qt.base.window import MyQUiLoader

from board_gui_builder import BoardGUIBuilder


class BoardWindow(MyQUiLoader):
    """ Window to show the pipeline status and results.
    """

    def __init__(self, pipeline_instance, ui_file, study_config):
        """ Method to initialize the board window.

        Parameters
        ----------
        pipeline_instance: Pipeline (mandatory)
            the pipeline
        ui_file: str (madatory)
            a filename that contains all the user interface description
        """
        # Load UI
        MyQUiLoader.__init__(self, ui_file)

        # Define controls
        self.controls = {QtGui.QTreeWidget: ["tree_controller", ],
                         QtGui.QWidget: ["tree_widget", ]}

        # Find controls
        self.add_controls_to_ui()

        # Init tree
        self.ui.tree_controller.setColumnCount(5)
        self.ui.tree_controller.headerItem().setText(0, "Pipeline Name")
        self.ui.tree_controller.headerItem().setText(1, "Processings")
        self.ui.tree_controller.headerItem().setText(2, "Status")
        self.ui.tree_controller.headerItem().setText(3, "Logs")
        self.ui.tree_controller.headerItem().setText(4, "Viewers")

        # Update window name
        self._pipeline = pipeline_instance
        self.ui.tree_widget.parentWidget().setWindowTitle(
            "Result Board Viewer: {0}".format(self._pipeline.name))

        # Init the tree
        BoardGUIBuilder(self._pipeline, self.ui, study_config)

    def show(self):
        """ Shows the widget and its child widgets.
        """
        self.ui.show()

    def add_controls_to_ui(self):
        """ Method that set all desired controls in ui.
        """
        for control_type in self.controls.keys():
            for control_name in self.controls[control_type]:
                try:
                    value = self.ui.findChild(control_type, control_name)
                except:
                    logging.warning(
                        "{0} has no attribute "
                        "'{1}'".format(type(self.ui), control_name))
                setattr(self.ui, control_name, value)