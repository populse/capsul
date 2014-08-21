#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore

# Capsul import
from capsul.qt_apps.utils.window import MyQUiLoader


class BoardWidget(QtGui.QWidget):
    """ Class that create a widget to visualize the controller status.
    """

    def __init__(self, controller, ui_file, parent=None, name=None):
        """ Method to initilaize the ControllerWidget class.

        Parameters
        ----------
        controller: derived Controller instance (mandatory)
            a class derived from the Controller class we want to parametrize
            with a widget.
        ui_file: str (mandatory)
            a filename containing the board interface description.
        parent: QtGui.QWidget (optional, default None)
            the controller widget parent widget.
        name: (optional, default None)
            the name of this controller widget
        """
        # Inheritance
        super(BoardWidget, self).__init__(parent)

        # Class parameters
        self.controller = controller

        # If possilbe, set the widget name
        if name:
            self.setObjectName(name)

        # Load the board description
        board = MyQUiLoader(ui_file)
