#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from pprint import pprint

# Capsul import
from soma.qt_gui.qt_backend import QtCore, QtGui
from soma.sorted_dictionary import SortedDictionary
from capsul.pipeline.pipeline import Switch
from capsul.process import get_process_instance, Process
from soma.controller import Controller
try:
    from soma.gui.widget_controller_creation import ControllerWidget
except ImportError:
    # soma-base not available
    pass

# -----------------------------------------------------------------------------
# Globals and constants
# -----------------------------------------------------------------------------

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

GOLD_1 = QtGui.QColor.fromRgb(255, 229, 51)
GOLD_2 = QtGui.QColor.fromRgb(229, 153, 51)
LIGHT_GOLD_1 = QtGui.QColor.fromRgb(225, 239, 131)
LIGHT_GOLD_2 = QtGui.QColor.fromRgb(240, 197, 140)

BROWN_1 = QtGui.QColor.fromRgb(233, 198, 175)
BROWN_2 = QtGui.QColor.fromRgb(211, 141, 95)
LIGHT_BROWN_1 = QtCore.Qt.gray  # TBI
LIGHT_BROWN_2 = QtCore.Qt.gray  # TBI

RED_1 = QtGui.QColor.fromRgb(175, 54, 16)
RED_2 = QtGui.QColor.fromRgb(234, 131, 31)
LIGHT_RED_1 = QtCore.Qt.gray  # TBI
LIGHT_RED_2 = QtCore.Qt.gray  # TBI

PURPLE_1 = QtGui.QColor.fromRgbF(0.85, 0.8, 0.85, 1)
PURPLE_2 = QtGui.QColor.fromRgbF(0.8, 0.75, 0.8, 1)
DEEP_PURPLE_1 = QtGui.QColor.fromRgbF(0.8, 0.7, 0.8, 1)
DEEP_PURPLE_2 = QtGui.QColor.fromRgbF(0.6, 0.5, 0.6, 1)


# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------

