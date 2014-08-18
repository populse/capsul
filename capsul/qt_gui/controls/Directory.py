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

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore

# Capsul import
from File import FileControlWidget


class DirectoryControlWidget(FileControlWidget):
    """ Control to enter a directory.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control value is correct.

        If the new entered value is not correct, the backroung control color
        will be red.

        Parameters
        ----------
        control_instance: QWidget (mandatory)
            the control widget we want to validate

        Returns
        -------
        out: bool
            True if the control value is a file,
            False otherwise
        """
        # Get the current control palette
        control_palette = control_instance.path.palette()

        # Get the control current value
        control_value = control_instance.path.text()

        # If the control value contains a file, the control is valid and the
        # backgound color of the control is white
        is_valid = False
        if os.path.isdir(control_value):
            control_palette.setColor(
                control_instance.path.backgroundRole(), QtCore.Qt.white)
            is_valid = True

        # If the control value do not contains a file, the control is not valid
        # and the backgound color of the control is red
        else:
            control_palette.setColor(
                control_instance.path.backgroundRole(), QtCore.Qt.red)

        # Set the new palette to the control instance
        control_instance.path.setPalette(control_palette)

        return is_valid

    ###########################################################################
    # Callbacks
    ###########################################################################

    @staticmethod
    def onBrowseClicked(control_instance):
        """ Browse the file system and update the control instance accordingly.

        If a valid direcorty has already been entered the dialogue will
        automatically point to this folder, otherwise the current working
        directory is used.

        Parameters
        ----------
        control_instance: QWidget (mandatory)
            the directory widget item
        """
        # Get the current directory
        current_control_value = os.path.join(os.getcwd(), os.pardir)
        if DirectoryControlWidget.is_valid(control_instance):
            current_control_value = unicode(control_instance.path.text())

        # Create a dialogue to select a directory
        folder = QtGui.QFileDialog.getExistingDirectory(
            control_instance, "Open directory", current_control_value)

        # Set the selected directory to the path sub control
        control_instance.path.setText(unicode(folder))
