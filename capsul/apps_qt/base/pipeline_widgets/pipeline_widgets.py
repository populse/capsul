#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from pprint import pprint
from capsul.apps_qt.qt_backend import QtCore, QtGui
try:
    from traits.api import File
except ImportError:
    from enthought.traits.api import File

from capsul.pipeline import Switch
from sub_pipeline_widgets import Link


###############################################################################
#                            Globals and constants                            #
###############################################################################
BLUE_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.9, 1)
BLUE_2 = QtGui.QColor.fromRgbF(0.5, 0.5, 0.7, 1)
LIGHT_BLUE_1 = QtGui.QColor.fromRgbF(0.95, 0.95, 1.0, 1)
LIGHT_BLUE_2 = QtGui.QColor.fromRgbF(0.85, 0.85, 0.9, 1)

SAND_1 = QtGui.QColor.fromRgb(204, 178, 76)
SAND_2 = QtGui.QColor.fromRgb(255, 229, 127)
LIGHT_SAND_1 = QtGui.QColor.fromRgb(217, 198, 123)
LIGHT_SAND_2 = QtGui.QColor.fromRgb(255, 241, 185)

GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
GRAY_2 = QtGui.QColor.fromRgbF(0.4, 0.4, 0.4, 1)
LIGHT_GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
LIGHT_GRAY_2 = QtGui.QColor.fromRgbF(0.6, 0.6, 0.7, 1)

###############################################################################
#                                   Items                                     #
###############################################################################
class TitleNode(QtGui.QGraphicsItemGroup):
    """ Define a node containing only its title.

    Parameters
    ----------
    name: String
        Name of the node.
    number: Int
        Number of the node: the format of the node title is <name>:<number>.
    active: Bool
        Determine if the node color is normal (True) or light (False).
    style: 'default' or 'switch'
        Determine the color map of the node.
        Blue for 'default', yellow for 'switch'.
    parent: QGraphicsItem
    """
    _colors = {'default': (BLUE_1, BLUE_2, LIGHT_BLUE_1, LIGHT_BLUE_2),
               'switch': (SAND_1, SAND_2, LIGHT_SAND_1, LIGHT_SAND_2)}

    def __init__(self, name,
                 number=None, active=True,
                 style=None, parent=None):
        super(TitleNode, self).__init__(parent)
        # If no style, define default style
        if style is None:
            style = 'default'

        self.name = name
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

        self.active = active
        self.number = number
        
        if self.active:
            # If active node, use normal colors for title
            color_1 = GRAY_1
            color_2 = GRAY_2
        else:
            # If non active node, use light colors for title
            color_1 = LIGHT_GRAY_1
            color_2 = LIGHT_GRAY_2

        # Define a background brush with a gradient
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, color_1)
        gradient.setColorAt(1, color_2)
        self.bg_brush = QtGui.QBrush(gradient)

        if self.active:
            # If active node, use normal colors for title
            color_1, color_2 = self._colors[style][0:2]
        else:
            # If non active node, use light colors for title
            color_1, color_2 = self._colors[style][2:4]

        # Define a title brush with a gradient
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(1, color_1)
        gradient.setColorAt(0, color_2)
        self.title_brush = QtGui.QBrush(gradient)

        # Build the node
        self._build()

    def get_title(self):
        """ Return the title of the node.
        The title format is <name> if no number, or <name>:<number>.
        """
        if self.number is None:
            return self.name
        else:
            return self.name + ":" + repr(self.number)

    def _build(self):
        """ Draws all the elements of the node : title, input and output
        parameters, background rectangle and title rectangle
        """
        ########## Title parameters ###########
        margin = 5
        # Define title
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        # Set title font
        font = self.title.font()
        font.setWeight(QtGui.QFont.Bold)
        font.setPointSize(20)
        self.title.setFont(font)
        # Set title position
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        # always add to group after setPos
        self.addToGroup(self.title)

        ######### Input parameters #########
        # Height of the first input parameter
        y_pos = margin * 2 + self.title.boundingRect().size().height()
        # Parameter name
        label = QtGui.QGraphicsTextItem("Expand Pipeline", self)
        label.setZValue(2)
        # Set plug position
        label.setPos(margin, y_pos)
        self.addToGroup(label)

        ######## Background box ##########
        self.box = QtGui.QGraphicsRectItem(self)
        self.box.setBrush(self.bg_brush)
        self.box.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box.setZValue(-1)
        self.addToGroup(self.box)
        # Set rectangle so that it includes everything inside the node
        self.box.setRect(self.boundingRect())

        ######### Title box ###########
        self.box_title = QtGui.QGraphicsRectItem(self)
        # Set title box so that it includes only the title, and the same width
        # as the background rectangle
        rect = self.title.mapRectToParent(self.title.boundingRect())
        rect.setWidth(self.boundingRect().width())
        self.box_title.setRect(rect)
        self.box_title.setBrush(self.title_brush)
        self.box_title.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.addToGroup(self.box_title)
        