class Plug(QtGui.QGraphicsPolygonItem):

    def __init__(self, name, height, width, activated=True, optional=False,
                 parent=None):
        super(Plug, self).__init__(parent)
        self.name = name
        if optional:
            if activated:
                color = QtCore.Qt.darkGreen
            else:
                color = QtGui.QColor('#BFDB91')
        else:
            if activated:
                color = QtCore.Qt.black
            else:
                color = QtCore.Qt.gray
        if True:
            brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
            brush.setColor(color)
            polygon = QtGui.QPolygonF([QtCore.QPointF(0, 0),
                                       QtCore.QPointF(
                                           width, (height - 5) / 2.0),
                                       QtCore.QPointF(0, height - 5)
                                       ])
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        else:
            brush = QtGui.QBrush(QtCore.Qt.Dense4Pattern)
            brush.setColor(color)
            polygon = QtGui.QPolygonF([QtCore.QPointF(0, 0),
                                       QtCore.QPointF(
                                           width / 3.0, (height - 5) / 4.0),
                                       QtCore.QPointF(width / 3.0, 0),
                                       QtCore.QPointF(
                                           width, (height - 5) / 2.0),
                                       QtCore.QPointF(
                                           width / 3.0, (height - 5)),
                                       QtCore.QPointF(
                                           width / 3.0, (height - 5) * 0.75),
                                       QtCore.QPointF(0, height - 5),
                                       ])
        self.setPolygon(polygon)
        self.setBrush(brush)
        self.setZValue(3)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

    def get_plug_point(self):
        point = QtCore.QPointF(
            self.boundingRect().size().width() / 2.0,
            self.boundingRect().size().height() / 2.0)
        return self.mapToParent(point)


    def mousePressEvent(self, event):
        super(Plug, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.scene().plug_clicked.emit(self.name)
            event.accept()


class NodeGWidget(QtGui.QGraphicsItem):

    _colors = {
        'default': (BLUE_1, BLUE_2, LIGHT_BLUE_1, LIGHT_BLUE_2),
        'switch': (SAND_1, SAND_2, LIGHT_SAND_1, LIGHT_SAND_2),
        'pipeline': (DEEP_PURPLE_1, DEEP_PURPLE_2, PURPLE_1, PURPLE_2),
    }

    def __init__(self, name, parameters, active=True,
                 style=None, parent=None, process=None, sub_pipeline=None):
        super(NodeGWidget, self).__init__(parent)
        if style is None:
            style = 'default'
        self.name = name
        self.parameters = parameters
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.in_plugs = {}
        self.out_plugs = {}
        self.active = active
        self.process = process
        self.sub_pipeline = sub_pipeline
        self.embedded_subpipeline = None

        if self.active:
            color_1, color_2 = self._colors[style][0:2]
        else:
            color_1, color_2 = self._colors[style][2:4]
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, color_1)
        gradient.setColorAt(1, color_2)
        self.bg_brush = QtGui.QBrush(gradient)

        if self.active:
            color_1 = GRAY_1
            color_2 = GRAY_2
        else:
            color_1 = LIGHT_GRAY_1
            color_2 = LIGHT_GRAY_2
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(1, color_1)
        gradient.setColorAt(0, color_2)
        self.title_brush = QtGui.QBrush(gradient)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton|QtCore.Qt.RightButton|QtCore.Qt.MiddleButton)

        self._build()

    def get_title(self):
        if self.sub_pipeline is None:
            return self.name
        else:
            return "[{0}]".format(self.name)

    def _build(self):
        margin = 5
        plug_width = 12
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        font = self.title.font()
        font.setWeight(QtGui.QFont.Bold)
        self.title.setFont(font)
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        # always add to group after setPos
        #self.addToGroup(self.title)
        self.title.setParentItem(self)

        pos = margin + margin + self.title.boundingRect().size().height()
        for in_param, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                continue
            param_name = QtGui.QGraphicsTextItem(in_param, self)
            plug_name = '%s:%s' % (self.name, in_param)
            plug = Plug(plug_name,param_name.boundingRect().size().height(),
                        plug_width, activated=pipeline_plug.activated,
                        optional=pipeline_plug.optional, parent=self)
            param_name.setZValue(2)
            plug.setPos(margin, pos)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            #self.addToGroup(param_name)
            #self.addToGroup(plug)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.in_plugs[in_param] = plug
            pos = pos + param_name.boundingRect().size().height()

        for out_param, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if not output:
                continue
            param_name = QtGui.QGraphicsTextItem(out_param, self)
            plug_name = '%s:%s' % (self.name, out_param)
            plug = Plug(plug_name,param_name.boundingRect().size().height(),
                        plug_width, activated=pipeline_plug.activated,
                        optional=pipeline_plug.optional, parent=self)
            param_name.setZValue(2)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            plug.setPos(plug.boundingRect().size().width() + margin +
                        param_name.boundingRect().size().width() + margin, pos)
            #self.addToGroup(plug)
            #self.addToGroup(param_name)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.out_plugs[out_param] = plug
            pos = pos + param_name.boundingRect().size().height()

        self.box = QtGui.QGraphicsRectItem(self)
        self.box.setBrush(self.bg_brush)
        self.box.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box.setZValue(-1)
        #self.addToGroup(self.box)
        self.box.setParentItem(self)
        self.box.setRect(self.contentsRect())

        self.box_title = QtGui.QGraphicsRectItem(self)
        rect = self.title.mapRectToParent(self.title.boundingRect())
        brect = self.contentsRect()
        brect.setWidth(brect.right() - margin * 2)
        rect.setWidth(brect.width())
        self.box_title.setRect(rect)
        self.box_title.setBrush(self.title_brush)
        self.box_title.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.addToGroup(self.box_title)
        self.box_title.setParentItem(self)

    def contentsRect(self):
        brect = QtCore.QRectF(0, 0, 0, 0)
        for child in self.childItems():
            if not child.isVisible() or child is self.box:
                continue
            item_rect = self.mapRectFromItem(child, child.boundingRect())
            if item_rect.right() > brect.right():
                brect.setRight(item_rect.right())
            if item_rect.bottom() > brect.bottom():
                brect.setBottom(item_rect.bottom())
        return brect

    def boundingRect(self):
        margin = 0
        brect = self.contentsRect()
        brect.setRight(brect.right() + margin * 2)
        brect.setBottom(brect.bottom() + margin * 2)
        return brect

    def paint(self, painter, option, widget=None):
        pass

    def postscript(self, file_name):
        printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)
        printer.setOutputFormat(QtGui.QPrinter.PostScriptFormat)
        printer.setOutputFileName(file_name)
        # qreal xmargin = contentRect.width()*0.01;
        # qreal ymargin = contentRect.height()*0.01;
        # printer.setPaperSize(10*contentRect.size()*1.02,QPrinter::DevicePixel);
        # printer.setPageMargins(xmargin,ymargin,xmargin,ymargin,QPrinter::DevicePixel);
        painter = QtGui.QPainter()
        painter.begin(printer)
        painter.setPen(QtCore.Qt.blue)
        painter.setFont(QtGui.QFont('Arial', 30))
        painter.drawText(0, 0, 'Ca marche !')
        # render(&painter,QRectF(QPointF(0,0),10*contentRect.size()),contentRect);
        painter.end()

    def add_subpipeline_view(self, sub_pipeline, allow_open_controller=True):
        if self.embedded_subpipeline:
            if self.embedded_subpipeline.isVisible():
                self.embedded_subpipeline.hide()
                self.box.setRect(self.boundingRect())
            else:
                self.embedded_subpipeline.show()
                self.box.setRect(self.boundingRect())
        else:
            sub_view = PipelineDevelopperView(sub_pipeline,
                show_sub_pipelines=True,
                allow_open_controller=allow_open_controller)
            margin = 5
            pos = margin * 2 + self.title.boundingRect().size().height()
            pwid = QtGui.QGraphicsProxyWidget(self)
            pwid.setWidget(sub_view)
            pwid.setPos(100, pos)
            #self.addToGroup(pwid)
            pwid.setParentItem(self)
            self.embedded_subpipeline = pwid
            self.box.setRect(self.boundingRect())
            #pwid.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)
            self.setFiltersChildEvents(False)

    def mouseDoubleClickEvent(self, event):
        if self.sub_pipeline:
            self.scene().subpipeline_clicked.emit(self.name, self.sub_pipeline,
                                                  event.modifiers())
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        item = self.scene().itemAt(event.scenePos())
        #print 'NodeGWidget click, item:', item
        if isinstance(item, Plug) and event.button() == QtCore.Qt.LeftButton:
            item.mousePressEvent(event)
            return
        #elif isinstance(item, QtGui.QGraphicsProxyWidget):
            ##print 'widget.'
            #event.accept()
        super(NodeGWidget, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.RightButton \
                and self.process is not None:
            self.scene().node_right_clicked.emit(self.name, self.process)
            event.accept()


class Link(QtGui.QGraphicsPathItem):

    def __init__(self, origin, target, active, weak, parent=None):
        super(Link, self).__init__(parent)
        pen = QtGui.QPen()
        pen.setWidth(2)
        if active:
            pen.setBrush(RED_2)
        else:
            pen.setBrush(QtCore.Qt.gray)
        if weak:
            pen.setStyle(QtCore.Qt.DashLine)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)

        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(origin.x() + 100, origin.y(),
                     target.x() - 100, target.y(),
                     target.x(), target.y())
        self.setPath(path)
        self.setPen(pen)
        self.setZValue(0.5)

    def update(self, origin, target):
        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(origin.x() + 100, origin.y(),
                     target.x() - 100, target.y(),
                     target.x(), target.y())

        self.setPath(path)


