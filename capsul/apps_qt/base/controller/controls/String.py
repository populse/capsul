#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.apps_qt.qt_backend import QtGui, QtCore
from observable import Observable


class String(QtGui.QWidget, Observable):
    """ Control to enter a string.
    The properties "value" and "valid" contain the current value of
    the control and a bool set to True if the control is filled
    correctely respectivelly.
    """

    def __init__(self, trait_name, value=None, is_enabled=True):
        """ Method to initialize a File control.

        Parameters
        ----------
        trait_name: str (mandatory)
            the corresponding trait name
        value: str (optional)
            the default string
        is_enabled: bool (mandatory)
            parameter to activate or unactivate the control
        """
        # Default parameters
        self._trait_name = trait_name
        self._value = None
        self._default_value = value or ""
        self._is_valid = False
        self._is_enabled = is_enabled

        # Inheritance
        Observable.__init__(self, ["value"])
        super(String, self).__init__()

        # Build control
        self._layout = QtGui.QHBoxLayout()
        self._initUI()
        self.setLayout(self._layout)
        self._text.setText(self._default_value)

        # Set default status
        self._set_value(value)

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

        self._text = QtGui.QLineEdit(self)
        self._text.setEnabled(self._is_enabled)
        self._text.textChanged.connect(self._onActivated)

        self._layout.addWidget(self._text)

    def _onActivated(self, text):
        """ Event when the text is entered.
        Update the status of the control accordingly to the user
        text.
        """
        self._set_value(self._text.text())

    def _validate(self):
        """ Check if the text entered is not empty and
        set a flag accordingly.
        """
        p = self._text.palette()
        if self._value != "":
            p.setColor(self._text.backgroundRole(), QtCore.Qt.white)
            self._is_valid = True
        else:
            p.setColor(self._text.backgroundRole(), QtCore.Qt.red)
            self._is_valid = False
        self._text.setPalette(p)

    def reset(self):
        """ Reset the control to his initiale value
        """
        self._text.setText(self._default_value)
        self._set_value(self._default_value)

    def _set_value(self, value):
        """ Method to update the control status.

        Parameters
        ----------
        value: str (mandatory)
            a text
        """
        self._value = value or ""
        self._validate()
        if self._is_valid:
            self.notify_observers("value", value=value,
                                  trait_name=self._trait_name)

    value = property(lambda x:x._value, _set_value)
    valid = property(lambda x:x._is_valid)

