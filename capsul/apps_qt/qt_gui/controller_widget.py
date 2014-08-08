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

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.controller import trait_ids, Controller

# Capsul import
import capsul.qtgui.controls as controls


class ControllerWidget(QtGui.QWidget):
    """ Class that create a widget to set the controller parameters.
    """

    # Parameter to store the mapping between the string trait descriptions and
    # the associated control names
    _defined_controls = controls.controls

    def __init__(self, controller, parent=None, name=None, live=False,
                 hide_labels=False):
        """ Method to initilaize the ControllerWidget class.

        Parameters
        ----------
        controller: derived Controller instance (mandatory)
            a class derived from the Controller class we want to parametrize
            with a widget.
        parent: QtGui.QWidget (optional, default None)
            the controller widget parent widget.
        name: (optional, default None)
            the name of this controller widget
        live: bool (optional, default False)
            if True, synchronize the edited values in the widget with the
            controller values on the fly,
            otherwise, wait the synchronization instruction to update the
            controller values.
        hide_labels: bool (optional, default False)
            if True, don't show the labels associated with the controls
        """
        # Inheritance
        super(ControllerWidget, self).__init__(parent)

        # Class parameters
        self.controller = controller
        self.live = live
        self.hide_labels = hide_labels
        self.connected = False
        self.btn_expand = None
        self._controls = {}

        # If possilbe, set the name of the widget
        if name:
            self.setObjectName(name)

        # Create the layout of the controller widget
        # We will add all the controls to this layout
        self._grid_layout = QtGui.QGridLayout()
        self._grid_layout.setAlignment(QtCore.Qt.AlignTop)
        self._grid_layout.setSpacing(3)
        self._grid_layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self._grid_layout)

        # Create all the layout controls associated with the controller values
        # we want to tune (ie the user_traits)
        self._create_controls()

        # Start the event loop that check for wrong edited fields (usefull
        # when we work off line, otherwise the traits make the job).
        self.check()

        # Set the synchrinization between this object and the input controller:
        # 1) synchronize the edited values in the widget with the controller
        # values on the fly
        if self.live:
            self.connect()

        # 2) initialize the controller widget with the controller values and
        # wait a synchronization instruction to update the controller values.
        else:
            self.update_controller_widget()

    ###########################################################################
    # Public members    
    ###########################################################################

    def check(self):
        """ 
        """
        # Go through all the controller widget controls
        for control_name, control in self._controls.iteritems():

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # Call the current control specific check method
            control_class.check(control_instance)        

    def update_controller(self):
        """ Update the controller.

        At the end the controller traits values will match the controller
        widget user defined parameters.
        """
        # Go through all the controller widget controls
        for control_name, control in self._controls.iteritems():

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # Call the current control specific update controller method
            control_class.update_controller(
                self, control_name, control_instance)

    def update_controller_widget(self):
        """ Update the controller widget.

        At the end the controller widget user editable parameters will match
        the controller traits values.
        """
        # Go through all the controller widget controls
        for control_name, control in self._controls.iteritems():

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # Call the current control specific update controller widget method
            control_class.update_controller_widget(
                self, control_name, control_instance)

    def connect(self):
        """ Connect the controller trait and the controller widget controls
        """
        # If the controller and controller widget are not yet connected
        if not self.connected:

            # Go through all the controller widget controls
            for control_name, control in self._controls.iteritems():

                # Unpack the control item
                trait, control_class, control_instance, control_label = control

                # Call the current control specific connection method
                control_class.connect(self, control_name, control_instance)

            # Add an event for the 'user_traits_changed' controller signal
            self.controller.on_trait_change(
                self.update_controls, "user_traits_changed")

            # Update the controller widget values
            self.update_controller_widget()

            # Update the connection status
            self.connected = True

    def disconnect(self):
        """ Disconnect the controller trait and the controller widget controls
        """
        # If the controller and controller widget are connected
        if self.connected:

            # Remove the 'update_controls' event connected with the
            # 'user_traits_changed' controller signal
            self.controller.on_trait_change(
                self.update_controls, "user_traits_changed", remove=True)

            # Go through all the controller widget controls
            for control_name, control in self._controls.iteritems():

                # Unpack the control item
                trait, control_class, control_instance, control_label = control

                # Call the current control specific disconnection method
                control_class.disconnect(self, control_name, control_instance)

            # Update the connection status
            self.connected = False

    def update_controls(self):
        """ Event to refresh the connection between the controller and the
        controller widget.

        The refresh is done off line, ie. we need first to disconnect the
        controller and the controller widget 
        """
        # Get the controller traits
        user_traits = self.controller.user_traits()

        # Assess the refreshing is done off line
        was_connected = self.connected
        if was_connected:
            self.disconnect()

        # Go through all the controller widget controls
        for control_name, control in self._controls.iteritems():

            # Unpack the control item
            trait, control_class, control_instance, control_label = control

            # If the the controller trait is different from the trait
            # associated with the control
            if user_traits.get(control_name) != trait:

                # Closes and schedules for deletation the control widget
                control_instance.close()
                control_instance.deleteLater()

                # Closes and schedules for deletation the control labels
                if isinstance(control_label, tuple):
                    for label in control_label:
                        control_label[0].close()
                        control_label[0].deleteLater()
                elif control_label:
                    control_label.close()
                    control_label.deleteLater()

                # Delete this control from the class
                del self._controls[name]

        # Recreate all the layout controls associated with the controller
        # values we want to tune (ie the user_traits)
        self._create_controls()

        # Restore the connection status
        if was_connected:
            self.connect()

        self.updateGeometry()

    ###########################################################################
    # Private members    
    ###########################################################################

    def _create_controls(self):
        """ Method that will create a control for each user-trait in the
        controller.

        Controller parameters that cannot be associated with controls will not
        appear in the user interface.
        """
        # Go through all the controller user-traits
        for trait_name, trait in self.controller.user_traits().iteritems():

            # Search if the current trait has already been processed
            control_name = self._controls.get(trait_name)

            # Try to find the control name associated with the current
            # trait name
            if control_name is None:

                # Call the search function
                control_class = self.get_control_class(trait)

                # If no control has been found, skip this trait and print
                # an error message. Note that the parameter will not be
                # accessible in the user interface.
                if control_class is None:
                    logging.error("No control defined for trait '{0}'. This "
                                  "parameter will not be accessible in the "
                                  "user interface.".format(trait_name))
                    continue

                # Create the control instance and associated label
                control_instance, control_label = control_class.create_widget(
                    self, trait_name, trait.label or trait.handler.values, 
                    getattr(self.controller, trait_name))
        
                # If the trait contains a description, insert a tool tip to the
                # control instance
                tooltip = ""
                if trait.desc:
                    tooltip = "<b>" + trait_name + ":</b> " + trait.desc
                control_instance.setToolTip(tooltip)
                    
                # If the control has no label, append the control in a two
                # columns span area of the grid layout
                if control_label is None:
                
                    # Parameters: QWidget, int row, int column, int rowSpan,
                    # int columnSpan
                    self._grid_layout.addWidget(
                        control_instance, self._grid_layout.rowCount(), 0, 1, 2)

                # If the control has two labels, add a first row with the
                # two labels (one per column), and add the control in
                # the next two columns span row of the grid layout
                elif (isinstance(control_label, tuple) and 
                      len(control_label) == 2):

                    # Append labels in two columns
                    last_row = self._grid_layout.rowCount()
                    if not self.hide_labels:
                        self._grid_layout.addWidget(
                            control_label[0], last_row, 0)
                    self._grid_layout.addWidget(control_label[1], last_row, 1)

                    # Append the control in a two columns span area
                    self._grid_layout.addWidget(
                        control_instance, last_row + 1, 0, 1, 2)

                # Otherwise, append the label and control in two separate
                # columns of the grid layout
                else:

                    # Append the label in the first column
                    last_row = self._grid_layout.rowCount()
                    if not self.hide_labels:
                        self._grid_layout.addWidget(control_label, last_row, 0)

                    # Append the control in the second column
                    self._grid_layout.addWidget(control_instance, last_row, 1)

                # Store some informations about the inserted control in the
                # private '_controls' class parameter
                # Keys: the trait names
                # Parameters: the trait - the control name - the control - and
                # the labels associated with the control 
                self._controls[trait_name] = (
                    trait, control_class, control_instance, control_label)

            # Otherwise, the control associated with the current trait name is
            # already inserted in the grid layout, just unpack the value
            # contained in the private '_controls' class parameter
            else:
                (trait, control_class, control_instance,
                 control_label) = control_name

            # Convert 'control_label' parameter to tuple
            control_label = control_label or ()
            if not isinstance(control_label, tuple):
                control_label = (control_label, )

            # Each trait has a hidden property. Take care of this information
            hide = getattr(trait, 'hidden', False)

            # Hide the control and associated labels
            if hide:
                control_instance.hide()
                for label in control_label:
                    label.hide()

            # Show the control and associated labels            
            else:
                control_instance.show()
                for label in control_label:
                    label.show()

    ###########################################################################
    # Class Methods   
    ###########################################################################

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

            # Try to get the control class
            control_class = cls._defined_controls.get(trait_id)

            # Stop when we have a match
            if control_class is not None:
                break

        return control_class
