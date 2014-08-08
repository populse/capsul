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

# Capsul import
from capsul.apps_qt.qt_gui.controller_widget import ControllerWidget


class ListControlWidget(object):
    """ Control to enter a list.
    """

    @staticmethod
    def is_valid(control_instance, *args, **kwargs):
        """ Method to check if the new control values are correct.

        If the new list controls values are not correct, the backroung color of 
        each control in the list will be red.

        Parameters
        ----------
        control_instance: QLineEdit (mandatory)
            the control widget we want to validate
        """
        return True

    @classmethod
    def check(cls, control_instance):
        """ Check if a controller widget list control is filled correctly.

        Parameters
        ----------
        cls: ListControlWidget (mandatory)
            a StrControlWidget control
        control_instance: QLineEdit (mandatory)
            the control widget we want to validate
        """
        pass
        # Hook: function that will be called to check for typo 
        # when a 'textEdited' qt signal is emited
        #widget_callback = partial(cls.is_valid, control_instance)

        # Execute manually the first time the control check method
        #widget_callback()

        # When a qt 'textEdited' signal is emited, check if the new
        # user value is correct
        #control_instance.textChanged.connect(widget_callback)


    @staticmethod
    def create_widget(parent, control_name, control_value, trait):
        """ Method to create the list widget.

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
            a two element tuple of the form (control widget: ,
            associated label: QLabel)
        """
        # Get the inner trait: expect only one inner trait
        if len(trait.inner_traits) != 1:
            raise Exception(
                "Expect only one inner trait in List control. Current value is "
                "'{0}'.".format(trait.inner_traits))
        inner_trait = trait.inner_traits[0]

        # Create the list widget
        scroll_area = QtGui.QScrollArea(parent=parent)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtGui.QFrame.StyledPanel)

        # Try to find the control name associated with the current inner
        # trait
        inner_control_class = ListControlWidget.get_control_class(inner_trait)
        print inner_control_class
        if isinstance(inner_control_class, str) and inner_control_class == "self":
            inner_control_class = ListControlWidget

        # If no control has been found, skip this trait and print
        # an error message. Note that the parameter will not be
        # accessible in the user interface.
        if inner_control_class is None:
            logging.error("No control defined for inner trait '{0}'. This "
                          "parameter will not be accessible in the "
                          "user interface.".format(control_name))
            return (scroll_area, None)

        # Create the inner widgets
        inner_widgets = []

        # Create the layout of the controller widget
        # We will add all the controls to this layout
        grid_layout = QtGui.QGridLayout()
        grid_layout.setAlignment(QtCore.Qt.AlignTop)
        grid_layout.setSpacing(3)
        grid_layout.setContentsMargins(5, 5, 5, 5)
        scroll_area.setLayout(grid_layout)

        for cnt, inner_control_values in enumerate(control_value):

            print cnt, inner_control_values

            # Create the control instance and associated label
            control_instance, control_label = inner_control_class.create_widget(
                scroll_area, str(cnt), inner_control_values,
                inner_trait)
            inner_widgets.append(control_instance)

            # Append the label and control in two separate columns of the
            # grid layout
            last_row = grid_layout.rowCount()
            grid_layout.addWidget(control_label, last_row, 0)
            grid_layout.addWidget(control_instance, last_row, 1)

        # Add the grid layout to the scroll area
        #scroll_area.setWidget(control_instance)

        # Create the label associated with the string widget
        control_label = trait.label
        if control_label is None:
            control_label = control_name
        if control_label is not None:
            label = QtGui.QLabel(control_label, parent)
        else:
            label = None

        return (scroll_area, label)

    @classmethod
    def get_control_class(cls, trait):
        """ Find the control associated with the input trait.

        The mapping is defined in the global class parameter
        '_defined_controls'.

        Parameters
        ----------
        cls: ControllerWidget (mandatory)
            a ControllerWidget class
        trait: Trait (mandatory)
            a trait item

        Returns
        -------
        control_class: class
            the class of the control widget associated with the input trait.
            If no match has been found, return None
        """
        # Initilaize the output variable
        control_class = None

        # Go through the trait string description: can have multiple element
        # when either trait is used
        # ToDo:: we actualy need to create all the controls and let the user
        # choose which one he wants to fill.
        for trait_id in trait_ids(trait):

            # Recursive construction: get only the top level
            print trait_id
            trait_id = trait_id.split("_")[0]

            # Try to get the control class
            control_class = cls._defined_controls.get(trait_id)

            # Stop when we have a match
            if control_class is not None:
                break

        return control_class

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
        #setattr(controller_widget.controller, control_name, unicode(
        #        control_instance.text()))
        pass

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
        #control_instance.setText(
        #    unicode(getattr(controller_widget.controller, control_name, "")))
        pass


