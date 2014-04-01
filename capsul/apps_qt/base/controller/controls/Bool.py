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


class Bool(QtGui.QWidget, Observable):
    """ Control to set or unset an option.
    The properties "value" and "valid" contain the current value
    of the control and a bool set to True if the control is filled
    correctely respectivelly.
    """

    def __init__(self, trait_name, value=False, trait_item=None,
                 is_enabled=True):
        """ Method to initialize a File control.

        Parameters
        ----------
        trait_name: str (mandatory)
            the corresponding trait name
        value: str (optional)
            the default string
        trait_item: has_traits item (mandatory)
            parameter where the trait are stored
        is_enabled: bool (mandatory)
            parameter to activate or unactivate the control
        """
        # Default parameters
        self._trait_item = trait_item
        self._trait_name = trait_name
        self._value = None
        self._is_valid = False
        self._default_value = value
        self._is_enabled = is_enabled

        # Inheritance
        Observable.__init__(self, ["value"])
        super(Bool, self).__init__()

        # Build control
        self._layout = QtGui.QHBoxLayout()
        self._initUI()
        self.setLayout(self._layout)

        # Set default status
        self._set_value(self._default_value)

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

        self._check = QtGui.QCheckBox(self)
        self._check.setEnabled(self._is_enabled)
        self._check.clicked.connect(self._onActivated)
        self._check.setChecked(self._default_value)

        self._layout.addWidget(self._check)

    def _onActivated(self):
        """ Event when the checkbox is clicked.
        Update the status of the control accordingly to the user
        option.
        """
        self._set_value(self._check.isChecked())

    def _validate(self):
        """ The checkbox is always valid.
        """
        self._is_valid = True

    def reset(self):
        """ Reset the control to his initiale value
        """
        self._set_value(self._default_value)

    def _set_value(self, value):
        """ Method to update the control status.

        Parameters
        ----------
        value: bool (mandatory)
            the new checkbox value
        """
        self._value = value
        self._validate()
        if self._is_valid:
            self.notify_observers("value", value=value,
                                  trait_name=self._trait_name,
                                  trait_item=self._trait_item)

    value = property(lambda x: x._value, _set_value)
    valid = property(lambda x: x._is_valid)
