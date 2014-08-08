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
from soma.utils.functiontools import SomaPartial



class EnumControlWidget(object):
    """ Control to select a value from a list.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control value is correct.
        """
        return True

    @classmethod
    def check(cls, control_instance):
        """ Check if a controller widget control is filled correctly.

        Parameters
        ----------
        cls: EnumControlWidget (mandatory)
            an EnumControlWidget control
        control_instance: QComboBox (mandatory)
            the control widget we want to validate
        """
        # Hook: function that will be called to check for typo 
        # when a 'textEdited' qt signal is emited
        widget_callback = partial(cls.is_valid, control_instance)

        # Execute manually the first time the control check method
        widget_callback()

        # When a qt 'textEdited' signal is emited, check if the new
        # user value is correct
        control_instance.textChanged.connect(widget_callback)

    @staticmethod
    def create_widget(parent, control_name, control_label, control_value):
        """ Method to create the widget.

        Parameters
        ----------
        parent: QWidget (mandatory)
            the parent widget
        control_name: str (mandatory)
            the name of the control we want to create
        control_label: str (mandatory)
            the label asssociated with the control
        control_value: str (mandatory)
            the default control value, here the enum values

        Returns
        -------
        out: 2-uplet
            a two element tuple of the form (control widget: QComboBox,
            associated label: QLabel)
        """
        # Create the widget that will be used to select a value
        widget = QtGui.QComboBox(parent)

        # Save the possible choices
        widget._choices = control_label

        # Set the enum list items to the widget
        for item in control_label:
            widget.addItem(item)

        # Select the default value
        # If the default value is not in the enum list, pick the first item
        # of the enum list
        if control_value not in control_label:
            widget.setCurrentIndex(0)
        else:
            widget.setCurrentIndex(control_label.index(control_value))

        # Create the label associated with the enum widget
        if control_name is not None:
            label = QtGui.QLabel(control_name, parent)
        else:
            label = None

        return (widget, label)

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
        control_instance: StrControlWidget (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        setattr(controller_widget.controller, control_name,
                control_instance._choices[control_instance.currentIndex()])

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
        control_instance: StrControlWidget (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        # Get the controller trait value
        controller_value = getattr(
            controller_widget.controller, control_name, None)

        # If the controller value is not empty, update the controller widget
        # associated control
        if controller_value is not None:
            control_instance.setCurrentIndex(
                control_instance._choices.index(controller_value))

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect an 'Enum' controller trait and an 'EnumControlWidget'
        controller widget control.

        Parameters
        ----------
        cls: EnumControlWidget (mandatory)
            an EnumControlWidget control
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str (mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QComboBox (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        # Update one element of the controller.
        # Hook: function that will be called to update a specific 
        # controller trait when an 'activated' qt signal is emited
        widget_hook = partial(cls.update_controller, controller_widget,
                              control_name, control_instance)

        # When a qt 'activated' signal is emited, update the 
        # 'control_name' controller trait value
        control_instance.connect(
            control_instance, QtCore.SIGNAL('activated( int )'),
            widget_hook)

        # Update one element of the controller widget.
        # Hook: function that will be called to update the specific widget 
        # when a trait event is detected.
        controller_hook = SomaPartial(
            cls.update_controller_widget, controller_widget, control_name,
            control_instance)

        # When the 'control_name' controller trait value is modified, update
        # the corresponding control
        controller_widget.controller.on_trait_change(
            controller_hook, name=control_name)

        # Store the trait - control connection we just build
        control_instance._controller_connections = (
            widget_hook, controller_hook)
        

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect an 'Enum' controller trait and an 'EnumControlWidget'
        controller widget control.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QComboBox (mandatory)
            the instance of the controller widget control we want to synchronize
            with the controller
        """
        # Get the stored widget and controller hooks
        widget_hook, controller_hook = attribute_widget._controller_connections

        # Remove the controller hook from the 'control_name' trait
        controller_widget.controller.on_trait_change(
            controller_hook, name=control_name, remove=True)

        # Remove the widget hook associated with the qt 'activated'
        # signal
        attribute_widget.disconnect(
            control_instance, QtCore.SIGNAL('activated( int )'),
            widget_hook)

        # Delete the trait - control connection we just remove
        del attribute_widget._controller_connections