class PipelineScene(QtGui.QGraphicsScene):
    # Signal emitted when a sub pipeline has to be open.
    subpipeline_clicked = QtCore.Signal(str, Process,
                                        QtCore.Qt.KeyboardModifiers)
    # Signal emitted when a node box is right-clicked
    node_right_clicked = QtCore.Signal(str, Controller)
    # Signal emitted when a plug is clicked
    plug_clicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(PipelineScene, self).__init__(parent)
        self.gnodes = {}
        self.glinks = {}
        self._pos = 50
        self.pos = {}

        self.changed.connect(self.update_paths)

    def add_node(self, name, gnode):
        self.addItem(gnode)
        pos = self.pos.get(name)
        if pos is None:
            gnode.setPos(self._pos, self._pos)
            self._pos += 100
        else:
            gnode.setPos(pos)
        self.gnodes[name] = gnode

    def add_link(self, source, dest, active, weak):
        source_gnode_name, source_param = source
        if not source_gnode_name:
            source_gnode_name = 'inputs'
        source_gnode = self.gnodes[source_gnode_name]
        dest_gnode_name, dest_param = dest
        if not dest_gnode_name:
            dest_gnode_name = 'outputs'
        dest_gnode = self.gnodes.get(dest_gnode_name)
        if dest_gnode is not None:
            if dest_param in dest_gnode.in_plugs:
                glink = Link(
                    source_gnode.mapToScene(
                        source_gnode.out_plugs[source_param].get_plug_point()),
                    dest_gnode.mapToScene(
                        dest_gnode.in_plugs[dest_param].get_plug_point()),
                    active, weak)
                self.glinks[((source_gnode_name, source_param),
                            (dest_gnode_name, dest_param))] = glink
                self.addItem(glink)

    def update_paths(self):
        for i in self.items():
            if isinstance(i, NodeGWidget):
                self.pos[i.name] = i.pos()

        for source_dest, glink in self.glinks.iteritems():
            source, dest = source_dest
            source_gnode_name, source_param = source
            dest_gnode_name, dest_param = dest
            source_gnode = self.gnodes[source_gnode_name]
            dest_gnode = self.gnodes[dest_gnode_name]
            glink.update(source_gnode.mapToScene(
                source_gnode.out_plugs[source_param].get_plug_point()),
                dest_gnode.mapToScene(
                    dest_gnode.in_plugs[dest_param].get_plug_point()))

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline
        pipeline_inputs = SortedDictionary()
        pipeline_outputs = SortedDictionary()
        for name, plug in pipeline.nodes[''].plugs.iteritems():
            if plug.output:
                pipeline_outputs[name] = plug
            else:
                pipeline_inputs[name] = plug
        if pipeline_inputs:
            self.add_node(
                'inputs', NodeGWidget('inputs', pipeline_inputs,
                    active=pipeline.pipeline_node.activated,
                    process=pipeline))
        for node_name, node in pipeline.nodes.iteritems():
            if not node_name:
                continue
            process = None
            if isinstance(node, Switch):
                style = 'switch'
                process = node
            else:
                style = None
            if hasattr(node, 'process'):
                process = node.process
            if hasattr(node, 'process') and hasattr(node.process, 'nodes'):
                sub_pipeline = node.process
            elif hasattr(node, 'nodes'):
                sub_pipeline = node
            else:
                sub_pipeline = None
            if sub_pipeline and self.parent() is not None \
                    and hasattr(self.parent(), '_show_sub_pipelines') \
                    and self.parent()._show_sub_pipelines:
                # this test is not really pretty...
                style = 'pipeline'
            self.add_node(node_name, NodeGWidget(
                node_name, node.plugs, active=node.activated, style=style,
                sub_pipeline=sub_pipeline, process=process))
        if pipeline_outputs:
            self.add_node(
                'outputs', NodeGWidget('outputs', pipeline_outputs,
                                       active=pipeline.pipeline_node.activated,
                                       process=pipeline))

        for source_node_name, source_node in pipeline.nodes.iteritems():
            for source_parameter, source_plug in source_node.plugs.iteritems():
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated and dest_plug.activated,
                            weak=weak_link)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_P:
            event.accept()
            posdict = dict([(key, (value.x(), value.y())) \
                            for key, value in self.pos.iteritems()])
            print posdict
        else:
            super(PipelineScene, self).keyPressEvent(event)


    def link_tooltip_text(self, source_dest):
        node_name = source_dest[0][0]
        if node_name in ('inputs', 'outputs'):
            proc = self.pipeline
        else:
            src = self.pipeline.nodes[node_name]
            proc = src
            if hasattr(src, 'process'):
                proc = src.process
        name = source_dest[0][1]
        value = getattr(proc, name)
        #trait = proc.user_traits()[name]
        typestr = str(type(value)).replace('<', '').replace('>', '')
        msg = '''<h3>%s</h3>
<table>
  <tr>
    <td>type:</td>
    <td>%s</td>
  </tr>
  <tr>
    <td>value:</td>
    <td>%s</td>
  </tr>
</table>''' \
            % (source_dest[0][1], typestr, str(value))
        return msg

    def plug_tooltip_text(self, node, name):
        if node.name in ('inputs', 'outputs'):
            proc = self.pipeline
            splug = self.pipeline.pipeline_node.plugs[name]
        else:
            src = self.pipeline.nodes[node.name]
            splug = src.plugs[name]
            proc = src
            if hasattr(src, 'process'):
                proc = src.process
        if splug.output:
            output = '<font color="#d00000">output</font>'
        else:
            output = '<font color="#00d000">input</font>'
        if splug.enabled:
            enabled = 'enabled'
        else:
            enabled = '<font color="#a0a0a0">disabled</font>'
        if splug.activated:
            activated = 'activated'
        else:
            activated = '<font color="#a0a0a0">inactive</font>'
        if splug.optional:
            optional = '<font color="#00d000">optional</font>'
        else:
            optional = 'mandatory'
        value = getattr(proc, name)
        typestr = str(type(value)).replace('<', '').replace('>', '')
        msg = '''<h3>%s</h3>
<table cellspacing="6">
    <tr>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
    </tr>
</table>
<table>
    <tr>
      <td>type:</td>
      <td>%s</td>
    </tr>
    <tr>
      <td>value:</td>
      <td><b>%s</b></td>
    </tr>
</table>''' \
            % (name, output, optional, enabled, activated, typestr, str(value))
        return msg


    def helpEvent(self, event):
        '''
        Display tooltips on plugs and links
        '''
        item = self.itemAt(event.scenePos())
        #print 'helpEvent for', self, ', on:', item
        if isinstance(item, Link):
            for source_dest, glink in self.glinks.iteritems():
                if glink is item:
                    text = self.link_tooltip_text(source_dest)
                    item.setToolTip(text)
                    break
        elif isinstance(item, Plug):
            node = item.parentItem()
            found = False
            for name, plug in node.in_plugs.iteritems():
                if plug is item:
                    found = True
                    break
            if not found:
              for name, plug in node.out_plugs.iteritems():
                  if plug is item:
                      found = True
                      break
            if found:
                text = self.plug_tooltip_text(node, name)
                item.setToolTip(text)
        elif isinstance(item, QtGui.QGraphicsProxyWidget):
            # PROBLEM: tooltips in child graphics scenes seem no to popup.
            event.setAccepted(False)

        super(PipelineScene, self).helpEvent(event)


