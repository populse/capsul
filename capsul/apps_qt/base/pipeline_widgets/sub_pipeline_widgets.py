#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.apps_qt.qt_backend import QtCore, QtGui
from capsul.pipeline import Switch


###############################################################################
#                            Globals and constants                            #
###############################################################################
BLUE_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.9, 1)
BLUE_2 = QtGui.QColor.fromRgbF(0.5, 0.5, 0.7, 1)
LIGHT_BLUE_1 = QtGui.QColor.fromRgbF(0.95, 0.95, 1.0, 1)
LIGHT_BLUE_2 = QtGui.QColor.fromRgbF(0.85, 0.85, 0.9, 1)

GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
GRAY_2 = QtGui.QColor.fromRgbF(0.4, 0.4, 0.4, 1)
LIGHT_GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
LIGHT_GRAY_2 = QtGui.QColor.fromRgbF(0.6, 0.6, 0.7, 1)

SAND_1 = QtGui.QColor.fromRgb(204, 178, 76)
SAND_2 = QtGui.QColor.fromRgb(255, 229, 127)
LIGHT_SAND_1 = QtGui.QColor.fromRgb(217, 198, 123)
LIGHT_SAND_2 = QtGui.QColor.fromRgb(255, 241, 185)

RED_1 = QtGui.QColor.fromRgb(175, 54, 16)
RED_2 = QtGui.QColor.fromRgb(234, 131, 31)


###############################################################################
#                                   Items                                     #
###############################################################################
class FullNode(QtGui.QGraphicsItemGroup):
    """ Generate a Node

    Parameters
    ----------
    name: string
        node name
    input_parameters: list of string
        input parameters of the node
    output_parameters: list of string
        output parameters of the node
    number: int
        add a number to the string name: node_title = <name>:<number>
    active: bool
        define if node is active of not (change the color of the node)
    style: string
        define the type of the node: 'default' or 'switch'
    parent:
    """
    _colors = {'default': (BLUE_1, BLUE_2, LIGHT_BLUE_1, LIGHT_BLUE_2),
               'switch': (SAND_1, SAND_2, LIGHT_SAND_1, LIGHT_SAND_2)}

    def __init__(self, name, input_parameters, output_parameters,
                 number=None, active=True,
                 style=None, parent=None):
        super(FullNode, self).__init__(parent)
        # If no style, define default style
        if style is None:
            style = 'default'

        self.name = name
        self.input_parameters = input_parameters
        self.output_parameters = output_parameters
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        # Initialize in_plugs and out_plugs as empty dicts
        self.in_plugs = {}
        self.out_plugs = {}

        self.active = active
        self.number = number
        #gradient = QtGui.QRadialGradient(50, 50, 50, 50, 50)

        if self.active:
            # If active node, use normal colors for background
            color_1, color_2 = self._colors[style][0:2]
        else:
            # If non active node, use light colors for background
            color_1, color_2 = self._colors[style][2:4]

        # Define a background brush with a gradient
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, color_1)
        gradient.setColorAt(1, color_2)
        self.bg_brush = QtGui.QBrush(gradient)

        if self.active:
            # If active node, use normal colors for title
            color_1 = GRAY_1
            color_2 = GRAY_2
        else:
            # If non active node, use light colors for title
            color_1 = LIGHT_GRAY_1
            color_2 = LIGHT_GRAY_2

        # Define a title brush with a gradient
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(1, color_1)
        gradient.setColorAt(0, color_2)
        self.title_brush = QtGui.QBrush(gradient)

        #title_font = QtGui.QApplication.font()
        #title_font.setWeight(QtGui.QFont.Bold)

        # Build the node
        self._build()

    def get_title(self):
        """ Get the node of the title, defined as <name> if number is None,
        or <name>:<number>
        """
        if self.number is None:
            return self.name
        else:
            return self.name + ":" + repr(self.number)

    def _build(self):
        """ Draws all the elements of the node : title, input and output
        parameters, background rectangle and title rectangle
        """
        plug_width = 12
        ########## Title parameters ###########
        margin = 5
        # Define title
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        # Set title font
        font = self.title.font()
        font.setWeight(QtGui.QFont.Bold)
        self.title.setFont(font)
        # Set title position
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        # always add to group after setPos
        self.addToGroup(self.title)

        ######### Input parameters #########
        # Height of the first input parameter
        y_pos = margin * 2 + self.title.boundingRect().size().height()
        # Draw each input parameter
        for in_param in self.input_parameters:
            if in_param.startswith('+'):
                # If in_param starts with '+', set other type of plug,
                # and remove '+'
                simple = False
                in_param = in_param[1:]
            else:
                # Else, just set simple plug
                simple = True
            # Parameter name
            param_name = QtGui.QGraphicsTextItem(in_param, self)
            # Create corresponding plug
            plug = Plug(param_name.boundingRect().size().height(),
                        plug_width, simple=simple, parent=self)
            #plug.setZValue(2)
            param_name.setZValue(2)
            # Set plug position
            plug.setPos(margin, y_pos)
            # Set parameter name position at the right of plug position
            param_name.setPos(plug.boundingRect().size().width() + margin,
                              y_pos)
            self.addToGroup(param_name)
            self.addToGroup(plug)
            # Add the plug inside input plug dictionary
            self.in_plugs[in_param] = plug
            # Define height of the next parameter
            y_pos = y_pos + param_name.boundingRect().size().height()

        # Draw each output parameter
        for out_param in self.output_parameters:
            if out_param.startswith('+'):
                # If out_param starts with '+', set other type of plug,
                # and remove '+'
                simple = False
                out_param = out_param[1:]
            else:
                # Else, just set simple plug
                simple = True
            # Parameter name
            param_name = QtGui.QGraphicsTextItem(out_param, self)
            # Create corresponding plug
            plug = Plug(param_name.boundingRect().size().height(),
                        plug_width, simple=simple, parent=self)
            #plug.setZValue(2)
            param_name.setZValue(2)
            # Set parameter name position
            param_name.setPos(plug.boundingRect().size().width() + margin,
                              y_pos)
            # Set parameter name position at the right of plug position
            plug.setPos(plug.boundingRect().size().width() + margin +
                        param_name.boundingRect().size().width() + margin,
                        y_pos)
            self.addToGroup(plug)
            self.addToGroup(param_name)
            # Add the plug inside output plug dictionary
            self.out_plugs[out_param] = plug
            # Define height of the next parameter
            y_pos = y_pos + param_name.boundingRect().size().height()

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


