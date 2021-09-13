# -*- coding: utf-8 -*-
'''
Classes
=======
:class:`BoardWidget`
--------------------
'''

# System import
from __future__ import absolute_import
import logging
import six

# Define the logger
logger = logging.getLogger(__name__)

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.qt_gui.controller_widget import ControllerWidget

# Capsul import
from capsul.qt_gui.widgets.viewer_widget import ViewerWidget
from capsul.api import Pipeline
from capsul.pipeline.pipeline_nodes import Switch, PipelineNode


class BoardWidget(QtGui.QWidget):
    """ Class that create a widget to visualize the controller status.
    """

    def __init__(self, controller, parent=None, name=None):
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
        """
        # Inheritance
        super(BoardWidget, self).__init__(parent)

        # Class parameters
        self.controller = controller

        # If possible, set the widget name
        if name:
            self.setObjectName(name)

        # Create the layout of the board widget
        # Three item layout: output_controller_widget - board_tree - viewer_tree
        self._grid_layout = QtGui.QGridLayout()
        self._grid_layout.setAlignment(QtCore.Qt.AlignTop)
        self._grid_layout.setSpacing(3)
        self._grid_layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self._grid_layout)

        # Create all the controls
        self.create_output_widget()
        self.create_viewer_tree()
        self.create_board_tree()

        # Fill the grid layout
        self._grid_layout.addWidget(self.board_tree, 0, 0, 1, 2)
        self._grid_layout.addWidget(self.output_controller_widget, 1, 0, 1, 1)
        self._grid_layout.addWidget(self.viewer_tree, 1, 1, 1, 1)

        # Create the board
        self._fill_trees()

    ###########################################################################
    # Methods   
    ###########################################################################

    def create_output_widget(self):
        """ Method to create the output controller widget built 
        from the class controller output traits
        """
        self.output_controller_widget = ControllerWidget(
                self.controller, parent=self, name="outputs", live=True,
                hide_labels=False, select_controls="outputs")
        self.output_controller_widget.setEnabled(False)

    def create_viewer_tree(self):
        """ Method to create a tree with two columns (pipeline name - viewers)
        that will summarize all the available quality control nodes
        """
        # Create the tree widget
        self.viewer_tree = QtGui.QTreeWidget(parent=self)

        # Initialize the tree widget
        self.viewer_tree.setColumnCount(2)
        self.viewer_tree.headerItem().setText(0, "Pipeline Name")
        self.viewer_tree.headerItem().setText(1, "Viewers")

    def create_board_tree(self):
        """ Method to create a tree with five columns (processings - status -
        execution time - memory - logs) that will summarize all the available
        quality control nodes
        """
        # Create the tree widget
        self.board_tree = QtGui.QTreeWidget(parent=self)

        # Initialize the tree widget
        self.board_tree.setColumnCount(5)
        self.board_tree.headerItem().setText(0, "Processings")
        self.board_tree.headerItem().setText(1, "Status")
        self.board_tree.headerItem().setText(2, "Execution Time")
        self.board_tree.headerItem().setText(3, "Memory")
        self.board_tree.headerItem().setText(4, "Logs")

    ###########################################################################
    # Private methods   
    ###########################################################################

    def _title_for(self, title):
        """ Method to tune a title name.

        Juste replace the '_' character by a blank ' '.

        Parameters
        ----------
        title: str (mandatory)
            the title name we want to tune.

        Returns
        -------
        output: str
            the tuned name
        """
        return title.replace("_", " ")

    def _fill_trees(self):
        """ Method to insert processing parameters in the class trees.
        """
        # Generate structures that contain all viewers and all processings
        # status - metainforamtion
        viewers_struct = {}
        processings_struct = []
    
        # Go through all the controller (pipeline) nodes.
        for node_name, node in six.iteritems(self.controller.nodes):

            # If the current node is a processing node
            if node_name != "" and node.node_type != "view_node":

                # First browse the current node to get processings and viewers
                process_nodes = []
                view_nodes = []
                self.browse_node(
                    node, process_nodes, view_nodes, self.controller)

                # Set process logs
                #for process_node in process_nodes:
                #    widget = LogWidget(process_node)
                #    widget.setParent(root.treeWidget())
                #    child.treeWidget().setItemWidget(child, 3, widget)

                # Fill the processing structure
                for processing_node in process_nodes:
                    processings_struct.append({
                        "name": processing_node.name,
                        "log": processing_node.process.log_file or "No log"})

                # Fill the viewer structure
                for viewer_node, pipeline in view_nodes:

                    # Create a viewer widget (a simple press button)
                    widget = ViewerWidget(viewer_node.name, pipeline, None)
                                          #self._study_config)

                    # Store the widget in the corresponding structure
                    title = self._title_for(pipeline.name)
                    if title not in viewers_struct:
                        viewers_struct[title] = []
                    viewers_struct[title].append(widget)


            # If the current node is a viewer node
            elif node.node_type == "view_node":

                # Create a viewer widget (a simple press button)
                widget = ViewerWidget(node_name, self.controller, None)
                                      #self._study_config)

                # Store the widget in the corresponding structure
                title = self._title_for(self.controller.name)
                if title not in viewers_struct:
                    viewers_struct[title] = []
                viewers_struct[title].append(widget)


        # Fill the viewer tree widget
        viewer_parent = self.viewer_tree.invisibleRootItem()
        for pipeline_title, viewer_widgets in six.iteritems(viewers_struct):

            # Create a new tree item
            viewer_child = QtGui.QTreeWidgetItem(viewer_parent)
            viewer_child.setText(0, pipeline_title)

            # Set the viewer widgets in a layout
            widget_layout = QtGui.QHBoxLayout()
            widget_layout.setSpacing(0)
            widget_layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
            widget_layout.setContentsMargins(0, 0, 0, 0)
            widget_layout.addStretch(1)
            for widget in viewer_widgets:
                widget = QtGui.QToolButton()
                widget_layout.addWidget(widget)

            # Set the final widget tree item
            widget = QtGui.QWidget(viewer_child.treeWidget())
            widget.setLayout(widget_layout)
            viewer_child.treeWidget().setItemWidget(viewer_child, 1, widget)

        # Fill the pboard tree widget
        board_parent = self.board_tree.invisibleRootItem()
        for process_info in processings_struct:

            # Create a new tree item
            board_child = QtGui.QTreeWidgetItem(board_parent)
            board_child.setText(0, process_info["name"])
            board_child.setText(4, process_info["log"])

    def browse_node(self, node, process_nodes, view_nodes, parent_pipeline):
        """ Find view_node and leaf nodes, ie. Process nodes

        Parameters
        ----------
        node: Node
            a capsul node
        process_nodes: Node
            node of type processing_node
        view_nodes: 2-uplet
            contains the node of type view_node and the pipeline where this node
            is defined
        """
        # Skip Switch nodes
        if not isinstance(node, Switch):

            # Browse recursively pipeline nodes
            if (isinstance(node.process, Pipeline) and 
                node.node_type != "view_node"):

                pipeline = node.process
                for sub_node in pipeline.nodes.values():
                    if not isinstance(sub_node, PipelineNode):
                        self.browse_node(sub_node, process_nodes, view_nodes,
                                         pipeline)
            # Update the results according to the node type
            else:
                if node.node_type == "view_node":
                    view_nodes.append((node, parent_pipeline))
                else:
                    process_nodes.append(node)

        