class PipelineDevelopperView(QtGui.QGraphicsView):
    '''
    Pipeline representation as a graph, using boxes and arrows.

    Based on Qt QGraphicsView, this can be used as a Qt QWidget.

    Qt signals are emitted on a right click on a node box, and on a double 
    click on a sub-pipeline box, to allow handling at a higher level. Default
    behaviors can be enabled using constructor parameters.
    '''
    subpipeline_clicked = QtCore.Signal(str, Process,
                                        QtCore.Qt.KeyboardModifiers)
    '''Signal emitted when a sub pipeline has to be open.'''
    node_right_clicked = QtCore.Signal(str, Controller)
    '''Signal emitted when a node box is right-clicked'''
    plug_clicked = QtCore.Signal(str)
    '''Signal emitted when a plug is right-clicked'''

    def __init__(self, pipeline, parent=None, show_sub_pipelines=False,
            allow_open_controller=False):
        '''
        Parameters
        ----------
        pipeline:  Pipeline (mandatory)
            pipeline object to be displayed
        parent:  QWidget (optional)
            parent widget
        show_sub_pipelines:  bool (optional)
            if set, sub-pipelines will appear as red/pink boxes and a double 
            click on one of them will open another window with the sub-pipeline
            structure in it
        allow_open_controller:  bool (optional)
            if set, a right click on any box will open another window with the
            underlying node controller, allowing to see and edit parameters
            values, switches states, etc.
        '''
        super(PipelineDevelopperView, self).__init__(parent)
        self.scene = None
        self._show_sub_pipelines = show_sub_pipelines
        self._allow_open_controller = allow_open_controller
        self.set_pipeline(pipeline)
        self._grab = False

    def _set_pipeline(self, pipeline):
        if self.scene:
            pos = self.scene.pos
            pprint(dict((i, (j.x(), j.y())) for i, j in pos.iteritems()))
        else:
            pos = dict((i, QtCore.QPointF(*j))
                       for i, j in pipeline.node_position.iteritems())
        self.scene = PipelineScene(self)
        self.scene.subpipeline_clicked.connect(self.subpipeline_clicked)
        self.scene.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)
        self.scene.node_right_clicked.connect(self.node_right_clicked)
        self.scene.node_right_clicked.connect(self.onOpenProcessController)
        self.scene.plug_clicked.connect(self.plug_clicked)
        self.scene.pos = pos
        self.scene.set_pipeline(pipeline)
        self.setWindowTitle(pipeline.name)
        self.setScene(self.scene)

        # Try to initialize the scene scale factor
        if hasattr(pipeline, "scene_scale_factor"):
            self.scale(
                pipeline.scene_scale_factor, pipeline.scene_scale_factor)


    def set_pipeline(self, pipeline):
        self._set_pipeline(pipeline)

        # Setup callback to update view when pipeline state is modified
        def reset_pipeline():
            self._set_pipeline(pipeline)
        pipeline.on_trait_change(reset_pipeline, 'selection_changed')

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.delta() < 0:
                self.zoom_out()
            else:
                self.zoom_in()
            event.accept()
        else:
            QtGui.QGraphicsView.wheelEvent(self, event)

    def mousePressEvent(self, event):
        super(PipelineDevelopperView, self).mousePressEvent(event)
        #item = self.itemAt(event.x(), event.y())
        # if item is None:
        if not event.isAccepted():
            self._grab = True
            self._grabpos = event.pos()

    def mouseReleaseEvent(self, event):
        self._grab = False
        super(PipelineDevelopperView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._grab:
            event.accept()
            translation = event.pos() - self._grabpos
            self._grabpos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(translation.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(translation.y()))
        else:
            super(PipelineDevelopperView, self).mouseMoveEvent(event)

    def onLoadSubPipelineClicked(self, node_name, sub_pipeline, modifiers):
        """ Event to load a sub pipeline
        """
        if self._show_sub_pipelines:
            if modifiers & QtCore.Qt.ControlModifier:
                gnode = self.scene.gnodes.get(str(node_name))
                if gnode is not None:
                    gnode.add_subpipeline_view(
                        sub_pipeline, self._allow_open_controller)
                    return
                else:
                    print 'node not found in:'
                    print self.scene.gnodes.keys()
            sub_view = PipelineDevelopperView(sub_pipeline,
                show_sub_pipelines=self._show_sub_pipelines,
                allow_open_controller=self._allow_open_controller)
            sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            sub_view.setWindowTitle(node_name)
            sub_view.show()

    def onOpenProcessController(self, node_name, process):
        """ Event to open a sub-process/sub-pipeline controller
        """
        if self._allow_open_controller:
            sub_view = QtGui.QScrollArea()
            cwidget = ControllerWidget(process, live=True)
            cwidget.setParent(sub_view)
            sub_view.setWidget(cwidget)
            sub_view.setWidgetResizable(True)
            sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            sub_view.setWindowTitle(node_name)
            sub_view.show()
            # keep this variable to avoid destroying the scroll area right now.
            # FIXME: in any case, ControllerWidget does never delete due to
            # cyclic references or something.
            # PipelineDevelopperView neither...
            cwidget._parent_scroll = sub_view
