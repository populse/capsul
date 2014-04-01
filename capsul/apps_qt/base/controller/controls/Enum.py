#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################


from capsul.apps_qt.qt_backend import QtGui
from observable import Observable


class Enum(QtGui.QWidget, Observable):
    """ Control to select an option.
    The properties "value" and "valid" contain the current value
    of the control and a bool set to True if the control is filled
    """

    def __init__(self, initializer, trait_name, value=None, is_enabled=True):
        """ Method to initialize a File control.

        Parameters
        ----------
        initializer: list of string (mandatory)
            the desired options
        trait_name: str (mandatory)
            the corresponding trait name
        value: str (optional)
            the default option
        is_enabled: bool (mandatory)
            parameter to activate or unactivate the control
        """
        # Default parameters
        self._trait_name = trait_name
        self._value = None
        self._default_value = value
        self._is_valid = False
        self._choices = initializer
        self._is_enabled = is_enabled

        # Inheritance
        Observable.__init__(self, ["value"])
        super(Enum, self).__init__()

        # Build control
        self._layout = QtGui.QHBoxLayout()
        self._initUI()
        self.setLayout(self._layout)

        # Set default status
        self._set_value(value)

    def _initUI(self):
        """ Build the control user interface.
        """
        self.resize(1000, 27)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self._layout.setSpacing(0)
        self._layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._combo = QtGui.QComboBox(self)
        self._combo.setEnabled(self._is_enabled)
        for item in self._choices:
            self._combo.addItem(item)
        if self._default_value not in self._choices:
            self._combo.insertItem(0, "----Undefined----")
            self._combo.setCurrentIndex(0)
        else:
            self._combo.setCurrentIndex(
                self._choices.index(self._default_value))
        self._combo.activated[str].connect(self._onActivated)

        self._layout.addWidget(self._combo)

    def _onActivated(self, text):
        """ Event when a new option is selected.
        Update the status of the control accordingly to the user
        selected option.
        """
        if self._value not in self._choices:
            self._combo.removeItem(0)
        self._set_value(text)

    def _validate(self):
        """ Check if the selected option is valid set a flag accordingly.
        """
        if self._value in self._choices:
            self._is_valid = True
        else:
            self._is_valid = False

    def reset(self):
        """ Reset the control to his initiale value
        """
        if self._default_value not in self._choices:
            self._combo.insertItem(0, "----Undefined----")
            self._combo.setCurrentIndex(0)
        self._set_value(self._default_value)

    def _set_value(self, value):
        """ Method to update the control status.

        Parameters
        ----------
        value: str (mandatory)
            new option
        """
        self._value = value
        self._validate()
        if self._is_valid:
            self.notify_observers("value", value=value,
                                           trait_name=self._trait_name)

    value = property(lambda x: x._value, _set_value)
    valid = property(lambda x: x._is_valid)

