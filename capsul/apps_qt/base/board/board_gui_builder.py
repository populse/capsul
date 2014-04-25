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
import subprocess

# Qt import
from capsul.apps_qt.qt_backend import QtGui, QtCore
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


class BoardGUIBuilder(QtGui.QWidget):
    """ Create the result board of a pipeline.
    """

    def __init__(self, pipeline, ui, study_config):
        """ Method to initialize the result board interface.

        Parameters
        ----------
        pipeline: Pipeline (mandatory)
            a pipeline
        ui: enum (mandatory)
            user interface where all Qt controls are stored
        """
        # Inheritance
        super(BoardGUIBuilder, self).__init__()

        # Parameters
        self._pipeline = pipeline
        self._ui = ui
        self._study_config = study_config
        self._tree = ui.tree_controller
        self._controls = {}

        # Create the board
        self.data_to_tree()

    ##############
    # Properties #
    ##############

    #####################
    # Private interface #
    #####################

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
        return title.replace("_", " ")

    def data_to_tree(self):
        """ Method to insert processing parameters in the class tree
        """
        # Create item
        root = QtGui.QTreeWidgetItem(self._tree.invisibleRootItem())
        root.setText(0, self._title_for(self._pipeline.name))

        # Insert expanded item
        self._tree.setItemExpanded(root, True)

        # Generate controller controls
        for node_name, node in self._pipeline.nodes.iteritems():
            # add Processing
            if node_name is not "" and node.node_type not in ["view_node"]:
                child = QtGui.QTreeWidgetItem(root)
                child.setText(1, self._title_for(node_name))
            elif node.node_type == "view_node":
                widget = ViewerWidget(node_name, self._pipeline,
                                      self._study_config)
                widget.setParent(root.treeWidget())
                # root.setText(4, "view")
                root.treeWidget().setItemWidget(root, 4, widget)

           # child.treeWidget().setItemWidget(child, 2, widget)
            
            
class ViewerWidget(QtGui.QWidget):
    """ View result class
    """
    
    def __init__(self, viewer_node_name, pipeline, study_config):
        """ Method to initialize a ViewConrol class.
        
        Parameters
        ----------
        viewer_node_name: str
            the name of the node containing the viewer process
        pipeline: str
            the full pipeline in order to get the viewer input trait values
            since the viewer node is unactivated
        """
        # Inheritance
        super(ViewerWidget, self).__init__()
        
        # Default parameters
        self.viewer_node_name = viewer_node_name
        self.pipeline = pipeline
        self.study_config = study_config
        
        # Build control
        button = QtGui.QToolButton(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/icones/view_result")),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        button.setIcon(icon)
        button.clicked.connect(self.onDelListClicked)
        
    def onDelListClicked(self):
        """ Event to create the viewer
        """
        # Get the viewer node and process
        viewer_node = self.pipeline.nodes[self.viewer_node_name]
        viewer_process = viewer_node.process
        
        # Propagate the parameters to the input viewer node
        # And check if the viewer is active (ie dependencies
        # are specified -> corresponding process have run)
        is_viewer_active = True
        for plug_name, plug in viewer_node.plugs.iteritems():
            if plug_name in ["nodes_activation", "selection_changed"]:
                continue
            # since it is a viewer node we normally have only inputs
            for (source_node_name, source_plug_name, source_node, 
                source_plug, weak_link) in plug.links_from:
                
                source_plug_value = getattr(source_node.process,
                                            source_plug_name)
                source_trait = source_node.process.trait(source_plug_name) 
                setattr(viewer_process, plug_name, source_plug_value)
                if source_plug_value == source_trait.handler.default_value:
                   is_viewer_active = False 
       
        # Execute the viewer process using the defined study configuration
        if is_viewer_active:
            subprocess.call(viewer_process.get_commandline())
            # self.study_config.run(viewer_process)
        else:
            logging.error("The viewer is not active yet, maybe "
                          "because the processings steps have not run or are "
                          "not finished.")