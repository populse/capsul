#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import logging
from functools import partial
from traits.api import Instance

# Define the logger
logger = logging.getLogger(__name__)

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.utils.functiontools import SomaPartial
from soma.controller import trait_ids
from soma.controller import Controller
from soma.sorted_dictionary import OrderedDict

# Capsul import
from capsul.qt_gui.controller_widget import ControllerWidget

# Qt import
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

QtCore.QResource.registerResource(os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'resources', 'widgets_icons.rcc'))

class DictController(Controller):
    """ Dummy dict controller to simplify the creation of a dict widget
    """
    pass


class DictControlWidget(object):
    """ Control to enter a dict of items.
    """

    ###########################################################################
    # Public members
    ###########################################################################

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control values are correct.

        If the new dict controls values are not correct, the backroung
        color of each control in the dict will be red.

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
        """ Check if a controller widget dict control is filled correctly.

        Parameters
        ----------
        cls: DictControlWidget (mandatory)
            a DictControlWidget control
        control_instance: QFrame (mandatory)
            the control widget we want to validate
        """
        pass

    @staticmethod
    def add_callback(callback, control_instance):
        """ Method to add a callback to the control instance when the dict
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
    def create_widget(parent, control_name, control_value, trait,
                      label_class=None):
        """ Method to create the dict widget.

        Parameters
        ----------
        parent: QWidget (mandatory)
            the parent widget
        control_name: str (mandatory)
            the name of the control we want to create
        control_value: dict of items (mandatory)
            the default control value
        trait: Tait (mandatory)
            the trait associated to the control
        label_class: Qt widget class (optional, default: None)
            the label widget will be an instance of this class. Its constructor
            will be called using 2 arguments: the label string and the parent
            widget.

        Returns
        -------
        out: 2-uplet
            a two element tuple of the form (control widget: ,
            associated labels: (a label QLabel, the tools QWidget))
        """
        # Get the inner trait: expect only one inner trait
        # note: trait.inner_traits might be a method (ListInt) or a tuple
        # (List), whereas trait.handler.inner_trait is always a method
        if len(trait.handler.inner_traits()) != 2:
            raise Exception(
                "Expect two inner traits in Dict control. Trait '{0}' "
                "inner traits are '{1}'.".format(
                    control_name, trait.inner_traits))
        inner_trait = trait.handler.inner_traits()[1]

        # Create the dict widget: a frame
        frame = QtGui.QFrame(parent=parent)
        frame.setFrameShape(QtGui.QFrame.StyledPanel)

        # Create tools to interact with the dict widget: expand or collapse -
        # add a dict item - remove a dict item
        tool_widget = QtGui.QWidget(parent)
        layout = QtGui.QHBoxLayout()
        layout.addStretch(1)
        tool_widget.setLayout(layout)
        # Create the tool buttons
        resize_button = QtGui.QToolButton()
        add_button = QtGui.QToolButton()
        layout.addWidget(resize_button)
        layout.addWidget(add_button)
        # Set the tool icons
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/capsul_widgets_icons/add")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        add_button.setIcon(icon)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/capsul_widgets_icons/nav_down")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        resize_button.setIcon(icon)

        # Create a new controller that contains length 'control_value' inner
        # trait elements
        controller = DictController()
        for name, inner_control_values in control_value.iteritems():
            controller.add_trait(str(name), inner_trait)
            setattr(controller, str(name), inner_control_values)

        # Create the associated controller widget
        controller_widget = ControllerWidget(controller, parent=frame,
                                             live=True, editable_labels=True)

        # Store some parameters in the dict widget
        frame.inner_trait = inner_trait
        frame.trait = trait
        frame.controller = controller
        frame.controller_widget = controller_widget
        frame.connected = False

        # Add the dict controller widget to the dict widget
        frame.setLayout(controller_widget.layout())

        # Set some callback on the dict control tools
        # Resize callback
        resize_hook = partial(
            DictControlWidget.expand_or_collapse, frame, resize_button)
        resize_button.clicked.connect(resize_hook)
        # Add dict item callback
        add_hook = partial(
            DictControlWidget.add_dict_item, parent, control_name, frame)
        add_button.clicked.connect(add_hook)

        # Create the label associated with the dict widget
        control_label = trait.label
        if control_label is None:
            control_label = control_name
        if label_class is None:
            label_class = QtGui.QLabel
        if control_label is not None:
            label = label_class(control_label, parent)
        else:
            label = None

        controller_widget.main_controller_def = (DictControlWidget, parent,
                                                 control_name, frame)
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
        # Get the dict widget inner controller values
        new_trait_value = dict([
            (name, getattr(control_instance.controller, name))
            for name in control_instance.controller.user_traits()])

        # Update the 'control_name' parent controller value
        setattr(controller_widget.controller, control_name,
                new_trait_value)
        logger.debug(
            "'DictControlWidget' associated controller trait '{0}' has "
            "been updated with value '{1}'.".format(
                control_name, new_trait_value))

    @classmethod
    def update_controller_widget(cls, controller_widget, control_name,
                                 control_instance):
        """ Update one element of the dict controller widget.

        At the end the dict controller widget user editable parameter with the
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
        if control_name in controller_widget.controller.user_traits():

            # Get the dict widget current connection status
            was_connected = control_instance.connected

            # Disconnect the dict controller and the inner dict controller
            cls.disconnect(controller_widget, control_name, control_instance)
            control_instance.controller_widget.disconnect()

            # Get the 'control_name' dict value from the top dict controller
            trait_value = getattr(controller_widget.controller, control_name)

            # Get the number of dict elements in the controller associated
            # with the current dict control
            widget_traits = control_instance.controller.user_traits()

            # Parameter that is True if a user trait associated with the
            # current dict control has changed
            user_traits_changed = False

            # Special case: some traits have been deleted to the top controller
            # Need to remove to the inner dict controller some traits
            for trait_name in widget_traits:
                if trait_name not in trait_value:
                    control_instance.controller.remove_trait(trait_name)
                    # Notify that some traits of the inner dict controller have
                    # been deleted
                    user_traits_changed = True

            # Special case: some new traits have been added to the top
            # controller
            # Need to add to the inner dict controller some traits
            # with type 'inner_trait'
            for trait_name in trait_value:
                if trait_name not in widget_traits:
                    control_instance.controller.add_trait(
                        trait_name, control_instance.inner_trait)
                    # Notify that some traits of the inner dict controller
                    # have been added
                    user_traits_changed = True

            # Update the controller associated with the current control
            for trait_name, value in trait_value.iteritems():
                setattr(control_instance.controller, trait_name, value)

            # Connect the inner dict controller
            control_instance.controller_widget.connect()

            # Emit the 'user_traits_changed' signal if necessary
            if user_traits_changed:
                control_instance.controller.user_traits_changed = True

                logger.debug(
                    "'DictControlWidget' inner controller has been updated:"
                    "old size '{0}', new size '{1}'.".format(
                        len(widget_traits), len(trait_value)))

            # Restore the previous dict controller connection status
            if was_connected:
                cls.connect(controller_widget, control_name, control_instance)

        else:
            logger.error("oups")
            #print cls, controller_widget, control_name, control_instance
            #print control_instance.controller
            #print control_instance.controller.user_traits()

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect a 'List' controller trait and a 'DictControlWidget'
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

            # Update the dict item when one of his associated controller trait
            # changed.
            # Hook: function that will be called to update the controller
            # associated with a dict widget when a dict widget inner controller
            # trait is modified.
            dict_controller_hook = SomaPartial(
                cls.update_controller, controller_widget, control_name,
                control_instance)

            # Go through all dict widget inner controller user traits
            for trait_name in control_instance.controller.user_traits():

                # And add the callback on each user trait
                control_instance.controller.on_trait_change(
                    dict_controller_hook, trait_name)
                logger.debug("Item '{0}' of a 'DictControlWidget', add "
                              "a callback on inner controller trait "
                              "'{0}'.".format(control_name, trait_name))

            # Update the dict controller widget.
            # Hook: function that will be called to update the specific widget
            # when a trait event is detected on the dict controller.
            controller_hook = SomaPartial(
                cls.update_controller_widget, controller_widget, control_name,
                control_instance)

            # When the 'control_name' controller trait value is modified,
            # update the corresponding control
            controller_widget.controller.on_trait_change(
                controller_hook, control_name)

            # Update the dict connection status
            control_instance._controller_connections = (
                dict_controller_hook, controller_hook)
            logger.debug("Add 'Dict' connection: {0}.".format(
                control_instance._controller_connections))

            # Connect also all dict items
            inner_controls = control_instance.controller_widget._controls
            for (inner_control_name,
                 inner_control) in inner_controls.iteritems():

                # Unpack the control item
                inner_control_instance = inner_control[2]
                inner_control_class = inner_control[1]

                # Call the inner control connect method
                inner_control_class.connect(
                    control_instance.controller_widget, inner_control_name,
                    inner_control_instance)

            # Update the dict control connection status
            control_instance.connected = True

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect a 'List' controller trait and a 'DictControlWidget'
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

            # Get the stored widget and controller hooks
            (dict_controller_hook,
             controller_hook) = control_instance._controller_connections

            # Remove the controller hook from the 'control_name' trait
            controller_widget.controller.on_trait_change(
                controller_hook, control_name, remove=True)

            # Remove the dict controller hook associated with the controller
            # traits
            for trait_name in control_instance.controller.user_traits():
                control_instance.controller.on_trait_change(
                    dict_controller_hook, trait_name, remove=True)

            # Delete the trait - control connection we just remove
            del control_instance._controller_connections

            # Disconnect also all dict items
            inner_controls = control_instance.controller_widget._controls
            for (inner_control_name,
                 inner_control) in inner_controls.iteritems():

                # Unpack the control item
                inner_control_instance = inner_control[2]
                inner_control_class = inner_control[1]

                # Call the inner control disconnect method
                inner_control_class.disconnect(
                    control_instance.controller_widget, inner_control_name,
                    inner_control_instance)

            # Update the dict control connection status
            control_instance.connected = False

    ###########################################################################
    # Callbacks
    ###########################################################################

    @staticmethod
    def add_dict_item(controller_widget, control_name, control_instance):
        """ Append one element in the dict controller widget.

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
        # Get a new key name
        trait_name = 'new_item'
        i = 1
        while control_instance.controller.trait(trait_name):
            trait_name = 'new_item_%d' % i
            i += 1

        was_connected = controller_widget.connected
        if was_connected:
            controller_widget.disconnect()
        # Add the new trait to the inner list controller
        control_instance.controller.add_trait(
            trait_name, control_instance.inner_trait)
        DictControlWidget.update_controller(
            controller_widget, control_name, control_instance)
        if was_connected:
            controller_widget.connect()

        # update interface
        control_instance.controller_widget.update_controls()

        logger.debug("Add 'DictControlWidget' '{0}' new trait "
                      "callback.".format(trait_name))

    @staticmethod
    def expand_or_collapse(control_instance, resize_button):
        """ Callback to expand or collapse a 'DictControlWidget'.

        Parameters
        ----------
        control_instance: QFrame (mandatory)
            the dict widget item
        resize_button: QToolButton
            the signal sender
        """
        # Change the icon depending on the button status
        icon = QtGui.QIcon()

        # Hide the control
        if control_instance.isVisible():
            control_instance.hide()
            icon.addPixmap(QtGui.QPixmap(_fromUtf8(
                ":/capsul_widgets_icons/nav_right")),
                QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Show the control
        else:
            control_instance.show()
            icon.addPixmap(QtGui.QPixmap(_fromUtf8(
                ":/capsul_widgets_icons/nav_down")),
                QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Set the new button icon
        resize_button.setIcon(icon)
