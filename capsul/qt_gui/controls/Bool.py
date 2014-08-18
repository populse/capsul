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
from soma.qt_gui.qt_backend import QtGui
from soma.utils.functiontools import SomaPartial


class BoolControlWidget(object):
    """ Control to set or unset an option.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control value is correct.

        Parameters
        ----------
        control_instance: QCheckBox (mandatory)
            the control widget we want to validate

        Returns
        -------
        out: bool
            always True since the control value is always valid
        """
        return True

    @classmethod
    def check(cls, control_instance):
        """ Check if a controller widget control is filled correctly.

        Parameters
        ----------
        cls: BoolControlWidget (mandatory)
            a BoolControlWidget control
        control_instance: QCheckBox (mandatory)
            the control widget we want to validate
        """
        # Hook: function that will be called to check for typo
        # when a 'clicked' qt signal is emited
        widget_callback = partial(cls.is_valid, control_instance)

        # Execute manually the first time the control check method
        widget_callback()

        # When a qt 'clicked' signal is emited, check if the new
        # user value is correct
        control_instance.clicked.connect(widget_callback)

    @staticmethod
    def create_widget(parent, control_name, control_value, trait):
        """ Method to create the bool widget.

        Parameters
        ----------
        parent: QWidget (mandatory)
            the parent widget
        control_name: str (mandatory)
            the name of the control we want to create
        control_value: str (mandatory)
            the default control value
        trait: Tait (mandatory)
            the trait associated to the control

        Returns
        -------
        out: 2-uplet
            a two element tuple of the form (control widget: QLineEdit,
            associated label: QLabel)
        """
        # Create the widget that will be used to select an option
        widget = QtGui.QCheckBox(parent)

        # Add a widget parameter to tell us if the widget is already connected
        widget.connected = False

        # Create the label associated with the bool widget
        control_label = trait.label
        if control_label is None:
            control_label = control_name
        if control_label is not None:
            label = QtGui.QLabel(control_label, parent)
        else:
            label = None

        return (widget, label)

    @staticmethod
    def update_controller(controller_widget, control_name, control_instance,
                          *args, **kwargs):
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
        control_instance: QCheckBox (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Update the controller only if the control is valid
        if BoolControlWidget.is_valid(control_instance):

            # Get the control value
            new_trait_value = bool(control_instance.isChecked())

            # Set the control value to the controller associated trait
            setattr(controller_widget.controller, control_name,
                    new_trait_value)
            logging.debug(
                "'BoolControlWidget' associated controller trait '{0}' has "
                "been updated with value '{1}'.".format(
                    control_name, new_trait_value))

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
        control_instance: QCheckBox (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Get the trait value
        new_controller_value = getattr(
            controller_widget.controller, control_name, False)

        # Set the trait value to the bool control
        control_instance.setChecked(new_controller_value)
        logging.debug("'BoolControlWidget' has been updated with value "
                      "'{0}'.".format(new_controller_value))

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect a 'Bool' controller trait and a 'BoolControlWidget'
        controller widget control.

        Parameters
        ----------
        cls: BoolControlWidget (mandatory)
            a BoolControlWidget control
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str (mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QCheckBox (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Check if the control is connected
        if not control_instance.connected:

            # Update one element of the controller.
            # Hook: function that will be called to update a specific
            # controller trait when a 'textChanged' qt signal is emited
            widget_hook = partial(cls.update_controller, controller_widget,
                                  control_name, control_instance)

            # When a qt 'clicked' signal is emited, update the
            # 'control_name' controller trait value
            control_instance.clicked.connect(widget_hook)

            # Update the control.
            # Hook: function that will be called to update the control value
            # when the 'control_name' controller trait is modified.
            controller_hook = SomaPartial(
                cls.update_controller_widget, controller_widget, control_name,
                control_instance)

            # When the 'control_name' controller trait value is modified,
            # update the corresponding control
            controller_widget.controller.on_trait_change(
                controller_hook, name=control_name)

            # Store the trait - control connection we just build
            control_instance._controller_connections = (
                widget_hook, controller_hook)
            logging.debug("Add 'String' connection: {0}.".format(
                control_instance._controller_connections))

            # Update the control connection status
            control_instance.connected = True

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect a 'Bool' controller trait and a 'BoolControlWidget'
        controller widget control.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QCheckBox (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Check if the control is connected
        if control_instance.connected:

            # Get the stored widget and controller hooks
            (widget_hook,
             controller_hook) = control_instance._controller_connections

            # Remove the controller hook from the 'control_name' trait
            controller_widget.controller.on_trait_change(
                controller_hook, name=control_name, remove=True)

            # Remove the widget hook associated with the qt 'clicked' signal
            control_instance.clicked.disconnect(widget_hook)

            # Delete the trait - control connection we just remove
            del control_instance._controller_connections

            # Update the control connection status
            control_instance.connected = False
