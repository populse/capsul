#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
import sys
import traceback

from capsul.apps_qt.qt_backend import QtGui, QtCore
from observable import Observable

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

from File import File
from Float import Float


class List(QtGui.QWidget, Observable):
    """ Control to enter a list of elments of dynamic types.
    The properties "value" and "valid" contain the current value of
    the control and a bool set to True if the control is filled
    correctely respectivelly.
    """

    def __init__(self, inner_controls, trait_name, value=None,
                 is_enabled=True):
        """ Method to initialize a List control.

        Parameters
        ----------
        inner_controls: str (madatory)
            the description of the list content, each depth beeing
            represented with a '_'
        trait_name: str (mandatory)
            the corresponding trait name
        value: str (optional)
            the default string
        is_enabled: bool (mandatory)
            parameter to activate or unactivate the control
        """
        # Default parameters
        self._trait_name = trait_name
        self._inner_controls = inner_controls
        self._value = None
        self._default_value = value or []
        self._is_valid = False
        self._controls = []
        self._del_buttons = []
        self._is_enabled = is_enabled

        # Inheritance
        Observable.__init__(self, ["value", "update"])
        super(List, self).__init__()

        # Build control
        self._layout = QtGui.QVBoxLayout()
        self._grid_layout = QtGui.QGridLayout()
        self._initUI()
        self._layout.addLayout(self._grid_layout)
        self.setLayout(self._layout)

        # Set default status
        if self._default_value == []:
            self._set_value(self._default_value)
        else:
            for current_value in self._default_value:
                self._addControl(current_value)

    def _initUI(self):
        """ Build the control user interface.
        """
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self._layout.setSpacing(0)
        self._layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._add_control = QtGui.QToolButton(self)
        self._add_control.setEnabled(self._is_enabled)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/add")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self._add_control.setIcon(icon)
        self._add_control.clicked.connect(self._onAddListClicked)

        self._layout.addWidget(self._add_control)

    def _updateUI(self, row_to_delete):
        """ Delete a row from the control
        Clean the grid layout
        """
        # first column
        to_remove_control = self._grid_layout.itemAtPosition(
            row_to_delete, 0)
        widget = to_remove_control.widget()
        self._grid_layout.removeWidget(widget)
        widget.deleteLater()

        # second column
        to_remove_control = self._grid_layout.itemAtPosition(
            row_to_delete, 1)
        widget = to_remove_control.widget()
        self._grid_layout.removeWidget(widget)
        widget.deleteLater()

    def _onAddListClicked(self):
        """ Event to create a new control
        """
        self._addControl()
        self.notify_observers("update")

    def _addControl(self, value=None):
        """ Create a new control
        """
        control = self._create_control(value)
        button = QtGui.QToolButton(self)
        button.setEnabled(self._is_enabled)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/delete")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        button.setIcon(icon)
        button.clicked.connect(self._onDelListClicked)

        self._del_buttons.append(button)

        index = len(self._controls)
        self._grid_layout.addWidget(control, index - 1, 0)
        self._grid_layout.addWidget(button, index - 1, 1)

    def _onDelListClicked(self):
        """ Delete a control from the list
        """
        # Find the botton the send the signal
        clickedButton = self.sender()

        # Remove the associted control
        index = self._del_buttons.index(clickedButton)
        self._del_buttons[index] = None
        self._controls[index] = None

        # Recreate the upper container
        self._updateUI(index)

        # Notify observers if all remaining controls are valid
        self._on_value_changed()
        self.notify_observers("update")

    def _validate(self):
        """ Check if the list contains valid elements.
        """
        valid_controls = [control for control in self._controls if control]
        all_controls_valid = True
        for control in valid_controls:
            all_controls_valid = all_controls_valid and control.valid
        self._is_valid = all_controls_valid

    def _on_value_changed(self, signal=None):
        """ Method to update list control when an inner control changed
        """
        valid_controls = [control for control in self._controls if control]
        result = []
        for control in valid_controls:
            result.append(control.value)
        self._set_value(result)

    def _create_control(self, value=None):
        """Create the inner control
        """
        parameter = self._inner_controls.split("_")
        expression = "{0}(".format(parameter[0])
        if parameter[0] == "List":
            inner_controls = "_".join(parameter[1:])
            expression += "inner_controls, "
        expression += "self._trait_name, "
        if value != None:
            expression += "value, "
        expression += "is_enabled=self._is_enabled, "
        expression += ")"
        try:
            # Create control
            control = eval(expression)

            # Add observer
            control.add_observer("value", self._on_value_changed)

            # Store the created control
            self._controls.append(control)
        except:
            logging.error("Could not create List control from"
                          "expression \"{0}\"".format(expression))
            exc_info = sys.exc_info()
            logging.error("".join(traceback.format_exception(*exc_info)))
            return

        return control

    def _set_value(self, value):
        """ Method to update the control status.

        Parameters
        ----------
        value: list (mandatory)
            new list
        """
        self._value = value
        self._validate()
        if self._is_valid:
            self.notify_observers("value", value=value,
                                  trait_name=self._trait_name)

    value = property(lambda x: x._value, _set_value)
    valid = property(lambda x: x._is_valid)
