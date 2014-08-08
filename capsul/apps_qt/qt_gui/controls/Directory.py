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
from functools import partial

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore

# Capsul import
from File import FileCreateWidget


class DirectoryCreateWidget(FileCreateWidget):

    @staticmethod
    def file_dialog(controller_widget, name, attribute_widget):
        value = QtGui.QFileDialog.getExistingDirectory(controller_widget, 'Select a directory', '',
                                                       options=QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontUseNativeDialog)
        setattr(controller_widget.controller, name, unicode(value))


def find_function_viewer(name_viewer):
    return GlobalNaming().get_object(name_viewer)
