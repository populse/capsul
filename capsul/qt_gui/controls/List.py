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
from soma.controller import trait_ids
from soma.controller import Controller

# Capsul import
from capsul.qt_gui.controller_widget import ControllerWidget
from capsul.qt_apps.resources import icones

# Qt import
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


class ListController(Controller):
    """ Dummy list controller to simplify the creation of a list widget
    """
    pass


class ListControlWidget(object):
    """ Control to enter a list of items.
    """

    ###########################################################################
    # Public members
    ###########################################################################

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control values are correct.

        If the new list controls values are not correct, the backroung
        color of each control in the list will be red.

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
        """ Check if a controller widget list control is filled correctly.

        Parameters
        ----------
        cls: ListControlWidget (mandatory)
            a StrControlWidget control
        control_instance: QFrame (mandatory)
            the control widget we want to validate
        """
        pass

    @staticmethod
    def create_widget(parent, control_name, control_value, trait):
        """ Method to create the list widget.

        Parameters
        ----------
        parent: QWidget (mandatory)
            the parent widget
        control_name: str (mandatory)
            the name of the control we want to create
        control_value: list of items (mandatory)
            the default control value
        trait: Tait (mandatory)
            the trait associated to the control

        Returns
        -------
        out: 2-uplet
            a two element tuple of the form (control widget: ,
            associated labels: (a label QLabel, the tools QWidget))
        """
        # Get the inner trait: expect only one inner trait
        if len(trait.inner_traits) != 1:
            raise Exception(
                "Expect only one inner trait in List control. Current "
                "value is '{0}'.".format(trait.inner_traits))
        inner_trait = trait.inner_traits[0]

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
        add_button = QtGui.QToolButton()
        delete_button = QtGui.QToolButton()
        layout.addWidget(resize_button)
        layout.addWidget(add_button)
        layout.addWidget(delete_button)
        # Set the tool icons
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/add")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        add_button.setIcon(icon)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/delete")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        delete_button.setIcon(icon)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/nav_down")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        resize_button.setIcon(icon)

        # Create a new controller that contains length 'control_value' inner
        # trait elements
        controller = ListController()
        for cnt, inner_control_values in enumerate(control_value):
            controller.add_trait(str(cnt), inner_trait)
            setattr(controller, str(cnt), inner_control_values)

        # Create the associated controller widget
        controller_widget = ControllerWidget(controller, parent=frame,
                                             live=True)

        # Store some parameters in the list widget
        frame.inner_trait = inner_trait
        frame.trait = trait
        frame.controller = controller
        frame.controller_widget = controller_widget
        frame.connected = False

        # Add the list controller widget to the list widget
        frame.setLayout(controller_widget.layout())

        # Set some callback on the list control tools
        # Resize callback
        resize_hook = partial(
            ListControlWidget.expand_or_collapse, frame, resize_button)
        resize_button.clicked.connect(resize_hook)
        # Add list item callback
        add_hook = partial(
            ListControlWidget.add_list_item, parent, control_name, frame)
        add_button.clicked.connect(add_hook)
        # Delete list item callback
        delete_hook = partial(
            ListControlWidget.delete_list_item, parent, control_name, frame)
        delete_button.clicked.connect(delete_hook)

        # Create the label associated with the list widget
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
        # Get the list widget inner controller values
        new_trait_value = [
            getattr(control_instance.controller, str(i))
            for i in range(len(control_instance.controller.user_traits()))]

        # Update the 'control_name' parent controller value
        setattr(controller_widget.controller, control_name,
                new_trait_value)
        logging.debug(
            "'ListControlWidget' associated controller trait '{0}' has "
            "been updated with value '{1}'.".format(
                control_name, new_trait_value))

    @classmethod
    def update_controller_widget(cls, controller_widget, control_name,
                                 control_instance):
        """ Update one element of the list controller widget.

        At the end the list controller widget user editable parameter with the
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

            # Get the list widget current connection status
            was_connected = control_instance.connected

            # Disconnect the list controller and the inner list controller
            cls.disconnect(controller_widget, control_name, control_instance)
            control_instance.controller_widget.disconnect()

            # Get the 'control_name' list value from the top list controller
            trait_value = getattr(controller_widget.controller, control_name)

            # Get the number of list elements in the controller associated
            # with the current list control
            len_widget = len(control_instance.controller.user_traits())

            # Parameter that is True if a user trait associated with the
            # current list control has changed
            user_traits_changed = False

            # Special case: some traits have been deleted to the top controller
            if len(trait_value) < len_widget:

                # Need to remove to the inner list controller some traits
                for i in range(len(trait_value), len_widget):
                    control_instance.controller.remove_trait(str(i))

                # Notify that some traits of the inner list controller have
                # been deleted
                user_traits_changed = True

            # Special case: some new traits have been added to the top
            # controller
            elif len(trait_value) > len_widget:

                # Need to add to the inner list controller some traits
                # with type 'inner_trait'
                for i in range(len_widget, len(trait_value)):
                    control_instance.controller.add_trait(
                        str(i), control_instance.inner_trait)

                # Notify that some traits of the inner list controller
                # have been added
                user_traits_changed = True

            # Update the controller associated with the current control
            for i in range(len(trait_value)):
                setattr(control_instance.controller, str(i), trait_value[i])

            # Connect the inner list controller
            control_instance.controller_widget.connect()

            # Emit the 'user_traits_changed' signal if necessary
            if user_traits_changed:
                control_instance.controller.user_traits_changed = True

                logging.debug(
                    "'ListControlWidget' inner controller has been updated:"
                    "old size '{0}', new size '{1}'.".format(
                        len_widget, len(trait_value)))

            # Restore the previous list controller connection status
            if was_connected:
                cls.connect(controller_widget, control_name, control_instance)

        else:
            print "oups"
            print cls, controller_widget, control_name, control_instance
            print control_instance.controller
            print control_instance.controller.user_traits()

    @classmethod
    def connect(cls, controller_widget, control_name, control_instance):
        """ Connect a 'List' controller trait and a 'ListControlWidget'
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

            # Update the list item when one of his associated controller trait
            # changed.
            # Hook: function that will be called to update the controller
            # associated with a list widget when a list widget inner controller
            # trait is modified.
            list_controller_hook = SomaPartial(
                cls.update_controller, controller_widget, control_name,
                control_instance)

            # Go through all list widget inner controller user traits
            for trait_name in control_instance.controller.user_traits():

                # And add the callback on each user trait
                control_instance.controller.on_trait_change(
                    list_controller_hook, trait_name)
                logging.debug("Item '{0}' of a 'ListControlWidget', add "
                              "a callback on inner controller trait "
                              "'{0}'.".format(control_name, trait_name))

            # Update the list controller widget.
            # Hook: function that will be called to update the specific widget
            # when a trait event is detected on the list controller.
            controller_hook = SomaPartial(
                cls.update_controller_widget, controller_widget, control_name,
                control_instance)

            # When the 'control_name' controller trait value is modified,
            # update the corresponding control
            controller_widget.controller.on_trait_change(
                controller_hook, control_name)

            # Update the list connection status
            control_instance._controller_connections = (
                list_controller_hook, controller_hook)
            logging.debug("Add 'List' connection: {0}.".format(
                control_instance._controller_connections))

            # Connect also all list items
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

            # Update the list control connection status
            control_instance.connected = True

    @staticmethod
    def disconnect(controller_widget, control_name, control_instance):
        """ Disconnect a 'List' controller trait and a 'ListControlWidget'
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
            (list_controller_hook,
             controller_hook) = control_instance._controller_connections

            # Remove the controller hook from the 'control_name' trait
            controller_widget.controller.on_trait_change(
                controller_hook, control_name, remove=True)

            # Remove the list controller hook associated with the controller
            # traits
            for trait_name in control_instance.controller.user_traits():
                control_instance.controller.on_trait_change(
                    list_controller_hook, trait_name, remove=True)

            # Delete the trait - control connection we just remove
            del control_instance._controller_connections

            # Disconnect also all list items
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

            # Update the list control connection status
            control_instance.connected = False

    ###########################################################################
    # Callbacks
    ###########################################################################

    @staticmethod
    def add_list_item(controller_widget, control_name, control_instance):
        """ Append one element in the list controller widget.

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
        # Get the number of traits associated with the current list control
        # controller
        nb_of_traits = len(control_instance.controller.user_traits())
        trait_name = str(nb_of_traits)

        # Add the new trait to the inner list controller
        control_instance.controller.add_trait(
            trait_name, control_instance.inner_trait)

        # Create the associated control
        control_instance.controller_widget.create_control(
            trait_name, control_instance.inner_trait)

        # Update the list controller
        control_instance._controller_connections[0]()
        control_instance.controller_widget.update_controller_widget()
        logging.debug("Add 'ListControlWidget' '{0}' new trait "
                      "callback.".format(trait_name))

    @staticmethod
    def delete_one_row(control_instance, index_to_remove):
        """ Delete a two columns row if a widget is found in column two

        Parameters
        ----------
        control_instance: QFrame (mandatory)
            the instance of the controller widget control we want to
            synchronize with the controller
        index_to_remove: int (mandatory)
            the row index we want to delete from the widget

        Returns
        -------
        is_deleted: bool
            True if a widget has been found and the row has been deledted,
            False otherwise
        widget: QWidget
            the widget that has been deleted. If 'is_deleted' is False return
            None
        """
        # Initilaize the output
        is_deleted = False

        # Try to get the widget item in column two
        widget_item = (
            control_instance.controller_widget._grid_layout.itemAtPosition(
                index_to_remove, 1))

        # If a widget has been found, remove the current line
        if widget_item is not None:

            # Remove the widget
            widget = widget_item.widget()
            control_instance.controller_widget._grid_layout.removeItem(
                widget_item)
            widget.deleteLater()

            # Try to get the widget label in column one
            label_item = (
                control_instance.controller_widget._grid_layout.itemAtPosition(
                    index_to_remove, 0))

            # If a label has been found, remove it
            if label_item is not None:

                # Remove the label
                label = label_item.widget()
                control_instance.controller_widget._grid_layout.removeItem(
                    label_item)
                label.deleteLater()

            # Update the output
            is_deleted = True

        # No widget found
        else:
            widget = None

        return is_deleted, widget

    @staticmethod
    def delete_list_item(controller_widget, control_name, control_instance):
        """ Delete the last control element

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
        # Delete the last inserted control
        last_row = (
            control_instance.controller_widget._grid_layout.rowCount())
        nb_of_items = control_instance.controller_widget._grid_layout.count()
        item_found = False
        index_to_remove = last_row - 1

        # If the list contain at least one widget
        if nb_of_items > 0:

            # While the last inserted widget has not been found
            while index_to_remove >= 0 and not item_found:

                # Try to remove the 'index_to_remove' control row
                item_found, widget = ListControlWidget.delete_one_row(
                    control_instance, index_to_remove)

                # If a list control has been deleted, remove the associated
                # tools
                if hasattr(widget, "controller"):

                    # Remove the list control extra tools row
                    ListControlWidget.delete_one_row(
                        control_instance, index_to_remove - 1)

                # Get the trait name that has just been deleted from the
                # controller widget
                if item_found:
                    trait_name = str(index_to_remove - 1)

                # Increment
                index_to_remove -= 1

        # No more control to delete
        else:
            logging.debug(
                "No more control to delete in '{0}'.".format(control_instance))

        # If one list control item has been deleted
        if item_found:

            # If the inner control is a list, convert the control index
            # Indeed, two elements are inserted for a list item
            # (tools + widget)
            if trait_ids(control_instance.inner_trait)[0].startswith("List_"):
                trait_name = str((int(trait_name) + 1) / 2 - 1)

            # Remove the trait from the controller
            control_instance.controller.remove_trait(trait_name)

            # Get, unpack and delete the control item
            control = control_instance.controller_widget._controls[trait_name]
            (inner_trait, inner_control_class, inner_control_instance,
             inner_control_label) = control
            del(control_instance.controller_widget._controls[trait_name])

            # Disconnect the removed control
            inner_control_class.disconnect(
                controller_widget, trait_name, inner_control_instance)

            # Update the list controller
            control_instance._controller_connections[0]()
            logging.debug("Remove 'ListControlWidget' '{0}' controller and "
                          "trait item.".format(trait_name))

        control_instance.controller_widget._grid_layout.update()

    @staticmethod
    def expand_or_collapse(control_instance, resize_button):
        """ Callback to expand or collapse a 'ListControlWidget'.

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
            icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/nav_right")),
                           QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Show the control
        else:
            control_instance.show()
            icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/nav_down")),
                           QtGui.QIcon.Normal, QtGui.QIcon.Off)

        # Set the new button icon
        resize_button.setIcon(icon)
