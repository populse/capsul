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
from controller_gui_builder import ControllerGUIBuilder


class ControllerWindow(MyQUiLoader):
    """ Window to set the pipeline parameters.
    """

    def __init__(self, pipeline_instance, ui_file):
        """ Method to initialize the controller window.

        Parameters
        ----------
        pipeline_instance: Pipeline (mandatory)
            the pipeline we want to parametrize
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
        self.ui.tree_controller.setColumnCount(3)
        self.ui.tree_controller.headerItem().setText(0, "Node Name")
        self.ui.tree_controller.headerItem().setText(1, "Plug Name")
        self.ui.tree_controller.headerItem().setText(2, "Plug Value")

        # Update window name
        self._pipeline = pipeline_instance
        self.ui.tree_widget.parentWidget().setWindowTitle(
            "Controller Viewer: {0}".format(self._pipeline.name))

        # Init the tree
        ControllerGUIBuilder(self._pipeline, self.ui)

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
                    logging.warning("{0} has no attribute "
                        "'{1}'".format(type(self.ui), control_name))
                setattr(self.ui, control_name, value)
