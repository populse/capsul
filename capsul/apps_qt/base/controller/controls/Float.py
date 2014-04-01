#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from String import String
from capsul.apps_qt.qt_backend import QtCore

class Float(String):
    """ Control to enter a float.
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
        # Inheritance
        if (value != None and not isinstance(value, str)):
            value = repr(value)
        String.__init__(self, trait_name, value, is_enabled)

    def _validate(self):
        """ Check if a float has been entered in the text field and
        set a flag accordingly.
        """
        value = self._value.replace(".", "", 1)
        p = self._text.palette()
        if value.isdigit():
            p.setColor(self._text.backgroundRole(), QtCore.Qt.white)
            self._is_valid = True
        else:
            p.setColor(self._text.backgroundRole(), QtCore.Qt.red)
            self._is_valid = False
        self._text.setPalette(p)

    def _set_value(self, value):
        """ Method to update the control status.

        Parameters
        ----------
        value: str (mandatory)
            a string representation of a float
        """
        self._value = value or ""
        self._validate()
        if self._is_valid:
            self._value = float(self._value)
            self.notify_observers("value", value=self._value,
                                  trait_name=self._trait_name)

