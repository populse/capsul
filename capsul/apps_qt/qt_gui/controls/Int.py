#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import re

# Soma import
from soma.qt_gui.qt_backend import QtCore
from Str import StrControlWidget


class IntControlWidget(StrControlWidget):
    """ Control to enter a float.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control value is correct.

        If the new entered value is not correct, the backroung control color
        will be red.

        Parameters
        ----------
        control_instance: QLineEdit (mandatory)
            the control widget we want to validate
        """
        # Get the current control palette
        control_palette = control_instance.palette()

        # Get the control current value
        control_value = re.sub("^([-+])", "", control_instance.text(), count=1)

        # If the control value contains only digits, the control is valid and
        # the backgound color of the control is white
        is_valid = False 
        if control_value.isdigit():
            control_palette.setColor(
                control_instance.backgroundRole(), QtCore.Qt.white)
            is_valid = True

        # If the control value contains some characters, the control is not
        # valid and the backgound color of the control is red
        else:
            control_palette.setColor(
                control_instance.backgroundRole(), QtCore.Qt.red)

        # Set the new palette to the control instance
        control_instance.setPalette(control_palette)

        return is_valid

    @staticmethod
    def update_controller(controller_widget, control_name, control_instance):
        """ Update one element of the controller.

        At the end the controller trait value with the name 'control_name'
        will match the controller widget user parameters defined in
        'control_instance'.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: FloatControlWidget (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        setattr(controller_widget.controller, control_name,
                int(control_instance.text()))

    @staticmethod
    def update_controller_widget(controller_widget, control_name,
                                 control_instance):
        """ Update one element of the controller widget.

        At the end the controller widget user editable parameter with the
        name 'control_name' will match the controller trait value with the same
        name.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: FloatControlWidget (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        control_instance.setText(
            unicode(getattr(controller_widget.controller, control_name, 0)))
