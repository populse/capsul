#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
import sys
import traceback

from capsul.apps_qt.qt_backend import QtGui

from capsul.apps_qt.base.controller.controls import *

from capsul.controller import trait_ids


class ControllerGUIBuilder(QtGui.QWidget):
    """ Create the controller interface of a pipeline.
    """

    def __init__(self, pipeline, ui):
        """ Method to initialize the controller interface.

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            a pipeline
        ui: enum (mandatory)
            user interface where all Qt controls are stored
        """
        # Inheritance
        super(ControllerGUIBuilder, self).__init__()

        # Parameters
        self._pipeline = pipeline
        self._ui = ui
        self._tree = ui.tree_controller
        self._controls = {}

        # Split the pipeline plug parameters accordingly to there
        # output property
        if self._pipeline.name == "StudyConfig":
            self.data_to_tree(self._pipeline,
                              self._pipeline.user_traits(), 
                              "Configuration Options")
        else:
            self._inputs, self._outputs = self._split_pipeline_plugs(
                pipeline.nodes[""].plugs)

            # Insert the splitted parameters in the tree
            self.data_to_tree(self._pipeline.nodes_activation,
                              self._pipeline.nodes_activation.user_traits(),
                              "node activation")
            self.data_to_tree(self._pipeline, self._inputs, "inputs")
            self.data_to_tree(self._pipeline, self._outputs, "outputs")

    ##############
    # Properties #
    ##############

    #####################
    # Private interface #
    #####################

    def _split_pipeline_plugs(self, parameters):
        """ Split plug parameters accordingly to there output property

        Parameters
        ----------
        parameters: dict (mandatory)
            structure that contains the plug names and values

        Returns
        -------
        inputs: dict
            the input plugs
        outputs: dict
            the output plugs
        """
        inputs = {}
        outputs = {}
        for plug_name, plug in parameters.iteritems():
            if plug.enabled == True and plug.activated == True:
                if plug.output:
                    (source_node_name, source_plug_name, source_node,
                     source_plug, weak_link) = list(plug.links_from)[0]
                    outputs[plug_name] = self._pipeline.trait(plug_name)
                else:
                    inputs[plug_name] = self._pipeline.trait(plug_name)

        return inputs, outputs

    def _title_for(self, title):
        """ Method to tune a plug name

        Parameters
        ----------
        title: str (mandatory)
            the name of a plug

        Returns
        -------
        output: str
            the tuned name
        """
        return title.replace("_", " ").capitalize()

    def data_to_tree(self, trait_item, parameters, name):
        """ Method to insert plug parameters in the class tree

        Parameters
        ----------
        trait_item: has_traits item (mandatory)
            parameter where the trait are stored
        parameters: dict (mandatory)
            structure that contains the plug names and values
        name: str (mandatory)
            the desired new tree enty name
        """
        # Create item
        root = QtGui.QTreeWidgetItem(self._tree.invisibleRootItem())
        root.setText(0, self._title_for(name))

        # Insert expanded item
        self._tree.setItemExpanded(root, True)

        # Generate controller controls
        for trait_name, trait in parameters.iteritems():
            # Generate
            child = QtGui.QTreeWidgetItem(root)
            child.setText(1, trait_name)
            widget = self._create_control(trait_name, trait, trait_item,
                                          child.treeWidget())
            # Add some documentation from trait desc
            child.setToolTip(1, unicode(trait.desc))
            # Insert in tree
            child.treeWidget().setItemWidget(child, 2, widget)

    def _on_value_changed(self, signal):
        """ Method to update trait values when the user interface changed.
        """
        try:
            if "trait_item" in dir(signal):
                setattr(signal.trait_item, signal.trait_name, signal.value)
            else:
                setattr(self._pipeline, signal.trait_name, signal.value)
        except:
            exc_info = sys.exc_info()
            logging.error("{0}: {1}".format(exc_info[0], exc_info[1]))

    def _on_dynamic_changed(self, signal):
        """ Method to update the tree when a dynamic control has changed.
        """
        #print "*****", signal
#        root = self._tree.invisibleRootItem()
#        child_count = root.childCount()
#        print child_count
#        for i in range(child_count):
#            item = root.child(i)
#            item.setExpanded(False)
#            item.setExpanded(True)
        self._tree.collapseAll()
        self._tree.expandAll()
        # *always* emit the dataChanged() signal after changing any data
        # inside the model.
        # this is so e.g. the different views know they need to do things
        # with it.
        #QObject.emit(self,
        #    SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"),
        #    index, index)
        #self._ui.tree_widget.layout().update()
        #self._ui.tree_widget.parentWidget().layout().update()

    def _create_control(self, name, trait, trait_item, parent):
        """ Method to create a new control for a plug.

        Parameters
        ----------
        name: str (mandatory)
            the plug name
        trait: trait (mandatory)
            the trait beeing processed
        trait_item: has_traits item (mandatory)
            parameter where the trait are stored
        parent: QtGui.QWidget (mandatory)
            the parent widget

        Returns
        -------
        control: QtGui.QWidget
            the plug corresponding control
        """
        # Get trait description
        parameters = trait_ids(trait)
        trait_value = getattr(trait_item, name)

        # Create the controls
        for parameter in parameters[:1]:  #TODO change hack
            parameter = parameter.split("_")
            expression = "{0}(".format(parameter[0])
            if parameter[0] == "Enum":
                expression += "{0}, ".format(
                    self._pipeline.trait(name).handler.values)
            if parameter[0] == "List":
                inner_controls = "_".join(parameter[1:])
                expression += "inner_controls, "
            expression += "name, "
            expression += "trait_value, "
            if parameter[0] == "Bool":
                expression += "trait_item, "
            if isinstance(trait.enabled, bool):
                expression += "trait.enabled, "
            expression += ")"

            try:
                # Create control
                control = eval(expression)
                control.setParent(parent)

                # Add observers
                control.add_observer("value", self._on_value_changed)
                if "update" in control.allowed_signals:
                    control.add_observer("update", self._on_dynamic_changed)

                # Store the created control
                self._controls[name] = control

            except:
                exc_info = sys.exc_info()
                logging.error("".join(traceback.format_exception(*exc_info)))
                logging.error("Could not create control from"
                              "expression \"{0}\"".format(expression))
                return

        return control