class PipelineScene(QtGui.QGraphicsScene):
    """ Container of all the title nodes of a given pipeline.
    """
    def __init__(self, ui, parent=None):
        super(PipelineScene, self).__init__(parent)
        self.gnodes = {}
        self.glinks = {}
        self._pos = 50
        self.pos = {}
        self.pipeline = None
        self.ui = ui

        self.changed.connect(self.update_paths)

    def add_gnode(self, gnode):
        """ Add a title node to the scene.

        Parameters
        ----------
        name: String
            Name of the node to add.
        title_gnode: TitleNode
            Node to add to the scene.
        """
        gnode_name = gnode.name
        # Add the node to the scene
        self.addItem(gnode)
        # Get node position
        pos = self.pos.get(gnode_name)
        if pos is None:
            # If no position, set a fixed position
            gnode.setPos(self._pos, self._pos)
            # Redefine set position for the next node
            self._pos += 100
        else:
            # If position, place the node on position
            gnode.setPos(pos)
        # Update dictionary containing all nodes
        self.gnodes[gnode_name] = gnode

    def add_glink(self, source_gnode_name, dest_gnode_name, active):
        """ Add a link between two title nodes to the scene.

        Parameters
        ----------
        source_gnode_name: String
            Name of the node from which originates the link.
        dest_gnode_name: String
            Name of the destination node of the link.
        active: Bool
            Determines if the link is activated (red) or deactivated (grey)
        """
        # Get the corresponding source gnode from node dict
        source_gnode = self.gnodes[source_gnode_name]
        src_bounding_rect = source_gnode.boundingRect()
        src_plug_pos = (src_bounding_rect.bottomRight() +
                        src_bounding_rect.topRight())/2
        # Get the corresponding destination gnode from node dict
        dest_gnode = self.gnodes[dest_gnode_name]
        dst_bounding_rect = dest_gnode.boundingRect()
        dst_plug_pos = (dst_bounding_rect.bottomLeft() +
                        dst_bounding_rect.topLeft())/2

        # Get pipeline nodes
        source_node_name = source_gnode_name.replace("inputs", "")
        dest_node_name = dest_gnode_name.replace("outputs", "")

        glink = Link(source_gnode.mapToScene(src_plug_pos),
                     dest_gnode.mapToScene(dst_plug_pos), active,
                     left_node=self.pipeline.nodes[source_node_name],
                     right_node=self.pipeline.nodes[dest_node_name],
                     ui=self.ui)
        # Add link to links dictionary
        self.glinks[(source_gnode_name,
                     dest_gnode_name)] = glink
        self.addItem(glink)

    def update_paths(self):
        """ Update links between plugs.
        Get all the title nodes' positions, and update links with the new
        origin and target coordinates.
        """
        # Get the position of each node in a dictionary
        for i in self.items():
            if isinstance(i, TitleNode):
                self.pos[i.name] = i.pos()

        # Iteration over all the links
        for source_dest, glink in self.glinks.iteritems():
            source_gnode_name, dest_gnode_name = source_dest
            # Get source and destination nodes from node dictionary
            source_gnode = self.gnodes[source_gnode_name]
            src_bounding_rect = source_gnode.boundingRect()
            src_plug_pos = (src_bounding_rect.bottomRight() +
                            src_bounding_rect.topRight())/2
            dest_gnode = self.gnodes[dest_gnode_name]
            dst_bounding_rect = dest_gnode.boundingRect()
            dst_plug_pos = (dst_bounding_rect.bottomLeft() +
                            dst_bounding_rect.topLeft())/2
            # Update links
            glink.update(source_gnode.mapToScene(src_plug_pos),
                         dest_gnode.mapToScene(dst_plug_pos))

    def set_pipeline(self, pipeline):
        """ Generate the whole graphical interface of the pipeline :
        all the title nodes, and links between them.
        """
        self.pipeline = pipeline
        pipeline_inputs = []
        pipeline_outputs = []
        # Get all plugs without node name
        for name, plug in pipeline.nodes[''].plugs.iteritems():
            if plug.links_to:
                # If link to other plug, inputs plug
                pipeline_inputs.append(name)
            else:
                # else, outputs plug
                pipeline_outputs.append(name)
        if pipeline_inputs:
            # Create inputs node, always active
            self.add_gnode(TitleNode('inputs', active=True))
        for node_name, node in pipeline.nodes.iteritems():
            if not node_name:
                # already set, continue
                continue
            if isinstance(node, Switch):
                # If node is a switch, get "switch" style (yellow)
                style = 'switch'
            else:
                style = None
            # add node with inputs and outputs activated or not
            self.add_gnode(TitleNode(node_name,
                                     active=node.activated,
                                     style=style))
        if pipeline_outputs:
            # Create outputs node, always active
            self.add_gnode(TitleNode('outputs', active=True))

        # Create all links between plugs
        for source_node_name, source_node in pipeline.nodes.iteritems():
            for source_plug_name, source_plug in source_node.plugs.iteritems():
                for (dest_node_name, dest_plug_name, dest_node, dest_plug,
                     only_if_activated) in source_plug.links_to:
                    if not source_node_name:
                        # If no source name, put default source name: "inputs"
                        source_node_name = 'inputs'
                    if not dest_node_name:
                        # If no source name, put default dest name: "outputs"
                        dest_node_name = 'outputs'
                    if (source_node_name, dest_node_name) not in \
                            self.glinks.keys():
                        self.add_glink(source_node_name, dest_node_name,
                                       active=source_plug.activated and
                                       dest_plug.activated)