class Plug(QtGui.QGraphicsPolygonItem):
    """ Generate a Plug

    Parameters
    ----------
    height: float
        height of the plug
    width: float
        width of the plug
    simple: bool
        define style of plug: True for black triangle, False for dotted polygon
    parent: NodeGWidget
        node which owns the plug
    """
    def __init__(self, height, width, simple=True, parent=None):
        super(Plug, self).__init__(parent)
        if simple:
            # Define brush for simple plug: unified black
            brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
            brush.setColor(QtCore.Qt.black)
            # Define polygon for simple plug: triangle
            polygon = QtGui.QPolygonF([
                QtCore.QPointF(0, 0),
                QtCore.QPointF(width, (height - 5) / 2.0),
                QtCore.QPointF(0, height - 5)])
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        else:
            # Define brush for other plug: dotted black
            brush = QtGui.QBrush(QtCore.Qt.Dense4Pattern)
            brush.setColor(QtCore.Qt.black)
            # Define polygon for other plug:
            polygon = QtGui.QPolygonF([
                QtCore.QPointF(0, 0),
                QtCore.QPointF(width / 3.0, (height - 5) / 4.0),
                QtCore.QPointF(width / 3.0, 0),
                QtCore.QPointF(width, (height - 5) / 2.0),
                QtCore.QPointF(width / 3.0, (height - 5)),
                QtCore.QPointF(width / 3.0, (height - 5)*0.75),
                QtCore.QPointF(0, height - 5)])
        self.setPolygon(polygon)
        self.setBrush(brush)
        self.setZValue(3)

    def get_plug_point(self):
        # Get plug coordinates
        return self.mapToParent(QtCore.QPointF(
            self.boundingRect().size().width() / 2.0,
            self.boundingRect().size().height()/2.0))


