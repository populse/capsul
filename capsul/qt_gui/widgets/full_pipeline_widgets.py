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
from pprint import pprint
import weakref

# Capsul import
from soma.qt_gui.qt_backend import QtCore, QtGui
from soma.sorted_dictionary import SortedDictionary
from capsul.pipeline.pipeline import Switch, PipelineNode, IterativeNode
from capsul.pipeline import pipeline_tools
from capsul.pipeline import Pipeline
from capsul.process import get_process_instance, Process
from soma.controller import Controller
from soma.utils.functiontools import SomaPartial
try:
    from traits import api as traits
except ImportError:
    from enthought.traits import api as traits

from capsul.qt_gui.controller_widget import ScrollControllerWidget

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
        color = self._color(activated, optional)
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

    def _color(self, activated, optional):
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
        return color

    def update_plug(self, activated, optional):
        color = self._color(activated, optional)
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        brush.setColor(color)
        self.setBrush(brush)

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

class EmbeddedSubPipelineItem(QtGui.QGraphicsProxyWidget):
    '''
    QGraphicsItem containing a sub-pipeline view
    '''

    def __init__(self, sub_pipeline_wid):
        super(EmbeddedSubPipelineItem, self).__init__()
        old_height = sub_pipeline_wid.sizeHint().height()
        sizegrip = QtGui.QSizeGrip(None)
        new_height = old_height \
            + sub_pipeline_wid.horizontalScrollBar().height()
        sub_pipeline_wid.setCornerWidget(sizegrip)
        sub_pipeline_wid.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn)
        sub_pipeline_wid.resize(sub_pipeline_wid.sizeHint().width(), new_height)
        self.setWidget(sub_pipeline_wid)


