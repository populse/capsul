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
import sys
import os

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.functiontools import partial

# Capsul import
from capsul.qt_gui.controller_widget import ControllerWidget

# Qt import
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

QtCore.QResource.registerResource(os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'resources', 'widgets_icons.rcc'))


class ControllerControlWidget(object):
    """ Control to enter an instance of controller.
    """

    ###########################################################################
    # Public members
    ###########################################################################

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control values are correct.

        If the new controller controls values are not correct, the backroung
        color of each control in the controller will be red.

        Parameters
        ----------
        control_instance: QFrame (mandatory)
            the control widget we want to validate

        Returns
        -------
        valid: bool
            True if the control values are valid,
            False otherwise
        """
        # Initilaized the output
        valid = True

        # Go through all the controller widget controls
        controller_widget = control_instance.controller_widget
        for control_name, control in controller_widget._controls.iteritems():

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # Call the current control specific check method
            valid = control_class.is_valid(control_instance)

            # Stop checking if a wrong control has been found
            if not valid:
                break

        return valid

    @classmethod
    def check(cls, control_instance):
        """ Check if a controller widget controller control is filled correctly.

        Parameters
        ----------
        cls: ControllerControlWidget (mandatory)
            a ControllerControlWidget control
        control_instance: QFrame (mandatory)
            the control widget we want to validate
        """
        pass

    @staticmethod
    def add_callback(callback, control_instance):
        """ Method to add a callback to the control instance when the controller 
        trait is modified

        Parameters
        ----------
        callback: @function (mandatory)
            the function that will be called when a 'textChanged' signal is
            emited.
        control_instance: QFrame (mandatory)
            the control widget we want to validate
        """
        pass

    @staticmethod
    def create_widget(parent, control_name, control_value, trait):
        """ Method to create the controller widget.

        Parameters
        ----------
        parent: QWidget (mandatory)
            the parent widget
        control_name: str (mandatory)
            the name of the control we want to create
        control_value: instance of Controller (mandatory)
            the default control value
        trait: Tait (mandatory)
            the trait associated to the control

        Returns
        -------
        out: 2-uplet
            a two element tuple of the form (control widget: ,
            associated labels: (a label QLabel, the tools QWidget))
        """
        # Create the list widget: a frame
        frame = QtGui.QFrame(parent=parent)
        frame.setFrameShape(QtGui.QFrame.StyledPanel)

        # Create tools to interact with the list widget: expand or collapse -
        # add a list item - remove a list item
        tool_widget = QtGui.QWidget(parent)
        layout = QtGui.QHBoxLayout()
        layout.addStretch(1)
        tool_widget.setLayout(layout)
        # Create the tool buttons
        resize_button = QtGui.QToolButton()
        layout.addWidget(resize_button)
        # Set the tool icons
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(
            _fromUtf8(":/capsul_widgets_icons/nav_down")),
            QtGui.QIcon.Normal, QtGui.QIcon.Off)
        resize_button.setIcon(icon)

        # Create the associated controller widget
        controller_widget = ControllerWidget(control_value, parent=frame,
                                             live=True)

        # Store some parameters in the list widget
        frame.trait = trait
        frame.controller = control_value
        frame.controller_widget = controller_widget
        frame.connected = False

        # Add the list controller widget to the list widget
        frame.setLayout(controller_widget.layout())

        # Set some callback on the controller control tools
        # Resize callback
        resize_hook = partial(
            ControllerControlWidget.expand_or_collapse, frame, resize_button)
        resize_button.clicked.connect(resize_hook)

        # Create the label associated with the controller widget
        control_label = trait.label
        if control_label is None:
            control_label = control_name
        if control_label is not None:
            label = QtGui.QLabel(control_label, parent)
        else:
            label = None

        return (frame, (label, tool_widget))

    @staticmethod
    def update_controller(controller_widget, control_name, control_instance,
                          *args, **kwarg):
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
        control_instance: QFrame (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        control_instance.controller_widget.update_controller()

    @classmethod
    def update_controller_widget(cls, controller_widget, control_name,
                                 control_instance):
        """ Update one element of the controller control widget.

        At the end the controller control widget user editable parameter with the
        name 'control_name' will match the controller trait value with the same
        name.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QFrame (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # One callback has not been removed properly
        control_instance.controller_widget.update_controller_widget()

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect a 'Controller' controller trait and a 'ControllerControlWidget'
        controller widget control.

        Parameters
        ----------
        cls: StrControlWidget (mandatory)
            a StrControlWidget control
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str (mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QFrame (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Check if the control is connected
        if not control_instance.connected:
            control_instance.controller_widget.connect()
            # Update the list control connection status
            control_instance.connected = True

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect a 'Controller' controller trait and a 'ControllerControlWidget'
        controller widget control.

        Parameters
        ----------
        cls: StrControlWidget (mandatory)
            a StrControlWidget control
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str (mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QFrame (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Check if the control is connected
        if control_instance.connected:
            control_instance.controller_widget.disconnect()
            # Update the list control connection status
            control_instance.connected = False

    @staticmethod
    def expand_or_collapse(control_instance, resize_button):
        """ Callback to expand or collapse a 'ControllerControlWidget'.

        Parameters
        ----------
        control_instance: QFrame (mandatory)
            the list widget item
        resize_button: QToolButton
            the signal sender
        """
        # Change the icon depending on the button status
        icon = QtGui.QIcon()

        # Hide the control
        if control_instance.isVisible():
            control_instance.hide()
            icon.addPixmap(
                QtGui.QPixmap(_fromUtf8(":/capsul_widgets_icons/nav_right")),
                QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Show the control
        else:
            control_instance.show()
            icon.addPixmap(
                QtGui.QPixmap(_fromUtf8(":/capsul_widgets_icons/nav_down")),
                QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Set the new button icon
        resize_button.setIcon(icon)