class Link(QtGui.QGraphicsPathItem):
    """ Create a bezier curve between <origin> and <target>.

    Parameters
    ----------
    origin:
        The origin of the curve.
    target:
        The target of the curve.
    link_status: Bool
        Determine the color of the link: red (True) or grey (False).
    bezier_parameter: int
        Derivation parameter of the bezier curve.
    parent: QGraphicsItem
    """
    def __init__(self, origin, target, link_status, ui=None,
                 bezier_param=80, parent=None,
                 left_node=None, right_node=None):
        super(Link, self).__init__(parent)
        self.parent = parent
        self.ui = ui
        self.right_node = right_node
        self.left_node = left_node
        self.link_status = link_status
        self.bezier_param = bezier_param
        ###### Pen properties #######
        self.pen = QtGui.QPen()
        # Width of the link
        self.pen.setWidth(3)
        if self.link_status:
            # If link activated, color in red
            self.pen.setBrush(RED_2)
        else:
            # Else, color in grey
            self.pen.setBrush(QtCore.Qt.gray)
        self.pen.setCapStyle(QtCore.Qt.RoundCap)
        self.pen.setJoinStyle(QtCore.Qt.RoundJoin)

        ######## Path properties #########
        path = QtGui.QPainterPath()
        # Move to the origin, and start a new path
        path.moveTo(origin.x(), origin.y())
        # Create a Bezier curve between origin and target, using the control
        # points (origin.x()+100, origin.y()) and (target.x()-100, target.y())
        path.cubicTo(origin.x() + self.bezier_param, origin.y(),
                     target.x() - self.bezier_param, target.y(),
                     target.x(), target.y())
        # Draw the path
        self.setPath(path)
        self.setPen(self.pen)
        self.setZValue(0.5)

    def update(self, origin, target):
        """ Update the bezier curve with new origin and target.

        Parameters
        ----------
        origin:
            The new origin of the curve.
        target:
            The new target of the curve.
        """
        path = QtGui.QPainterPath()
        # Move to the new origin, and start a new path
        path.moveTo(origin.x(), origin.y())
        # Create a Bezier curve between origin and target, using the control
        # points (origin.x()+100, origin.y()) and (target.x()-100, target.y())
        path.cubicTo(origin.x() + self.bezier_param, origin.y(),
                     target.x() - self.bezier_param, target.y(),
                     target.x(), target.y())
        # Draw the path
        self.setPath(path)

    def mousePressEvent(self, event):
        if self.right_node and self.left_node:
            # first clean layout
            while self.ui.sub_pipeline.count() != 0:
                b = self.ui.sub_pipeline.takeAt(0)
                b.widget.close()
            # create widget
            popup = PartialView()
            popup.set_sub_pipeline(self.left_node, self.right_node)
            # add widget
            self.ui.sub_pipeline.addWidget(popup)