class NodeGWidget(QtGui.QGraphicsItem):

    _colors = {
        'default': (BLUE_1, BLUE_2, LIGHT_BLUE_1, LIGHT_BLUE_2),
        'switch': (SAND_1, SAND_2, LIGHT_SAND_1, LIGHT_SAND_2),
        'pipeline': (DEEP_PURPLE_1, DEEP_PURPLE_2, PURPLE_1, PURPLE_2),
    }

    def __init__(self, name, parameters, active=True,
                 style=None, parent=None, process=None, sub_pipeline=None,
                 colored_parameters=True, runtime_enabled=True):
        super(NodeGWidget, self).__init__(parent)
        if style is None:
            style = 'default'
        self.style = style
        self.name = name
        self.parameters = parameters
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.in_plugs = {}
        self.in_params = {}
        self.out_plugs = {}
        self.out_params = {}
        self.active = active
        self.process = process
        self.sub_pipeline = sub_pipeline
        self.embedded_subpipeline = None
        self.colored_parameters = colored_parameters
        self.runtime_enabled = runtime_enabled

        self._set_brush()
        self.setAcceptedMouseButtons(
            QtCore.Qt.LeftButton|QtCore.Qt.RightButton|QtCore.Qt.MiddleButton)

        self._build()
        if colored_parameters:
            process.on_trait_change(self._repaint_parameter)

    def __del__(self):
        if self.colored_parameters:
            self.process.on_trait_change(self._repaint_parameter, remove=True)
        #super(NodeGWidget, self).__del__()

    def get_title(self):
        if self.sub_pipeline is None:
            return self.name
        else:
            return "[{0}]".format(self.name)

    def _repaint_parameter(self, param_name, new_value):
        if param_name not in self.parameters:
            return
        param_text = self._parameter_text(param_name)
        param_item = self.in_params.get(param_name)
        if param_item is None:
            param_item = self.out_params[param_name]
        param_item.setHtml(param_text)

    def _build(self):
        margin = 5
        plug_width = 12
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        font = self.title.font()
        font.setWeight(QtGui.QFont.Bold)
        self.title.setFont(font)
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        self.title.setParentItem(self)

        pos = margin + margin + self.title.boundingRect().size().height()
        for in_param, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                continue
            param_text = self._parameter_text(in_param)
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml(param_text)
            plug_name = '%s:%s' % (self.name, in_param)
            plug = Plug(plug_name, param_name.boundingRect().size().height(),
                        plug_width, activated=pipeline_plug.activated,
                        optional=pipeline_plug.optional, parent=self)
            param_name.setZValue(2)
            plug.setPos(margin, pos)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.in_plugs[in_param] = plug
            self.in_params[in_param] = param_name
            pos = pos + param_name.boundingRect().size().height()

        for out_param, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if not output:
                continue
            param_text = self._parameter_text(out_param)
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml(param_text)
            plug_name = '%s:%s' % (self.name, out_param)
            plug = Plug(plug_name, param_name.boundingRect().size().height(),
                        plug_width, activated=pipeline_plug.activated,
                        optional=pipeline_plug.optional, parent=self)
            param_name.setZValue(2)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            plug.setPos(plug.boundingRect().size().width() + margin +
                        param_name.boundingRect().size().width() + margin, pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.out_plugs[out_param] = plug
            self.out_params[out_param] = param_name
            pos = pos + param_name.boundingRect().size().height()

        self.box = QtGui.QGraphicsRectItem(self)
        self.box.setBrush(self.bg_brush)
        self.box.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box.setZValue(-1)
        self.box.setParentItem(self)
        self.box.setRect(self.contentsRect())

        self.box_title = QtGui.QGraphicsRectItem(self)
        rect = self.title.mapRectToParent(self.title.boundingRect())
        brect = self.contentsRect()
        brect.setWidth(brect.right() - margin)
        rect.setWidth(brect.width())
        self.box_title.setRect(rect)
        self.box_title.setBrush(self.title_brush)
        self.box_title.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box_title.setParentItem(self)

    def _set_brush(self):
        if self.active:
            color_1, color_2 = self._colors[self.style][0:2]
        else:
            color_1, color_2 = self._colors[self.style][2:4]
        if not self.runtime_enabled:
            color_1 = self._color_disabled(color_1)
            color_2 = self._color_disabled(color_2)
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
        if not self.runtime_enabled:
            color_1 = self._color_disabled(color_1)
            color_2 = self._color_disabled(color_2)
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(1, color_1)
        gradient.setColorAt(0, color_2)
        self.title_brush = QtGui.QBrush(gradient)

    def _color_disabled(self, color):
        target = [220, 240, 220]
        new_color = QtGui.QColor((color.red() + target[0]) / 2,
                                 (color.green() + target[1]) / 2,
                                 (color.blue() + target[2]) / 2)
        return new_color

    def _create_parameter(self, param_name, pipeline_plug):
        plug_width = 12
        margin = 5
        output = (not pipeline_plug.output if self.name in (
            'inputs', 'outputs') else pipeline_plug.output)
        param_text = self._parameter_text(param_name)
        param_name_item = QtGui.QGraphicsTextItem(self)
        param_name_item.setHtml(param_text)
        plug_name = '%s:%s' % (self.name, param_name)
        plug = Plug(plug_name, param_name_item.boundingRect().size().height(),
                    plug_width, activated=pipeline_plug.activated,
                    optional=pipeline_plug.optional, parent=self)
        param_name_item.setZValue(2)
        if output:
            plugs = self.out_plugs
            params = self.out_params
            params_size = len(params) + len(self.in_params)
            # FIXME: sub-pipeline size
            xpos = plug.boundingRect().size().width() + margin
            pxpos = plug.boundingRect().size().width() + margin * 2 \
                + param_name_item.boundingRect().size().width()
        else:
            plugs = self.in_plugs
            params = self.in_params
            params_size = len(params)
            xpos = plug.boundingRect().size().width() + margin
            pxpos = margin
        pos = margin * 2 + self.title.boundingRect().size().height() \
            + param_name_item.boundingRect().size().height() * params_size
        param_name_item.setPos(xpos, pos)
        plug.setPos(pxpos, pos)
        param_name_item.setParentItem(self)
        plug.setParentItem(self)
        plugs[param_name] = plug
        params[param_name] = param_name_item
        if output:
            self._shift_params()

    def _shift_params(self):
        margin = 5
        if not self.in_params:
            if not self.out_params:
                return # nothing to do.
            else:
                param_item = self.out_params.values()[0]
        else:
            param_item = self.in_params.values()[0]
        ni = 0
        no = 0
        for param_name, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                params = self.out_params
                plugs = self.out_plugs
                npos = no + len(self.in_params)
                no += 1
            else:
                params = self.in_params
                plugs = self.in_plugs
                npos = ni
                ni += 1
            pos = margin * 2 + self.title.boundingRect().size().height() \
                + param_item.boundingRect().size().height() * npos
            param_item = params[param_name]
            plug = plugs[param_name]
            ppos = param_item.pos()
            param_item.setPos(ppos.x(), pos)
            ppos = plug.pos()
            plug.setPos(ppos.x(), pos)
            pos += param_item.boundingRect().size().height()

    def _remove_parameter(self, param_name):
        if param_name in self.in_params:
            params = self.in_params
            plugs = self.in_plugs
        else:
            params = self.out_params
            plugs = self.out_plugs
        param_item = params[param_name]
        self.scene().removeItem(param_item)
        plug = plugs[param_name]
        self.scene().removeItem(plug)
        del params[param_name]
        del plugs[param_name]
        self._shift_params()

    def _parameter_text(self, param_name):
        pipeline_plug = self.parameters[param_name]
        #output = (not pipeline_plug.output if self.name in (
            #'inputs', 'outputs') else pipeline_plug.output)
        output = pipeline_plug.output
        if output:
            param_text = '<font color="#400000">%s</font>' % param_name
        else:
            param_text = param_name
        value = getattr(self.process, param_name)
        if value is None or value is traits.Undefined or value == '':
            param_text = '<em>%s</em>' % param_text
        else:
            trait = self.process.user_traits()[param_name]
            if (isinstance(trait.trait_type, traits.File) \
                    or isinstance(trait.trait_type, traits.Directory)) \
                    and os.path.exists(value):
                param_text = '<b>%s</b>' % param_text
        return param_text

    def update_node(self):
        # print 'update_node', self.name
        self._set_brush()
        self.box_title.setBrush(self.title_brush)
        self.box.setBrush(self.bg_brush)
        for param, pipeline_plug in self.parameters.iteritems():
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                plugs = self.out_plugs
                params = self.out_params
            else:
                plugs = self.in_plugs
                params = self.in_params
            gplug = plugs.get(param)
            if gplug is None: # new parameter ?
                self._create_parameter(param, pipeline_plug)
                gplug = plugs.get(param)
            gplug.update_plug(pipeline_plug.activated, pipeline_plug.optional)
            params[param].setHtml(self._parameter_text(param))

        # check removed params
        to_remove = []
        for param in self.in_params:
            if param not in self.parameters:
                to_remove.append(param)
        for param in self.out_params:
            if param not in self.parameters:
                to_remove.append(param)
        for param in to_remove:
            self._remove_parameter(param)
        self.box.setRect(self.boundingRect())

    def contentsRect(self):
        brect = QtCore.QRectF(0, 0, 0, 0)
        first = True
        excluded = []
        for name in ('box', 'box_title'):
            if hasattr(self, name):
                excluded.append(getattr(self, name))
        for child in self.childItems():
            if not child.isVisible() or child in excluded:
                continue
            item_rect = self.mapRectFromItem(child, child.boundingRect())
            if first:
                first = False
                brect = item_rect
            else:
                if child is self.embedded_subpipeline:
                    margin = 5
                    item_rect.setBottom(item_rect.bottom() + margin)
                if item_rect.left() < brect.left():
                    brect.setLeft(item_rect.left())
                if item_rect.top() < brect.top():
                    brect.setTop(item_rect.top())
                if item_rect.right() > brect.right():
                    brect.setRight(item_rect.right())
                if item_rect.bottom() > brect.bottom():
                    brect.setBottom(item_rect.bottom())
        return brect

    def boundingRect(self):
        margin = 0
        brect = self.contentsRect()
        if self.embedded_subpipeline and self.embedded_subpipeline.isVisible():
            margin = 5
        brect.setRight(brect.right())
        brect.setBottom(brect.bottom() + margin)
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

    def resize_subpipeline_on_show(self):
        margin = 5
        param_width = self.in_params_width()
        pos = margin * 2 + self.title.boundingRect().size().height()
        opos = param_width \
            + self.embedded_subpipeline.boundingRect().width() # + margin ?
        for name, param in self.out_params.iteritems():
            param.setPos(opos, param.pos().y())
            plug = self.out_plugs[name]
            plug.setPos(opos + margin + param.boundingRect().size().width(),
                plug.pos().y())
        rect = self.box_title.boundingRect()
        rect.setWidth(self.contentsRect().width())
        self.box_title.setRect(rect)
        self.box.setRect(self.boundingRect())

    def resize_subpipeline_on_hide(self):
        margin = 5
        for name, param in self.out_params.iteritems():
            plug = self.out_plugs[name]
            param.setPos(plug.boundingRect().width() + margin, param.pos().y())
            plug.setPos(plug.boundingRect().size().width() + margin +
                param.boundingRect().size().width() + margin, plug.pos().y())
        rect = self.box_title.boundingRect()
        rect.setWidth(self.contentsRect().width())
        self.box_title.setRect(rect)
        self.box.setRect(self.boundingRect())

    def in_params_width(self):
        margin = 5
        width = 0
        pwidth = 0
        for param_name, param in self.in_params.iteritems():
            if param.boundingRect().width() > width:
                width = param.boundingRect().width()
            if pwidth == 0:
                plug = self.in_plugs[param_name]
                pwidth = plug.boundingRect().width()
        return width + margin + pwidth

    def out_params_width(self):
        width = 0
        for param_name, param in self.out_params.iteritems():
            if param.boundingRect().width() > width:
                width = param.boundingRect().width()
        return width

    def add_subpipeline_view(
            self,
            sub_pipeline,
            allow_open_controller=True,
            scale=None):
        if self.embedded_subpipeline:
            if self.embedded_subpipeline.isVisible():
                self.embedded_subpipeline.hide()
                self.resize_subpipeline_on_hide()
            else:
                self.embedded_subpipeline.show()
                self.resize_subpipeline_on_show()
        else:
            sub_view = PipelineDevelopperView(sub_pipeline,
                show_sub_pipelines=True,
                allow_open_controller=allow_open_controller)
            if scale is not None:
                sub_view.scale(scale, scale)
            pwid = EmbeddedSubPipelineItem(sub_view)
            sub_view._graphics_item = weakref.proxy(pwid)
            margin = 5
            pos = margin * 2 + self.title.boundingRect().size().height()
            pwid.setParentItem(self)
            pwid.setPos(self.in_params_width(), pos)
            self.embedded_subpipeline = pwid
            self.resize_subpipeline_on_show()
            self.setFiltersChildEvents(False)
            pwid.geometryChanged.connect(self.resize_subpipeline_on_show)

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
        super(NodeGWidget, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.RightButton \
                and self.process is not None:
            self.scene().node_right_clicked.emit(self.name, self.process)
            event.accept()


class Link(QtGui.QGraphicsPathItem):

    def __init__(self, origin, target, active, weak, parent=None):
        super(Link, self).__init__(parent)
        self._set_pen(active, weak)

        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(origin.x() + 100, origin.y(),
                     target.x() - 100, target.y(),
                     target.x(), target.y())
        self.setPath(path)
        self.setZValue(0.5)

    def _set_pen(self, active, weak):
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
        self.setPen(pen)

    def update(self, origin, target):
        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(origin.x() + 100, origin.y(),
                     target.x() - 100, target.y(),
                     target.x(), target.y())

        self.setPath(path)

    def update_activation(self, active, weak):
        self._set_pen(active, weak)


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
        self.colored_parameters = True

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
        dest_gnode_name, dest_param = dest
        if not dest_gnode_name:
            dest_gnode_name = 'outputs'
        source_dest = ((source_gnode_name, source_param),
            (dest_gnode_name, dest_param))
        if source_dest in self.glinks:
            return # already done
        source_gnode = self.gnodes[source_gnode_name]
        dest_gnode = self.gnodes.get(dest_gnode_name)
        if dest_gnode is not None:
            if dest_param in dest_gnode.in_plugs:
                glink = Link(
                    source_gnode.mapToScene(
                        source_gnode.out_plugs[source_param].get_plug_point()),
                    dest_gnode.mapToScene(
                        dest_gnode.in_plugs[dest_param].get_plug_point()),
                    active, weak)
                self.glinks[source_dest] = glink
                self.addItem(glink)

    def _remove_link(self, source_dest):
        source, dest = source_dest
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
                glink = self.glinks[((source_gnode_name, source_param),
                    (dest_gnode_name, dest_param))]
                self.removeItem(glink)
                del self.glinks[((source_gnode_name, source_param),
                    (dest_gnode_name, dest_param))]

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
                    process=pipeline,
                    colored_parameters=self.colored_parameters))
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
            if isinstance(node, PipelineNode) \
                    or isinstance(node, IterativeNode):
                sub_pipeline = node.process
            else:
                sub_pipeline = None
            if sub_pipeline and self.parent() is not None \
                    and hasattr(self.parent(), '_show_sub_pipelines') \
                    and self.parent()._show_sub_pipelines:
                # this test is not really pretty...
                style = 'pipeline'
            self.add_node(node_name, NodeGWidget(
                node_name, node.plugs, active=node.activated, style=style,
                sub_pipeline=sub_pipeline, process=process,
                colored_parameters=self.colored_parameters,
                runtime_enabled=self.is_node_runtime_enabled(node)))
        if pipeline_outputs:
            self.add_node(
                'outputs', NodeGWidget(
                    'outputs', pipeline_outputs,
                    active=pipeline.pipeline_node.activated,
                    process=pipeline,
                    colored_parameters=self.colored_parameters))

        for source_node_name, source_node in pipeline.nodes.iteritems():
            for source_parameter, source_plug in source_node.plugs.iteritems():
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated \
                                and dest_plug.activated,
                            weak=weak_link)

    def is_node_runtime_enabled(self, node):
        steps = getattr(self.pipeline, 'pipeline_steps', None)
        if steps is None:
            return True
        in_steps = [step for step, trait in steps.user_traits().iteritems()
                    if node.name in trait.nodes
                    and getattr(steps, step) is False]
        # enabled: if in no disabled step
        return len(in_steps) == 0

    def update_pipeline(self):
        pipeline = self.pipeline
        for node_name, gnode in self.gnodes.iteritems():
            if node_name in ('inputs', 'outputs'):
                node = pipeline.nodes['']
                # in case traits have been added/removed
                if node_name == 'inputs':
                    pipeline_inputs = SortedDictionary()
                    for name, plug in node.plugs.iteritems():
                        if not plug.output:
                            pipeline_inputs[name] = plug
                    gnode.parameters = pipeline_inputs
                else:
                    pipeline_outputs = SortedDictionary()
                    for name, plug in node.plugs.iteritems():
                        if plug.output:
                            pipeline_outputs[name] = plug
                    gnode.parameters = pipeline_outputs
            else:
                node = pipeline.nodes[node_name]
                gnode.runtime_enabled = self.is_node_runtime_enabled(node)
            gnode.active = node.activated
            gnode.update_node()
        to_remove = []
        for source_dest, glink in self.glinks.iteritems():
            source, dest = source_dest
            source_node_name, source_param = source
            dest_node_name, dest_param = dest
            if source_node_name == 'inputs':
                source_node_name = ''
            if dest_node_name == 'outputs':
                dest_node_name = ''
            source_plug \
                = pipeline.nodes[source_node_name].plugs.get(source_param)
            dest_plug = pipeline.nodes[dest_node_name].plugs.get(dest_param)
            remove_glink = False
            if source_plug is None or dest_plug is None:
                # plug[s] removed
                remove_glink = True
            else:
                active = source_plug.activated and dest_plug.activated
                weak = [x[4] for x in source_plug.links_to \
                    if x[:2] == (dest_node_name, dest_param)]
                if len(weak) == 0:
                    # link removed
                    remove_glink = True
                else:
                    weak = weak[0]
            if remove_glink:
                to_remove.append(source_dest)
            else:
                glink.update_activation(active, weak)
        for source_dest in to_remove:
            self._remove_link(source_dest)
        # check added links
        for source_node_name, source_node in pipeline.nodes.iteritems():
            for source_parameter, source_plug in source_node.plugs.iteritems():
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated \
                                and dest_plug.activated,
                            weak=weak_link)

    def keyPressEvent(self, event):
        super(PipelineScene, self).keyPressEvent(event)
        if not event.isAccepted() and event.key() == QtCore.Qt.Key_P:
            done = True
            event.accept()
            posdict = dict([(key, (value.x(), value.y())) \
                            for key, value in self.pos.iteritems()])
            pprint(posdict)

    def link_tooltip_text(self, source_dest):
        source_node_name = source_dest[0][0]
        dest_node_name = source_dest[1][0]
        if source_node_name in ('inputs', 'outputs'):
            proc = self.pipeline
            source_node_name = ''
            source_node = self.pipeline.nodes[source_node_name]
        else:
            source_node = self.pipeline.nodes[source_node_name]
            proc = source_node
            if hasattr(source_node, 'process'):
                proc = source_node.process
        if dest_node_name in ('inputs', 'outputs'):
            dest_node_name = ''
        splug = source_node.plugs[source_dest[0][1]]
        link = [l for l in splug.links_to \
            if l[0] == dest_node_name and l[1] == source_dest[1][1]][0]
        if splug.activated and link[3].activated:
            active = '<font color="#ffa000">activated</font>'
        else:
            active = '<font color="#a0a0a0">inactive</font>'
        if link[4]:
            weak = '<font color="#e0c0c0">weak</font>'
        else:
            weak = '<b>strong</b>'
        name = source_dest[0][1]
        value = getattr(proc, name)
        #trait = proc.user_traits()[name]
        trait_type = proc.user_traits()[name].trait_type
        trait_type_str = str(trait_type)
        trait_type_str = trait_type_str[: trait_type_str.find(' object ')]
        trait_type_str = trait_type_str[trait_type_str.rfind('.') + 1:]
        typestr = ('%s (%s)' % (str(type(value)), trait_type_str)).replace(
            '<', '').replace('>', '')
        msg = '''<h3>%s</h3>
<table cellspacing="6">
    <tr>
      <td><b>Link:</b></td>
      <td>%s</td>
      <td>%s</td>
    </tr>
</table>
<table>
  <tr>
    <td><b>type:</b></td>
    <td>%s</td>
  </tr>
  <tr>
    <td><b>value:</b></td>
    <td>%s</td>
  </tr>
''' \
            % (source_dest[0][1], active, weak, typestr, str(value))
        if isinstance(trait_type, traits.File) \
                or isinstance(trait_type, traits.Directory) \
                or isinstance(trait_type, traits.Any):
            if self.is_existing_path(value):
                msg += '''    <tr>
      <td></td>
      <td>existing path</td>
    </tr>
'''
            elif not isinstance(trait_type, traits.Any):
                msg +=  '''    <tr>
      <td></td>
      <td><font color="#a0a0a0">non-existing path</font></td>
    </tr>
'''
        msg += '</table>'
        return msg

    @staticmethod
    def is_existing_path(value):
        if value not in (None, traits.Undefined) \
                and type(value) in (str, unicode) and os.path.exists(value):
            return True
        return False

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
        trait_type = proc.user_traits()[name].trait_type
        trait_type_str = str(trait_type)
        trait_type_str = trait_type_str[: trait_type_str.find(' object ')]
        trait_type_str = trait_type_str[trait_type_str.rfind('.') + 1:]
        typestr = ('%s (%s)' % (str(type(value)), trait_type_str)).replace(
            '<', '').replace('>', '')
        msg = '''<h3>%s</h3>
<table cellspacing="6">
    <tr>
      <td><b>Plug:</b></td>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
    </tr>
</table>
<table>
    <tr>
      <td><b>type:</b></td>
      <td>%s</td>
    </tr>
    <tr>
      <td><b>value:</b></td>
      <td>%s</td>
    </tr>
''' \
            % (name, output, optional, enabled, activated, typestr, str(value))
        if isinstance(trait_type, traits.File) \
                or isinstance(trait_type, traits.Directory) \
                or isinstance(trait_type, traits.Any):
            if self.is_existing_path(value):
                msg += '''    <tr>
      <td></td>
      <td>existing path</td>
    </tr>
'''
            elif not isinstance(trait_type, traits.Any):
                msg +=  '''    <tr>
      <td></td>
      <td><font color="#a0a0a0">non-existing path</font></td>
    </tr>
'''
        msg += '</table>'
        return msg


    def helpEvent(self, event):
        '''
        Display tooltips on plugs and links
        '''
        item = self.itemAt(event.scenePos())
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
            #
            # to force them we would have to translate the event position to
            # the sub-scene position, and call the child scene helpEvent()
            # method, with a custom event.
            # However this is not possible, since QGraphicsSceneHelpEvent
            # does not provide a public (nor even protected) constructor, and
            # secondarily helpEvent() is protected.
            event.setAccepted(False)

        super(PipelineScene, self).helpEvent(event)