class PipelineView(QtGui.QGraphicsView):
    """ Define a view to visualize the pipeline scene

    Parameters
    ----------
    pipeline: Pipeline
        pipeline to draw
    """
    def __init__(self, pipeline, ui, parent=None):
        super(PipelineView, self).__init__(parent)
        self.scene = None
        self.ui = ui
        self.set_pipeline(pipeline)
        # add the widget if new
        # otherwise, recreate the widget
        already_created = False
        index = 0
        for index in range(self.ui.simple_pipeline.count()):
            if self.ui.simple_pipeline.tabText(index) == pipeline.name:
                already_created = True
                break
        if not already_created:
            self.ui.simple_pipeline.addTab(self, pipeline.name)
            self.ui.simple_pipeline.setCurrentIndex(
                self.ui.simple_pipeline.count() - 1)
        else:
            self.ui.simple_pipeline.removeTab(index)
            self.ui.simple_pipeline.insertTab(index, self, pipeline.name)
            self.ui.simple_pipeline.setCurrentIndex(index)

    def _set_pipeline(self, pipeline):
        """ Set the pipeline
        """
        # Define items position
        if self.scene:
            pos = self.scene.pos
#            pprint(dict((i, (j.x(), j.y())) for i, j in pos.iteritems()))
        else:
            pos = dict((i, QtCore.QPointF(*j))
                       for i, j in pipeline.node_position.iteritems())
        # Create pipeline scene
        self.scene = PipelineScene(ui=self.ui)
        self.scene.pos = pos
        self.scene.set_pipeline(pipeline)
        self.setWindowTitle(pipeline.name)
        self.setScene(self.scene)

    def set_pipeline(self, pipeline):
        """ Set the pipeline and setup callback to update view when pipeline
        state is modified
        """
        self._set_pipeline(pipeline)

        # Setup callback to update view when pipeline state is modified
        def reset_pipeline():
            self._set_pipeline(pipeline)
        pipeline.on_trait_change(reset_pipeline, 'selection_changed')

    def zoom_in(self):
        """ To zoom in on the graph
        """
        self.scale(1.2, 1.2)

    def zoom_out(self):
        """ To zoom out on the graph
        """
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def wheelEvent(self, event):
        """ Zoom in or out when scrolling
        """
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.delta() < 0:
                self.zoom_out()
            else:
                self.zoom_in()
            event.accept()
        else:
            QtGui.QGraphicsView.wheelEvent(self, event)