class PartialScene(QtGui.QGraphicsScene):
    def __init__(self, parent=None):
        super(PartialScene, self).__init__(parent)
        self.gnodes = {}
        self.glinks = {}
        self._pos = 50
        self.pos = {}

        self.changed.connect(self.update_paths)

    def add_gnode(self, gnode):
        """ Add a node to the scene

        Parameters
        ----------
        name: String
            name of the node to add
        gnode: NodeGWidget
            node to add
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
        self.pos[gnode_name] = gnode.pos()

    def add_glink(self, source, dest, active):
        """ Add a link between a source and a destination

        Parameters
        ----------
        source: tuple (node_name, parameter_name)
            the origin of the link
        dest: tuple (node_name, parameter_name)
            the destination of the link
        active: bool
            define if the link is active (in red) or inactive (in grey)
        """
        # Get source parameters
        source_node_name, source_plug_name = source
        if not source_node_name:
            # If no source name, put default source name : "inputs"
            source_gnode_name = 'inputs'
        else:
            source_gnode_name = source_node_name
        # Get the corresponding source node from node dict
        source_gnode = self.gnodes[source_gnode_name]

        # Get destination parameters
        dest_node_name, dest_plug_name = dest
        if not dest_node_name:
            # If no destination name, put default destination name : "outputs"
            dest_gnode_name = 'outputs'
        else:
            dest_gnode_name = dest_node_name
        # Get the corresponding destination node from node dict
        dest_gnode = self.gnodes[dest_gnode_name]

        # Test if destination parameter is in destination node in_plugs
        if dest_plug_name in dest_gnode.in_plugs:
            # Create link from source plug to destination plug
            glink = Link(
                source_gnode.mapToScene(
                    source_gnode.out_plugs[source_plug_name].get_plug_point()),
                dest_gnode.mapToScene(
                    dest_gnode.in_plugs[dest_plug_name].get_plug_point()),
                active)
            # Add link to links dictionary
            self.glinks[((source_gnode_name, source_plug_name),
                         (dest_gnode_name, dest_plug_name))] = glink
            self.addItem(glink)

    def set_sub_pipeline(self, source_node, dest_node):
        """ Generate the partial graphical interface of the pipeline :
        nodes, plugs, interplugs, links and interlinks
        """
        for node_type, node in zip(["source", "dest"],
                                   [source_node, dest_node]):
            inputs = [(plug_name if plug.activated else "+" + plug_name)
                      for plug_name, plug in node.plugs.iteritems()
                      if not plug.output]

            outputs = [(plug_name if plug.activated else "+" + plug_name)
                       for plug_name, plug in node.plugs.iteritems()
                       if plug.output]

            if isinstance(node, Switch):
                # If node is a switch, get "switch" style (yellow)
                style = 'switch'
            else:
                style = None

            # add nodes with inputs and outputs activated or not
            if node_type == "source":
                if not node.name:
                    self.add_gnode(FullNode("inputs", [], inputs,
                                            active=node.activated,
                                            style=style))
                else:
                    self.add_gnode(FullNode(node.name, [], outputs,
                                            active=node.activated,
                                            style=style))
            else:
                if not node.name:
                    self.add_gnode(FullNode("outputs", outputs, [],
                                            active=node.activated,
                                            style=style))
                else:
                    self.add_gnode(FullNode(node.name, inputs, [],
                                            active=node.activated,
                                            style=style))

        # Create all links between plugs
        for source_plug_name, source_plug in source_node.plugs.iteritems():
            for (_dest_node_name, _dest_plug_name, _dest_node, _dest_plug,
                 _only_if_activated) in source_plug.links_to:
                if not source_node.name:
                    # If no source name, put default source name: "inputs"
                    source_gnode_name = 'inputs'
                else:
                    source_gnode_name = source_node.name
                if not _dest_node_name:
                    # If no source name, put default dest name: "outputs"
                    dest_gnode_name = 'outputs'
                else:
                    dest_gnode_name = _dest_node_name
                if dest_gnode_name == dest_node.name or \
                        (dest_gnode_name == "outputs" and not dest_node.name):
                    self.add_glink((source_gnode_name, source_plug_name),
                                   (dest_gnode_name, _dest_plug_name),
                                   active=source_plug.activated and
                                   _dest_plug.activated)

    def update_paths(self):
        """ Update links between plugs
        """
        # Get the position of each node in a dictionary
        for i in self.items():
            if isinstance(i, FullNode):
                self.pos[i.name] = i.pos()

        # Iteration over all the links
        for source_dest, glink in self.glinks.iteritems():
            source, dest = source_dest
            source_gnode_name, source_plug_name = source
            dest_gnode_name, dest_plug_name = dest
            # Get source and destination nodes from node dictionary
            source_gnode = self.gnodes[source_gnode_name]
            dest_gnode = self.gnodes[dest_gnode_name]
            # Update links
            glink.update(
                source_gnode.mapToScene(
                    source_gnode.out_plugs[source_plug_name].get_plug_point()),
                dest_gnode.mapToScene(
                    dest_gnode.in_plugs[dest_plug_name].get_plug_point()))


class PartialView(QtGui.QGraphicsView):
    def __init__(self, parent=None):
        super(PartialView, self).__init__(parent)
        self.scene = None

    def set_sub_pipeline(self, source_node, dest_node):
        # Define items position
        if self.scene:
            pos = self.scene.pos
        # Create pipeline scene
        self.scene = PartialScene()
        #self.scene.pos = pos
        self.scene.set_sub_pipeline(source_node, dest_node)
        self.setWindowTitle(source_node.name + r"/" + dest_node.name
                            + " interaction")
        self.setScene(self.scene)

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