class PipelineDevelopperView(QtGui.QGraphicsView):
    '''
    Pipeline representation as a graph, using boxes and arrows.

    Based on Qt QGraphicsView, this can be used as a Qt QWidget.

    Qt signals are emitted on a right click on a node box, and on a double 
    click on a sub-pipeline box, to allow handling at a higher level. Default
    behaviors can be enabled using constructor parameters.

    Ctrl + double click opens sub-pipelines in embedded views inside their
    parent box.

    Attributes
    ----------
    subpipeline_clicked
    node_right_clicked
    plug_clicked
    colored_parameters
    scene

    Methods
    -------
    __init__
    set_pipeline
    zoom_in
    zoom_out
    add_embedded_subpipeline
    onLoadSubPipelineClicked
    onOpenProcessController
    '''
    subpipeline_clicked = QtCore.Signal(str, Process,
                                        QtCore.Qt.KeyboardModifiers)
    '''Signal emitted when a sub pipeline has to be open.'''
    node_right_clicked = QtCore.Signal(str, Controller)
    '''Signal emitted when a node box is right-clicked'''
    plug_clicked = QtCore.Signal(str)
    '''Signal emitted when a plug is right-clicked'''
    scene = None
    '''
    type: PipelineScene

    the main scene.
    '''
    colored_parameters = True
    '''
    If enabled (default), parameters in nodes boxes are displayed with color
    codes representing their state, and the state of their values: output
    parameters, empty values, existing files, non-existing files...

    When colored_parameters is set, however, callbacks have to be installed to
    track changes in traits values, so this actually has an overhead.
    When colored_parameters is used, the color code is as follows:

    * black pamameter name: input
    * red parameter name: output
    * italics parameter name: Undefined, None, or empty string value
    * bold parameter name: existing file or directory name
    * regular font parameter name: non-existing file, or non-file parameter type
    * black plug: mandatory
    * green plug: optional
    * grey plug: mandatory, inactive
    * light green plug: optional, inactive
    * grey link: inactive
    * orange link: active
    * dotted line link: weak link
    '''

    def __init__(self, pipeline, parent=None, show_sub_pipelines=False,
            allow_open_controller=False):
        '''PipelineDevelopperView

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
        self.colored_parameters = True
        self._show_sub_pipelines = show_sub_pipelines
        self._allow_open_controller = allow_open_controller

        # Check that we have a pipeline or a process
        if not isinstance(pipeline, Pipeline):
            if isinstance(pipeline, Process):
                process = pipeline
                pipeline = Pipeline()
                pipeline.add_process(process.name, process.id)
                pipeline.autoexport_nodes_parameters()
                pipeline.node_position["inputs"] = (0., 0.)
                pipeline.node_position[process.name] = (300., 0.)
                pipeline.node_position["outputs"] = (600., 0.)
                pipeline.scene_scale_factor = 0.5
            else:
                raise Exception("Expect a Pipeline or a Process, not a "
                                "'{0}'.".foramt(repr(pipeline)))

        self.set_pipeline(pipeline)
        self._grab = False

    def __del__(self):
        if self.scene.pipeline:
            pipeline = self.scene.pipeline
            if hasattr(pipeline, 'pipeline_steps'):
                pipeline.pipeline_steps.on_trait_change(
                    self._reset_pipeline, remove=True)
            pipeline.on_trait_change(self._reset_pipeline,
                                     'selection_changed', remove=True)
            pipeline.on_trait_change(self._reset_pipeline,
                                     'user_traits_changed', remove=True)
        #super(PipelineDevelopperView, self).__del__()

    def _set_pipeline(self, pipeline):
        if self.scene:
            pos = self.scene.pos
            pprint(dict((i, (j.x(), j.y())) for i, j in pos.iteritems()))
        else:
            pos = dict((i, QtCore.QPointF(*j))
                       for i, j in pipeline.node_position.iteritems())
        self.scene = PipelineScene(self)
        self.scene.colored_parameters = self.colored_parameters
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
        '''
        Assigns a new pipeline to the view.
        '''
        self._set_pipeline(pipeline)

        # Setup callback to update view when pipeline state is modified
        pipeline.on_trait_change(self._reset_pipeline, 'selection_changed')
        pipeline.on_trait_change(self._reset_pipeline, 'user_traits_changed')
        if hasattr(pipeline, 'pipeline_steps'):
            pipeline.pipeline_steps.on_trait_change(
                self._reset_pipeline)

    def _reset_pipeline(self):
        # print 'reset pipeline'
        #self._set_pipeline(pipeline)
        self.scene.update_pipeline()

    def zoom_in(self):
        '''
        Zoom the view in, applying a 1.2 zoom factor
        '''
        self.scale(1.2, 1.2)

    def zoom_out(self):
        '''
        Zoom the view out, applying a 1/1.2 zool factor
        '''
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def wheelEvent(self, event):
        done = False
        if event.modifiers() == QtCore.Qt.ControlModifier:
            item = self.itemAt(event.pos())
            if not isinstance(item, QtGui.QGraphicsProxyWidget):
                done = True
                if event.delta() < 0:
                    self.zoom_out()
                else:
                    self.zoom_in()
                event.accept()
        if not done:
            super(PipelineDevelopperView, self).wheelEvent(event)

    def mousePressEvent(self, event):
        super(PipelineDevelopperView, self).mousePressEvent(event)
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

    def add_embedded_subpipeline(self, subpipeline_name, scale=None):
        '''
        Adds an embedded sub-pipeline inside its parent node.
        '''
        gnode = self.scene.gnodes.get(str(subpipeline_name))
        sub_pipeline = self.scene.pipeline.nodes[str(subpipeline_name)].process
        if gnode is not None:
            gnode.add_subpipeline_view(
                sub_pipeline, self._allow_open_controller, scale=scale)

    def onLoadSubPipelineClicked(self, node_name, sub_pipeline, modifiers):
        """ Event to load a open a sub-pipeline view.
        If ctrl is pressed the new view will be embedded in its parent node box.
        """
        if self._show_sub_pipelines:
            if modifiers & QtCore.Qt.ControlModifier:
                try:
                    self.add_embedded_subpipeline(node_name)
                    return
                except KeyError:
                    print 'node not found in:'
                    print self.scene.gnodes.keys()
            sub_view = PipelineDevelopperView(sub_pipeline,
                show_sub_pipelines=self._show_sub_pipelines,
                allow_open_controller=self._allow_open_controller)
            # set self.window() as QObject parent (not QWidget parent) to
            # prevent the sub_view to close/delete immediately
            QtCore.QObject.setParent(sub_view, self.window())
            sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            sub_view.setWindowTitle(node_name)
            sub_view.show()

    def window(self):
        '''
        window() is overloaded from QWidget.window() to handle embedded views
        cases.
        A PipelineDevelopperView may be displayed inside a NodeGWidget.
        In this case, we want to go up to the parent scene's window to the
        "real" top window, where QWidget.window() will end in the current
        graphics scene.
        '''
        if hasattr(self, '_graphics_item'):
            return self._graphics_item.scene().views()[0].window()
        else:
            return super(PipelineDevelopperView, self).window()

    def onOpenProcessController(self, node_name, process):
        """ Event to open a sub-process/sub-pipeline controller
        """
        if self._allow_open_controller:
            self.openPopupMenu(node_name, process)

    def openProcessController(self):
        sub_view = QtGui.QScrollArea()
        node_name = self.current_node_name
        if node_name in ('inputs', 'outputs'):
            node_name = ''
        process = self.scene.pipeline.nodes[node_name]
        if hasattr(process, 'process'):
            process = process.process
        cwidget = ScrollControllerWidget(process, live=True)
        cwidget.setParent(sub_view)
        sub_view.setWidget(cwidget)
        sub_view.setWidgetResizable(True)
        sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        sub_view.setWindowTitle(self.current_node_name)
        sub_view.show()
        # set self.window() as QObject parent (not QWidget parent) to
        # prevent the sub_view to close/delete immediately
        QtCore.QObject.setParent(sub_view, self.window())

    def openPopupMenu(self, node_name, process):
        """ right-click popup menu for nodes
        """
        menu = QtGui.QMenu('Nodes handling', None)
        node_name = unicode(node_name) # in case it is a QString
        self.current_node_name = node_name
        self.current_process = process
        if node_name in ('inputs', 'outputs'):
            node_name = ''
        node = self.scene.pipeline.nodes[node_name]
        controller_action = QtGui.QAction('open node controller', menu)
        controller_action.triggered.connect(self.openProcessController)
        menu.addAction(controller_action)

        disable_action = QtGui.QAction('Enable/disable node', menu)
        disable_action.setCheckable(True)
        disable_action.setChecked(node.enabled)
        disable_action.toggled.connect(self.enableNode)

        #disable_down_action = menu.addAction('Disable for downhill processing')
        #disable_down_action.triggered.connect(self.disable_downhill)

        #disable_up_action = menu.addAction('Disable for uphill processing')
        #disable_up_action.triggered.connect(self.disable_uphill)

        #disable_done_action = menu.addAction('Disable nodes with existing outputs')
        #disable_done_action.triggered.connect(self.disable_done_outputs)

        #reactivate_pipeline_action = menu.addAction('Reactivate disabed pipeline nodes')
        #reactivate_pipeline_action.triggered.connect(self.reactivate_pipeline)

        #reactivate_node_action = menu.addAction('Reactivate disabed pipeline node')
        #reactivate_node_action.triggered.connect(self.reactivate_node)

        steps = getattr(self.scene.pipeline, 'pipeline_steps', None)
        if steps is not None:
            my_steps = [step_name for step_name in steps.user_traits()
                        if node.name in steps.trait(step_name).nodes]
            for step in my_steps:
                step_action = menu.addAction('(enable) step: %s' % step)
                step_action.setCheckable(True)
                step_state = getattr(self.scene.pipeline.pipeline_steps, step)
                step_action.setChecked(step_state)
                step_action.toggled.connect(SomaPartial(self.enable_step, step))
            if len(my_steps) != 0:
                step = my_steps[0]
                disable_prec = menu.addAction('Disable preceding steps')
                disable_prec.triggered.connect(SomaPartial(
                    self.disable_preceding_steps, step))
                enable_prec = menu.addAction('Enable preceding steps')
                enable_prec.triggered.connect(SomaPartial(
                    self.enable_preceding_steps, step))
                step = my_steps[-1]
                disable_foll = menu.addAction('Disable following steps')
                disable_foll.triggered.connect(SomaPartial(
                    self.disable_following_steps, step))
                enable_foll = menu.addAction('Enable following steps')
                enable_foll.triggered.connect(SomaPartial(
                    self.enable_following_steps, step))

        menu.addAction(disable_action)
        menu.exec_(QtGui.QCursor.pos())
        del self.current_node_name
        del self.current_process

    def enableNode(self, checked):
        self.scene.pipeline.nodes[self.current_node_name].enabled = checked

    #def disable_downhill(self):
        #pipeline = self.scene.pipeline
        #pipeline_tools.disable_node_for_downhill_pipeline(pipeline, self.current_node_name)

    #def disable_uphill(self):
        #pipeline = self.scene.pipeline
        #pipeline_tools.disable_node_for_uphill_pipeline(pipeline, self.current_node_name)

    #def disable_done_outputs(self):
        #pipeline_tools.disable_nodes_with_existing_outputs(self.scene.pipeline)

    #def reactivate_pipeline(self):
        #pipeline_tools.reactivate_pipeline(self.scene.pipeline)

    #def reactivate_node(self):
        #pipeline_tools.reactivate_node(self.scene.pipeline, self.current_node_name)

    def enable_step(self, step_name, state):
        setattr(self.scene.pipeline.pipeline_steps, step_name, state)

    def disable_preceding_steps(self, step_name, dummy):
        # don't know why we get this additionall dummy parameter (False)
        steps = self.scene.pipeline.pipeline_steps
        for step in steps.user_traits():
            if step == step_name:
                break
            setattr(steps, step, False)

    def disable_following_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        found = False
        for step in steps.user_traits():
            if found:
                setattr(steps, step, False)
            elif step == step_name:
                found = True

    def enable_preceding_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        for step in steps.user_traits():
            if step == step_name:
                break
            setattr(steps, step, True)

    def enable_following_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        found = False
        for step in steps.user_traits():
            if found:
                setattr(steps, step, True)
            elif step == step_name:
                found = True