#-------------------------------------------------------------------------
class ListCreateWidget(object):

    #class ListController(Controller):
    #    pass

    @staticmethod
    def is_valid_trait(trait):
        item_trait = trait.inner_traits[0]
        create_widget = ControllerWidget.find_create_control_from_trait(
            item_trait)
        return create_widget is not None

    @classmethod
    def create_widget(cls, parent, name, trait, value):

        item_trait = trait.inner_traits[0]
        # print '!ListCreateWidget!', name, 'List( %s )' % trait_ids(
        # item_trait )
        list_controller = cls.ListController()
        for i in xrange(len(value)):
            list_controller.add_trait(str(i), item_trait)
            trait = list_controller.trait(str(i))
            trait.order = i
            setattr(list_controller, str(i), value[i])
        result = ControllerCreateWidget.create_widget(
            parent, name, None, list_controller)
        control_instance = result[0]
        control_instance.controller_widget.connect_controller()
        control_instance.item_trait = item_trait
        control_instance.list_controller = list_controller
        control_instance.connected = False
        return result

    @staticmethod
    def update_controller(controller_widget, name, control_instance):
        items = [getattr(control_instance.list_controller, str(i))
                 for i in xrange(len(control_instance.list_controller.user_traits()))]
        # print '!update_controller!', name, len( items ), items
        setattr(controller_widget.controller, name, items)

    @classmethod
    def update_controller_widget(cls, controller_widget, name, control_instance, control_label):
        was_connected = control_instance.connected
        cls.disconnect_controller(
            controller_widget, name, control_instance, control_label)
        control_instance.controller_widget.disconnect_controller()
        items = getattr(controller_widget.controller, name)
        len_widget = len(control_instance.list_controller.user_traits())
        # print '!update_controller_widget!', name, len_widget, items
        user_traits_changed = False
        if len(items) < len_widget:
            for i in xrange(len(items), len_widget):
                control_instance.list_controller.remove_trait(str(i))
            user_traits_changed = True
        elif len(items) > len_widget:
            for i in xrange(len_widget, len(items)):
                control_instance.list_controller.add_trait(
                    str(i), control_instance.item_trait)
                trait = control_instance.list_controller.trait(str(i))
                trait.order = i
            user_traits_changed = True
        for i in xrange(len(items)):
            setattr(control_instance.list_controller, str(i), items[i])
        # print '!update_controller_widget! done', name
        control_instance.controller_widget.connect_controller()
        if user_traits_changed:
            control_instance.list_controller.user_traits_changed = True
        if was_connected:
            cls.connect_controller(
                controller_widget, name, control_instance, control_label)

    @classmethod
    def connect_controller(cls, controller_widget, name, control_instance, control_label):
        if not control_instance.connected:
            def list_controller_hook(obj, key, old, new):
                # print '!list_controller_hook!', ( obj, key, old, new )
                items = getattr(controller_widget.controller, name)
                items[int(key)] = new
            for n in control_instance.list_controller.user_traits():
                control_instance.list_controller.on_trait_change(
                    list_controller_hook, n)
            controller_hook = SomaPartial(
                cls.update_controller_widget, controller_widget, name, control_instance, control_label)
            controller_widget.controller.on_trait_change(
                controller_hook, name + '[]')
            control_instance._controller_connections = (
                list_controller_hook, controller_hook)
            control_instance.connected = True

    @staticmethod
    def disconnect_controller(controller_widget, name, control_instance, control_label):
        if control_instance.connected:
            list_controller_hook, controller_hook = control_instance._controller_connections
            controller_widget.controller.on_trait_change(
                controller_hook, name + '[]', remove=True)
            for n in control_instance.list_controller.user_traits():
                control_instance.list_controller.on_trait_change(
                    list_controller_hook, n, remove=True)
            del control_instance._controller_connections
            control_instance.connected = False

