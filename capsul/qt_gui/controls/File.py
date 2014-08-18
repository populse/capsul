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
import os
from functools import partial

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.utils.functiontools import SomaPartial


class FileControlWidget(object):
    """ Control to enter a file.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control value is correct.

        If the new entered value is not correct, the backroung control color
        will be red.

        Parameters
        ----------
        control_instance: QWidget (mandatory)
            the control widget we want to validate

        Returns
        -------
        out: bool
            True if the control value is a file,
            False otherwise
        """
        # Get the current control palette
        control_palette = control_instance.path.palette()

        # Get the control current value
        control_value = control_instance.path.text()

        # If the control value contains a file, the control is valid and the
        # backgound color of the control is white
        is_valid = False
        if os.path.isfile(control_value):
            control_palette.setColor(
                control_instance.path.backgroundRole(), QtCore.Qt.white)
            is_valid = True

        # If the control value do not contains a file, the control is not valid
        # and the backgound color of the control is red
        else:
            control_palette.setColor(
                control_instance.path.backgroundRole(), QtCore.Qt.red)

        # Set the new palette to the control instance
        control_instance.path.setPalette(control_palette)

        return is_valid

    @classmethod
    def check(cls, control_instance):
        """ Check if a controller widget control is filled correctly.

        Parameters
        ----------
        cls: FileControlWidget (mandatory)
            a StrControlWidget control
        control_instance: QWidget (mandatory)
            the control widget we want to validate
        """
        # Hook: function that will be called to check for typo
        # when a 'textChanged' qt signal is emited
        widget_callback = partial(cls.is_valid, control_instance)

        # The first time execute manually the control check method
        widget_callback()

        # When a qt 'textChanged' signal is emited, check if the new
        # user value is correct
        control_instance.path.textChanged.connect(widget_callback)

    @staticmethod
    def create_widget(parent, control_name, control_value, trait):
        """ Method to create the file widget.

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
            a two element tuple of the form (control widget: QWidget with two
            elements, a QLineEdit in the 'path' parameter and a browse button
            in the 'browse' parameter, associated label: QLabel)
        """
        # Create the widget that will be used to select a file
        widget = QtGui.QWidget(parent)
        layout = QtGui.QHBoxLayout()
        layout.setSpacing(0)
        layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        # Create a widget to print the file path
        path = QtGui.QLineEdit(widget)
        layout.addWidget(path)
        widget.path = path
        # Create a browse button
        button = QtGui.QPushButton("...", widget)
        layout.addWidget(button)
        widget.browse = button

        # Add a widget parameter to tell us if the widget is already connected
        widget.connected = False

        # Set a callback on the browse button
        control_class = parent.get_control_class(trait)
        browse_hook = partial(control_class.onBrowseClicked, widget)
        widget.browse.clicked.connect(browse_hook)

        # Create the label associated with the string widget
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
        control_instance: QWidget (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Update the controller only if the control is valid
        control_class = controller_widget._controls[control_name][1]
        if control_class.is_valid(control_instance):

            # Get the control value
            new_trait_value = unicode(control_instance.path.text())

            # Set the control value to the controller associated trait
            setattr(controller_widget.controller, control_name,
                    new_trait_value)
            logging.debug(
                "'FileControlWidget' associated controller trait '{0}' has "
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
        control_instance: QWidget (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        """
        # Get the trait value
        new_controller_value = getattr(
            controller_widget.controller, control_name, "")

        # Set the trait value to the string control
        control_instance.path.setText(unicode(new_controller_value))
        logging.debug("'FileControlWidget' has been updated with value "
                      "'{0}'.".format(new_controller_value))

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect a 'File' controller trait and a 'FileControlWidget'
        controller widget control.

        Parameters
        ----------
        cls: FileControlWidget (mandatory)
            a StrControlWidget control
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str (mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QWidget (mandatory)
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

            # When a qt 'textChanged' signal is emited, update the
            # 'control_name' controller trait value
            control_instance.path.textChanged.connect(widget_hook)

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
            logging.debug("Add 'File' connection: {0}.".format(
                control_instance._controller_connections))

            # Update the control connection status
            control_instance.connected = True

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect a 'File' controller trait and a 'FileControlWidget'
        controller widget control.

        Parameters
        ----------
        controller_widget: ControllerWidget (mandatory)
            a controller widget that contains the controller we want to update
        control_name: str(mandatory)
            the name of the controller widget control we want to synchronize
            with the controller
        control_instance: QWidget (mandatory)
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

            # Remove the widget hook associated with the qt 'textChanged'
            # signal
            control_instance.path.textChanged.disconnect(widget_hook)

            # Delete the trait - control connection we just remove
            del control_instance._controller_connections

            # Update the control connection status
            control_instance.connected = False

    ###########################################################################
    # Callbacks
    ###########################################################################

    @staticmethod
    def onBrowseClicked(control_instance):
        """ Browse the file system and update the control instance accordingly.

        If a valid file path has already been entered the file dialogue will
        automatically point to the file folder, otherwise the current working
        directory is used.

        Parameters
        ----------
        control_instance: QWidget (mandatory)
            the file widget item
        """
        # Get the current file path
        current_control_value = os.getcwd()
        if FileControlWidget.is_valid(control_instance):
            current_control_value = unicode(control_instance.path.text())

        # Create a dialogue to select a file
        fname, _ = QtGui.QFileDialog.getOpenFileName(
            control_instance, "Open file", current_control_value)

        # Set the selected file path to the path sub control
        control_instance.path.setText(unicode(fname))
