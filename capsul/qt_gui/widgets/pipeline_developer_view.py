"""
A Pipeline structure viewer widget, which displays pipeline nodes as boxes and links as lines, and provides pipeline editor features.

The only main class you should look at is the :class:`PipelineDeveloperView` widget, the remaining is internal infrastructure::

    pv = PipelineDeveloperView(pipeline, allow_open_controller=True,
                                enable_edition=True,show_sub_pipelines=True)
    pv.show()

Classes
=======
:class:`ColorType`
------------------
:class:`Plug`
-------------
:class:`EmbeddedSubPipelineItem`
--------------------------------
:class:`boxItem`
----------------
:class:`NodeGWidget`
--------------------
:class:`HandleItem`
-------------------
:class:`Link`
-------------
:class:`PipelineScene`
----------------------
:class:`PipelineDeveloperView`
-------------------------------

"""

# System import
import dataclasses
import distutils.spawn
import html
import importlib
import inspect
import json
import os
import sys
import tempfile
import traceback
import weakref
from pprint import pprint

import soma.subprocess

# Capsul import
from soma.qt_gui import qt_backend

qt_backend.set_qt_backend(compatible_qt5=True)

from soma import controller as sc
from soma.controller import Controller, undefined
from soma.qt_gui.controller import ControllerWidget
from soma.qt_gui.qt_backend import Qt, QtCore, QtGui
from soma.qt_gui.qt_backend.Qt import QGraphicsView, QMessageBox
from soma.sorted_dictionary import SortedDictionary
from soma.utils.functiontools import SomaPartial
from soma.utils.weak_proxy import get_ref, proxy_method

from capsul.api import Capsul, Pipeline, Process, Switch, executable
from capsul.application import get_node_class, is_executable
from capsul.pipeline import pipeline_tools
from capsul.pipeline.pipeline import CustomPipeline
from capsul.pipeline.pipeline_nodes import Node
from capsul.pipeline.process_iteration import ProcessIteration
from capsul.qt_gui.widgets.attributed_process_widget import AttributedProcessWidget
from capsul.qt_gui.widgets.pipeline_file_warning_widget import PipelineFileWarningWidget

# -----------------------------------------------------------------------------
# Globals and constants
# -----------------------------------------------------------------------------

GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 0.1)
GRAY_2 = QtGui.QColor.fromRgbF(0.4, 0.4, 0.4, 1)
LIGHT_GRAY_1 = QtGui.QColor.fromRgbF(0.2, 0.2, 0.2, 1)
LIGHT_GRAY_2 = QtGui.QColor.fromRgbF(0.2, 0.2, 0.2, 1)

# Colors for links and plugs

ORANGE_1 = QtGui.QColor.fromRgb(220, 80, 20)
ORANGE_2 = QtGui.QColor.fromRgb(220, 120, 20)
BLUE_1 = QtGui.QColor.fromRgb(50, 150, 250)
BLUE_2 = QtGui.QColor.fromRgb(50, 50, 250)
PURPLE_2 = QtGui.QColor.fromRgb(200, 0, 200)
RED_2 = QtGui.QColor.fromRgb(200, 0, 0)
GREEN_2 = QtGui.QColor.fromRgb(0, 100, 0)
BLACK_2 = QtGui.QColor.fromRgb(10, 10, 10)
WHITE_2 = QtGui.QColor.fromRgb(255, 255, 255)

ANTHRACITE_1 = QtGui.QColor.fromRgbF(0.05, 0.05, 0.05)
LIGHT_ANTHRACITE_1 = QtGui.QColor.fromRgbF(0.25, 0.25, 0.25)


# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------


class ColorType:
    def __init__(self):
        pass

    def colorLink(self, x):
        if not isinstance(x, str):
            # x is a field
            field_type_str = x.type_str(x)
            if field_type_str in ("file", "directory", "path") and x.metadata.get(
                "write", False
            ):
                field_type_str = "%s_out" % field_type_str
            x = field_type_str
        return {
            "str": PURPLE_2,
            "float": ORANGE_1,
            "int": BLUE_2,
            "list": RED_2,
            "file": ORANGE_2,
            "directory": ORANGE_2,
            "path": ORANGE_2,
            "file_out": GREEN_2,
            "directory_out": GREEN_2,
            "path_out": GREEN_2,
        }.get(x, PURPLE_2)


class Plug(Qt.QGraphicsPolygonItem):
    def __init__(
        self, color, name, height, width, activated=True, optional=False, parent=None
    ):
        super().__init__(parent)
        self.name = name
        #         self.color = self._color(activated, optional)
        self.color = color
        if optional:
            brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
            brush.setColor(self.color)
            polygon = QtGui.QPolygonF(
                [
                    QtCore.QPointF(0, 0),
                    QtCore.QPointF(width / 1.5, 0),
                    QtCore.QPointF(width / 1.5, (height - 5)),
                    QtCore.QPointF(0, (height - 5)),
                ]
            )
        #             self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        else:
            brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
            brush.setColor(self.color)
            polygon = QtGui.QPolygonF(
                [
                    QtCore.QPointF(0, 0),
                    QtCore.QPointF(width, (height - 5) / 2.0),
                    QtCore.QPointF(0, height - 5),
                ]
            )
        self.setPolygon(polygon)
        self.setBrush(brush)
        self.setZValue(3)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

    #     def _color(self, activated, optional):
    #         if optional:
    #             if activated:
    #                 color = QtCore.Qt.darkGreen
    #             else:
    #                 color = QtGui.QColor('#BFDB91')
    #         else:
    #             if activated:
    #                 color = QtCore.Qt.black
    #             else:
    #                 color = QtCore.Qt.gray
    #         return color

    #     def update_plug(self, activated, optional):
    #         color = self._color(activated, optional)
    #         brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
    #         brush.setColor(color)
    #         self.setBrush(brush)

    def update_plug(self, color):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        brush.setColor(color)
        self.setBrush(brush)

    def get_plug_point(self):
        point = QtCore.QPointF(
            self.boundingRect().size().width() / 2.0,
            self.boundingRect().size().height() / 2.0,
        )
        return self.mapToParent(point)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.scene().plug_clicked.emit(self.name)
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            # print('plug: right click')
            self.scene().plug_right_clicked.emit(self.name)
            event.accept()


class EmbeddedSubPipelineItem(Qt.QGraphicsProxyWidget):
    """
    QGraphicsItem containing a sub-pipeline view
    """

    def __init__(self, sub_pipeline_wid):
        super().__init__()
        old_height = sub_pipeline_wid.sizeHint().height()
        sizegrip = QtGui.QSizeGrip(None)
        new_height = old_height + sub_pipeline_wid.horizontalScrollBar().height()
        sub_pipeline_wid.setCornerWidget(sizegrip)
        sub_pipeline_wid.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        sub_pipeline_wid.resize(sub_pipeline_wid.sizeHint().width(), new_height)
        self.setWidget(sub_pipeline_wid)


class boxItem(QtGui.QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        #         self.setFlags(self.ItemIsFocusable)
        self.penBox = 0
        self.name = ""

    def focusInEvent(self, event):
        self.setPen(QtGui.QPen(QtGui.QColor(150, 150, 250), 3, QtCore.Qt.DashDotLine))
        return QtGui.QGraphicsRectItem.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.setPen(self.penBox)
        return QtGui.QGraphicsRectItem.focusOutEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.scene()._node_keydelete_clicked(self)
            event.accept()
        else:
            super().keyPressEvent(event)


class NodeGWidget(QtGui.QGraphicsItem):
    def __init__(
        self,
        name,
        parameters,
        pipeline,
        parent=None,
        process=None,
        sub_pipeline=None,
        colored_parameters=True,
        logical_view=False,
        labels=None,
        show_opt_inputs=True,
        show_opt_outputs=True,
        userlevel=0,
    ):
        super().__init__(parent)

        self.infoActived = QtGui.QGraphicsTextItem("", self)
        self.colType = ColorType()
        self._userlevel = userlevel

        self.setFlags(self.ItemIsSelectable)
        self.setCursor(Qt.QCursor(QtCore.Qt.PointingHandCursor))

        self.style = "default"
        self.name = name
        # print('GNode userlevel:', self.userlevel)
        # print([(pname, param) for pname, param in parameters.items()
        # if not getattr(param, 'hidden', False)
        # and (getattr(param, 'userlevel', None) is None
        # or param.userlevel <= self.userlevel)]
        controller = process
        self.parameters = SortedDictionary()
        for pname, param in parameters.items():
            show = True
            if controller:
                field = controller.field(pname)
                if getattr(field, "hidden", False):
                    show = False
                elif getattr(field, "userlevel", None) is not None:
                    if field.userlevel > self.userlevel:
                        show = False
            if show:
                self.parameters[pname] = param

        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.in_plugs = SortedDictionary()
        self.in_params = {}
        self.out_plugs = SortedDictionary()
        self.out_params = {}
        self.process = process
        self.sub_pipeline = sub_pipeline
        self.embedded_subpipeline = None
        self.colored_parameters = colored_parameters
        self.logical_view = logical_view
        self.pipeline = pipeline

        # Added to choose to visualize optional parameters
        self.show_opt_inputs = show_opt_inputs
        self.show_opt_outputs = show_opt_outputs

        self.labels = []
        self.scene_labels = labels or []
        self.label_items = []
        my_labels = []
        steps = getattr(pipeline, "pipeline_steps", None)
        if steps:
            for step in steps.fields():
                step_name = step.name
                step_nodes = step.nodes
                if name in step_nodes:
                    my_labels.append("step: %s" % step_name)
        selects = pipeline.get_processes_selections()
        for sel_plug in selects:
            groups = pipeline.get_processes_selection_groups(sel_plug)
            for group, nodes in groups.items():
                if name in nodes:
                    my_labels.append("select: %s" % sel_plug)

        for label in my_labels:
            self._get_label(label)

        self._set_brush()
        self.setAcceptedMouseButtons(
            QtCore.Qt.LeftButton | QtCore.Qt.RightButton | QtCore.Qt.MiddleButton
        )

        self._build()

        self._update_param_timer = Qt.QTimer()
        self._update_param_timer.setSingleShot(True)
        self._update_param_timer.timeout.connect(
            proxy_method(self, "update_parameters_now")
        )

        if colored_parameters:
            process.on_attribute_change.add(self._repaint_parameter)
        process.on_fields_change.add(self.update_parameters)

    def __del__(self):
        # print('NodeGWidget.__del__')
        self._release()
        # super().__del__()

    @property
    def userlevel(self):
        return self._userlevel

    @userlevel.setter
    def userlevel(self, value):
        self._userlevel = value
        self.update_parameters()

    def _release(self):
        # release internal connections / callbacks / references in order to
        # allow deletion of self
        self.process.on_fields_change.remove(self.update_parameters)
        if self.colored_parameters:
            try:
                self.process.on_attribute_change.remove(self._repaint_parameter)
            except Exception:
                pass
            self.colored_parameters = None
        self.sizer = None

    def get_title(self):
        if self.sub_pipeline is None:
            return self.name
        else:
            return f"[{self.name}]"

    def update_parameters(self):
        self._update_param_timer.start(20)

    def update_parameters_now(self):
        forbidden = ["nodes_activation", "activated", "enabled", "name", "node_type"]

        controller = self.process
        self.parameters = SortedDictionary()
        for param in self.process.fields():
            pname = param.name
            show = True
            if self.name == "inputs" and param.is_output():
                continue
            elif self.name == "outputs" and not param.is_output():
                continue
            if getattr(param, "hidden", False):
                show = False
            elif getattr(param, "userlevel", None) is not None:
                if param.userlevel > self.userlevel:
                    show = False
            if show:
                self.parameters[pname] = self.process.plugs[pname]

        self.update_node()

    def update_labels(self, labels):
        """Update colored labels"""
        self.labels = []
        for item in self.label_items:
            item.deleteLater()  # FIXME there should be another way !
        self.label_items = []
        for label in labels:
            self._get_label(label)
        self._create_label_marks()

    def _get_label(self, label, register=True):
        class Label:
            def __init__(self, label, color):
                self.text = label
                self.color = color

        for l in self.scene_labels:
            if label == l.text:
                if register and l not in self.labels:
                    self.labels.append(l)
                return l
        color = self.new_color(len(self.scene_labels))
        label_item = Label(label, color)
        if register:
            self.labels.append(label_item)
        self.scene_labels.append(label_item)
        return label_item

    def new_color(self, num):
        colors = [
            [1, 0.3, 0.3],
            [0.3, 1, 0.3],
            [0.3, 0.3, 1],
            [1, 1, 0],
            [0, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
            [1, 0.7, 0],
            [1, 0, 0.7],
            [1, 0.7, 0.7],
            [0.7, 1, 0],
            [0.0, 1.0, 0.7],
            [0.7, 1, 0.7],
            [0.7, 0, 1],
            [0.0, 0.7, 1],
            [0.7, 0.7, 1],
            [1, 1, 0.5],
            [0.5, 1, 1],
            [1, 0.5, 1],
        ]
        c = colors[num % len(colors)]
        code = (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
        return code

    def _repaint_parameter(self, new_value, old_value, param_name):
        if self.logical_view or param_name not in self.parameters:
            return
        param_text = self._parameter_text(param_name)
        param_item = self.in_params.get(param_name)
        if param_item is None:
            param_item = self.out_params[param_name]
        if isinstance(param_item, QtGui.QGraphicsProxyWidget):
            # colored parameters are widgets
            param_item.widget().findChild(QtGui.QLabel, "label").setText(param_text)
        else:
            param_item.setHtml(param_text)

    def _build(self):
        margin = 0
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        #         font = self.title.font()
        font = QtGui.QFont("Times", 11, QtGui.QFont.Bold)
        #         font.setWeight(QtGui.QFont.Bold)
        self.title.setFont(font)
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        self.title.setDefaultTextColor(QtCore.Qt.white)
        self.title.setParentItem(self)

        if self.logical_view:
            self._build_logical_view_plugs()
        else:
            self._build_regular_view_plugs()
        self._create_label_marks()

        ctr = self.contentsRect()
        self.wmin = ctr.width()
        self.hmin = ctr.height()

        font1 = QtGui.QFont("Times", 12, QtGui.QFont.Normal)
        font1.setItalic(True)
        self.infoActived.setFont(font1)
        self.infoActived.setZValue(2)
        self.infoActived.setDefaultTextColor(QtCore.Qt.red)
        self.infoActived.setParentItem(self)

        self.box = boxItem(self)
        self.box.setFlags(self.box.ItemIsFocusable)
        self.box.setBrush(self.bg_brush)
        self.box.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box.setZValue(-1)
        self.box.penBox = self.box.pen()
        self.box.name = self.name
        self.box.setParentItem(self)

        self.sizer = HandleItem(self)
        self.sizer.wmin = self.wmin
        self.sizer.hmin = self.hmin
        self.sizer.setPos(ctr.width(), ctr.height())
        self.sizer.posChangeCallbacks.append(proxy_method(self, "changeSize"))
        self.sizer.setFlag(self.sizer.ItemIsSelectable, True)

        self.box_title = QtGui.QGraphicsRectItem(self)
        self.box_title.setBrush(self.title_brush)
        self.box_title.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.box_title.setZValue(1)
        self.box_title.setParentItem(self)

        self.changeSize(ctr.width(), ctr.height())

    def changeSize(self, w, h):
        limit = False
        factor_h = 35

        if h < self.hmin:
            h = self.hmin
            limit = True

        if w < self.wmin:
            w = self.wmin
            limit = True

        winMax, woutMax = 0, 0

        self.box.setRect(0.0, 0.0, w, h)

        self.box_title.setRect(0.0, 0.0, w, 30)
        self.title.setPos(w / 2 - self.title.boundingRect().size().width() / 2, 0)
        self.infoActived.setPos(
            w / 2 - self.infoActived.boundingRect().size().width() / 2, h + 2
        )

        #         rect = self.title.mapRectToParent(self.title.boundingRect())
        #         rect.setWidth(w)
        #         self.box_title.setRect(rect)

        y1 = h / (len(self.in_plugs) + 1)
        dy = y1
        for inp in self.in_plugs:
            self.in_plugs[inp].setPos(0, y1)
            self.in_params[inp].setPos(
                self.in_plugs[inp].boundingRect().size().width(), y1
            )
            if winMax < self.in_params[inp].boundingRect().size().width():
                winMax = self.in_params[inp].boundingRect().size().width()
            y1 += dy

        y2 = h / (len(self.out_plugs) + 1)
        dy = y2
        for outp in self.out_plugs:
            self.out_plugs[outp].setPos(w, y2)
            self.out_params[outp].setPos(
                w - self.out_params[outp].boundingRect().size().width() - 5, y2
            )
            if woutMax < self.out_params[outp].boundingRect().size().width():
                woutMax = self.out_params[outp].boundingRect().size().width()
            y2 += dy

        if w < winMax + woutMax + 15:
            w = winMax + woutMax + 15
            self.updateSize(w, h)
            # self.sizer.setPos(w, h)
            self.wmin = w

        if limit:
            self.sizer.setPos(w, h)

        self.update_labels([l.text for l in self.labels])

        # if self.hmin < factor_h * len(self.in_plugs):
        #     self.hmin = factor_h * len(self.in_plugs)
        #     self.updateSize(w, self.hmin)
        # if self.hmin < factor_h * len(self.out_plugs):
        #     self.hmin = factor_h * len(self.out_plugs)
        #     self.updateSize(w, self.hmin)

    def updateSize(self, w, h):
        # print("wmin =",self.wmin,", w=",w)
        if w < self.wmin:
            w = self.wmin
        margin = 20
        factor_h = 35.0
        h = factor_h * len(self.in_plugs) + margin
        self.hmin = h

        if h < factor_h * len(self.out_plugs):
            h = factor_h * len(self.out_plugs) + margin
            self.hmin = h
        self.sizer.hmin = h
        self.changeSize(w, h + margin)
        self.sizer.setPos(w, h + margin)

    def _colored_text_item(self, label, text=None, margin=2):
        labelc = self._get_label(label, False)
        color = labelc.color
        if text is None:
            text = label
        # I can't make rounded borders with appropriate padding
        # without using 2 QLabels. This is probably overkill. We could
        # replace this code of we find a simpler way.
        label_w = QtGui.QLabel("")
        label_w.setStyleSheet("background: rgba(255, 255, 255, 0);")
        lay = QtGui.QVBoxLayout()
        lay.setContentsMargins(margin, margin, margin, margin)
        label_w.setLayout(lay)
        label2 = QtGui.QLabel(text)
        label2.setObjectName("label")
        label2.setStyleSheet(
            "background: rgba({}, {}, {}, 255); "
            "border-radius: 7px; border: 0px solid; "
            "padding: 1px;".format(*color)
        )
        lay.addWidget(label2)
        label_item = QtGui.QGraphicsProxyWidget(self)
        label_item.setWidget(label_w)
        return label_item

    def _build_regular_view_plugs(self):
        margin = 5
        plug_width = 12
        pos = margin + margin + self.title.boundingRect().size().height()
        pos0 = pos
        if self.name == "inputs":
            selections = self.pipeline.get_processes_selections()
        else:
            selections = []

        for in_param, pipeline_plug in self.parameters.items():
            output = (
                not pipeline_plug.output
                if self.name in ("inputs", "outputs")
                else pipeline_plug.output
            )
            if output or (not self.show_opt_inputs and pipeline_plug.optional):
                continue
            param_text = self._parameter_text(in_param)
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml(param_text)

            plug_name = "%s:%s" % (self.name, in_param)

            try:
                #                 color = self.colorLink(field)
                color = self.colType.colorLink(self.process.field(in_param))
            except Exception:
                color = ORANGE_2

            plug = Plug(
                color,
                plug_name,
                param_name.boundingRect().size().height(),
                plug_width,
                activated=pipeline_plug.activated,
                optional=pipeline_plug.optional,
                parent=self,
            )
            param_name.setZValue(2)
            plug.setPos(margin, pos)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.in_plugs[in_param] = plug
            self.in_params[in_param] = param_name
            pos = pos + param_name.boundingRect().size().height()

        pos = pos0
        for out_param, pipeline_plug in self.parameters.items():
            output = (
                not pipeline_plug.output
                if self.name in ("inputs", "outputs")
                else pipeline_plug.output
            )
            if not output or (not self.show_opt_outputs and pipeline_plug.optional):
                continue
            param_text = self._parameter_text(out_param)
            if out_param in selections:
                param_name = self._colored_text_item(
                    "select: " + out_param, param_text, 0
                )
            else:
                param_name = QtGui.QGraphicsTextItem(self)
                param_name.setHtml(param_text)

            plug_name = "%s:%s" % (self.name, out_param)

            try:
                #                 color = self.colorLink(field_type_str)
                color = self.colType.colorLink(self.process.field(out_param))

            except Exception:
                color = ORANGE_2

            plug = Plug(
                color,
                plug_name,
                param_name.boundingRect().size().height(),
                plug_width,
                activated=pipeline_plug.activated,
                optional=pipeline_plug.optional,
                parent=self,
            )
            param_name.setZValue(2)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            plug.setPos(
                plug.boundingRect().size().width()
                + margin
                + param_name.boundingRect().size().width()
                + margin,
                pos,
            )
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.out_plugs[out_param] = plug
            self.out_params[out_param] = param_name
            pos = pos + param_name.boundingRect().size().height()

    def change_input_view(self):
        self.show_opt_inputs = not self.show_opt_inputs

    def change_output_view(self):
        self.show_opt_outputs = not self.show_opt_outputs

    def _build_logical_view_plugs(self):
        margin = 5
        plug_width = 12
        pos = margin + margin + self.title.boundingRect().size().height()

        has_input = False
        has_output = False

        for in_param, pipeline_plug in self.parameters.items():
            output = (
                not pipeline_plug.output
                if self.name in ("inputs", "outputs")
                else pipeline_plug.output
            )
            if output:
                has_output = True
            else:
                has_input = True
            if has_input and has_output:
                break

        if has_input:
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml("")
            plug_name = "%s:inputs" % self.name

            color = QtCore.Qt.black

            plug = Plug(
                color,
                plug_name,
                param_name.boundingRect().size().height(),
                plug_width,
                activated=True,
                optional=False,
                parent=self,
            )
            param_name.setZValue(2)
            plug.setPos(margin, pos)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.in_plugs["inputs"] = plug
            self.in_params["inputs"] = param_name

        if has_output:
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml("")
            plug_name = "%s:outputs" % self.name

            color = QtCore.Qt.black

            plug = Plug(
                color,
                plug_name,
                param_name.boundingRect().size().height(),
                plug_width,
                activated=True,
                optional=False,
                parent=self,
            )
            param_name.setZValue(2)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            plug.setPos(
                self.title.boundingRect().width() - plug.boundingRect().width(), pos
            )
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.out_plugs["outputs"] = plug
            self.out_params["outputs"] = param_name

    def _create_label_marks(self):
        labels = self.labels
        if labels:
            margin = 5
            plug_width = 12
            xpos = margin + plug_width
            ypos = None
            params = dict(self.in_params)
            params.update(self.out_params)
            child = None
            for param in params.values():
                y = self.mapRectFromItem(param, param.boundingRect()).bottom()
                if ypos is None or ypos < y:
                    ypos = y
                    child = param
            # if ypos is None:
            # ypos = margin * 2 + self.title.boundingRect().size().height()
            if child is None:
                child = self.childItems()[-1]
                item_rect = self.mapRectFromItem(child, child.boundingRect())
                ypos = item_rect.bottom()
            for label in labels:
                color = label.color
                text = label.text
                label_item = self._colored_text_item(label.text, label.text)
                label_item.setPos(xpos, ypos)
                label_item.setParentItem(self)
                self.label_items.append(label_item)
                ypos = self.mapRectFromItem(
                    label_item, label_item.boundingRect()
                ).bottom()

    def clear_plugs(self):
        for plugs, params in (
            (self.in_plugs, self.in_params),
            (self.out_plugs, self.out_params),
        ):
            for plug_name, plug in plugs.items():
                param_item = params[plug_name]
                self.scene().removeItem(param_item)
                self.scene().removeItem(plug)
        self.in_params = {}
        self.in_plugs = {}
        self.out_params = {}
        self.out_plugs = {}

    def updateInfoActived(self, state):
        if state:
            self.infoActived.setPlainText("")
        else:
            self.infoActived.setPlainText("disabled")

    def fonced_viewer(self, det):
        if det:
            #             color=QtGui.QColor(150, 150, 250)
            self.setOpacity(0.2)
        else:
            #             color=self.color
            self.setOpacity(1)

    #         self._set_pen(self.active, self.weak, color)

    def _set_brush(self):
        pipeline = self.pipeline
        if self.name in ("inputs", "outputs"):
            node = pipeline
        else:
            node = pipeline.nodes[self.name]
        color_1, color_2, color_3, style = pipeline_tools.pipeline_node_colors(
            pipeline, node
        )
        self.style = style
        color_1 = QtGui.QColor.fromRgbF(*color_1)
        color_2 = QtGui.QColor.fromRgbF(*color_2)
        #         color_1 = ANTHRACITE_1
        #         color_2 = LIGHT_ANTHRACITE_1
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, color_1)
        gradient.setColorAt(1, color_2)
        self.bg_brush = QtGui.QBrush(gradient)

        if node.activated:
            #             color_1 = GRAY_1
            #             color_2 = GRAY_2
            self.updateInfoActived(True)

        else:
            #             color_1 = LIGHT_GRAY_1
            #             color_2 = LIGHT_GRAY_2
            self.updateInfoActived(False)

        if node in pipeline.disabled_pipeline_steps_nodes():
            color_1 = self._color_disabled(color_1)
            color_2 = self._color_disabled(color_2)

        gradient = QtGui.QLinearGradient(0, 2, 5, 100)
        gradient.setColorAt(1, GRAY_1)
        gradient.setColorAt(0, GRAY_2)
        self.title_brush = QtGui.QBrush(LIGHT_GRAY_2)

    def _color_disabled(self, color):
        target = [220, 240, 220]
        new_color = QtGui.QColor(
            (color.red() + target[0]) / 2,
            (color.green() + target[1]) / 2,
            (color.blue() + target[2]) / 2,
        )
        return new_color

    def _create_parameter(self, param_name, pipeline_plug):
        plug_width = 12
        margin = 5
        output = (
            not pipeline_plug.output
            if self.name in ("inputs", "outputs")
            else pipeline_plug.output
        )
        if self.logical_view:
            if output:
                param_name = "outputs"
            else:
                param_name = "inputs"
        param_text = self._parameter_text(param_name)
        if (
            self.name == "inputs"
            and not self.logical_view
            and "select: " + param_name in [l.text for l in self.scene_labels]
        ):
            param_name_item = self._colored_text_item(
                "select: " + param_name, param_text, 0
            )
        else:
            param_name_item = QtGui.QGraphicsTextItem(self)
            param_name_item.setHtml(param_text)
        plug_name = "%s:%s" % (self.name, param_name)

        color = QtCore.Qt.black

        plug = Plug(
            color,
            plug_name,
            param_name_item.boundingRect().size().height(),
            plug_width,
            activated=pipeline_plug.activated,
            optional=pipeline_plug.optional,
            parent=self,
        )
        param_name_item.setZValue(2)
        if output:
            plugs = self.out_plugs
            params = self.out_params
            params_size = len(params) + len(self.in_params)
            # FIXME: sub-pipeline size
            xpos = plug.boundingRect().size().width() + margin
            pxpos = (
                plug.boundingRect().size().width()
                + margin * 2
                + param_name_item.boundingRect().size().width()
            )
        else:
            plugs = self.in_plugs
            params = self.in_params
            params_size = len(params)
            xpos = plug.boundingRect().size().width() + margin
            pxpos = margin
        if self.logical_view:
            params_size = 0
            if output:
                pxpos = self.title.boundingRect().width() - plug.boundingRect().width()
        pos = (
            margin * 2
            + self.title.boundingRect().size().height()
            + param_name_item.boundingRect().size().height() * params_size
        )
        param_name_item.setPos(xpos, pos)
        plug.setPos(pxpos, pos)
        param_name_item.setParentItem(self)
        plug.setParentItem(self)
        plugs[param_name] = plug
        params[param_name] = param_name_item
        if output:
            self._shift_params()

        self.updateSize(
            self.box.boundingRect().size().width(),
            self.box.boundingRect().size().height(),
        )
        self.sizer.setPos(
            self.box.boundingRect().size().width(),
            self.box.boundingRect().size().height(),
        )

    #         self.hmin=self.box.boundingRect().size().height()

    def _shift_params(self):
        margin = 5
        if not self.in_params:
            if not self.out_params:
                param_item = None
            else:
                param_item = list(self.out_params.values())[0]
        else:
            param_item = list(self.in_params.values())[0]
        ni = 0
        no = 0
        bottom_pos = 0
        if param_item:
            for param_name, pipeline_plug in self.parameters.items():
                output = (
                    not pipeline_plug.output
                    if self.name in ("inputs", "outputs")
                    else pipeline_plug.output
                )
                if output:
                    # Added to choose to visualize optional parameters
                    if not pipeline_plug.optional or (
                        self.show_opt_outputs and pipeline_plug.optional
                    ):
                        params = self.out_params
                        plugs = self.out_plugs
                        npos = no + len(self.in_params)
                        no += 1
                    else:
                        continue
                else:
                    # Added to choose to visualize optional parameters
                    if not pipeline_plug.optional or (
                        self.show_opt_inputs and pipeline_plug.optional
                    ):
                        params = self.in_params
                        plugs = self.in_plugs
                        npos = ni
                        ni += 1
                    else:
                        continue
                pos = (
                    margin * 2
                    + self.title.boundingRect().size().height()
                    + param_item.boundingRect().size().height() * npos
                )
                new_param_item = params.get(param_name)
                if new_param_item is None:
                    continue
                param_item = new_param_item
                plug = plugs[param_name]
                ppos = param_item.pos()
                param_item.setPos(ppos.x(), pos)
                ppos = plug.pos()
                plug.setPos(ppos.x(), pos)
                pos += param_item.boundingRect().size().height()
                bottom_pos = max(pos, bottom_pos)
            if self.logical_view:
                nparams = 1
            else:
                nparams = len(self.in_params) + len(self.out_params)
            pos = (
                margin * 2
                + self.title.boundingRect().size().height()
                + param_item.boundingRect().size().height() * nparams
            )
        else:
            pos = margin * 2 + self.title.boundingRect().size().height()
        for label_item in self.label_items:
            ppos = label_item.pos()
            label_item.setPos(ppos.x(), pos)
            pos += label_item.boundingRect().size().height()

    def _remove_parameter(self, param_name):
        if param_name in self.in_params:
            params = self.in_params
            plugs = self.in_plugs
        else:
            params = self.out_params
            plugs = self.out_plugs
        param_item = params[param_name]
        if self.scene():
            self.scene().removeItem(param_item)
        plug = plugs[param_name]
        if self.scene():
            self.scene().removeItem(plug)
        del params[param_name]
        del plugs[param_name]
        self._shift_params()

    def _parameter_text(self, param_name):
        if self.logical_view:
            return ""
        pipeline_plug = self.parameters[param_name]
        # output = (not pipeline_plug.output if self.name in (
        # 'inputs', 'outputs') else pipeline_plug.output)
        output = pipeline_plug.output
        if output:
            param_text = '<font color="#400000"><b>%s</b></font>' % param_name
        else:
            param_text = '<font color="#111111"><b>%s</b></font>' % param_name
        value = getattr(self.process, param_name, undefined)
        if value in (None, undefined, ""):
            param_text = "<em>%s</em>" % param_text
        else:
            field = self.process.field(param_name)
            if field.is_path() and os.path.exists(value):
                param_text = "<b>%s</b>" % param_text
        return param_text

    def update_node(self):
        # this is needed before the box is resized, otherwise some bad things
        # may happen, especially segfaults...
        self.prepareGeometryChange()
        self._set_brush()
        self.box_title.setBrush(self.title_brush)
        self.box.setBrush(self.bg_brush)
        for param, pipeline_plug in self.parameters.items():
            output = (
                not pipeline_plug.output
                if self.name in ("inputs", "outputs")
                else pipeline_plug.output
            )
            if output:
                plugs = self.out_plugs
                params = self.out_params
                if self.logical_view:
                    param = "outputs"
            else:
                plugs = self.in_plugs
                params = self.in_params
                if self.logical_view:
                    param = "inputs"
            gplug = plugs.get(param)
            if gplug is None:  # new parameter ?
                self._create_parameter(param, pipeline_plug)
                gplug = plugs.get(param)
            if not self.logical_view:
                #                 gplug.update_plug(pipeline_plug.activated,
                #                                   pipeline_plug.optional)

                try:
                    #                     color = self.colorLink(field)
                    color = self.colType.colorLink(self.process.field(param))

                except Exception:
                    color = ORANGE_2

                gplug.update_plug(color)

                if isinstance(params[param], QtGui.QGraphicsProxyWidget):
                    # colored parameters are widgets
                    params[param].widget().findChild(QtGui.QLabel, "label").setText(
                        self._parameter_text(param)
                    )
                else:
                    params[param].setHtml(self._parameter_text(param))

        if not self.logical_view:
            # check removed params
            to_remove = []

            # Added to choose to visualize optional parameters
            for param, pipeline_plug in self.parameters.items():
                output = (
                    not pipeline_plug.output
                    if self.name in ("inputs", "outputs")
                    else pipeline_plug.output
                )
                if output:
                    if pipeline_plug.optional and not self.show_opt_outputs:
                        to_remove.append(param)
                else:
                    if pipeline_plug.optional and not self.show_opt_inputs:
                        to_remove.append(param)

            for param in self.in_params:
                if param not in self.parameters:
                    to_remove.append(param)
            for param in self.out_params:
                if param not in self.parameters:
                    to_remove.append(param)
            for param in to_remove:
                self._remove_parameter(param)

        self._shift_params()

        #         rect = self.title.mapRectToParent(self.title.boundingRect())
        #         margin = 5
        #         brect = self.boundingRect()
        #         brect.setWidth(brect.right() - margin)
        #         rect.setWidth(brect.width())
        #         self.box_title.setRect(rect)
        #         self.box.setRect(self.boundingRect())

        ################a dd by Irmage OM #############################################
        try:
            dim = self.scene().dim.get(self.box.name)
            if isinstance(dim, Qt.QPointF):
                dim = (dim.x(), dim.y())

            self.updateSize(dim[0], dim[1])
        #             self.scene().dim[self.box.name] = (dim[0],dim[1])
        #             print("update_node : self.scene().dim ",dim)

        except Exception:
            dim = (
                self.box.boundingRect().size().width(),
                self.box.boundingRect().size().height(),
            )
            self.updateSize(dim[0], dim[1])

    #             self.scene().dim[self.box.name] = (dim[0],dim[1])
    #             print("update_node : boundingRect()")
    ##############################################################################

    def contentsRect(self):
        brect = QtCore.QRectF(0, 0, 0, 0)
        first = True
        excluded = []
        for name in ("box", "box_title"):
            if hasattr(self, name):
                excluded.append(getattr(self, name))
        for child in self.childItems():
            if not hasattr(child, "isVisible"):
                # we sometimes get some QObject here, I don't know who they are
                continue
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
        painter.setFont(QtGui.QFont("Arial", 30))
        painter.drawText(0, 0, "Ca marche !")
        # render(&painter,QRectF(QPointF(0,0),10*contentRect.size()),contentRect);
        painter.end()

    def resize_subpipeline_on_show(self):
        margin = 5
        param_width = self.in_params_width()
        pos = margin * 2 + self.title.boundingRect().size().height()
        opos = (
            param_width + self.embedded_subpipeline.boundingRect().width()
        )  # + margin ?
        for name, param in self.out_params.items():
            param.setPos(opos, param.pos().y())
            plug = self.out_plugs[name]
            plug.setPos(
                opos + margin + param.boundingRect().size().width(), plug.pos().y()
            )
        #         rect = self.box_title.boundingRect()
        rect = self.box.boundingRect()
        rect.setWidth(self.contentsRect().width())
        #         self.box_title.setRect(rect)
        self.box.setRect(self.boundingRect())

    def resize_subpipeline_on_hide(self):
        margin = 5
        for name, param in self.out_params.items():
            plug = self.out_plugs[name]
            param.setPos(plug.boundingRect().width() + margin, param.pos().y())
            plug.setPos(
                plug.boundingRect().size().width()
                + margin
                + param.boundingRect().size().width()
                + margin,
                plug.pos().y(),
            )
        #         rect = self.box_title.boundingRect()
        rect = self.box.boundingRect()
        rect.setWidth(self.contentsRect().width())
        #         self.box_title.setRect(rect)
        self.box.setRect(self.boundingRect())

    def in_params_width(self):
        margin = 5
        width = 0
        pwidth = 0
        for param_name, param in self.in_params.items():
            if param.boundingRect().width() > width:
                width = param.boundingRect().width()
            if pwidth == 0:
                plug = self.in_plugs[param_name]
                pwidth = plug.boundingRect().width()
        return width + margin + pwidth

    def out_params_width(self):
        width = 0
        for param_name, param in self.out_params.items():
            if param.boundingRect().width() > width:
                width = param.boundingRect().width()
        return width

    def add_subpipeline_view(
        self, sub_pipeline, allow_open_controller=True, scale=None
    ):
        if self.embedded_subpipeline:
            if self.embedded_subpipeline.isVisible():
                self.embedded_subpipeline.hide()
                self.resize_subpipeline_on_hide()
            else:
                self.embedded_subpipeline.show()
                self.resize_subpipeline_on_show()
        else:
            sub_view = PipelineDeveloperView(
                sub_pipeline,
                show_sub_pipelines=True,
                allow_open_controller=allow_open_controller,
                enable_edition=self.scene().edition_enabled(),
                userlevel=self.userlevel,
            )
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
            if isinstance(self.sub_pipeline, weakref.ProxyTypes):
                # get the "real" object
                process = self.sub_pipeline.__init__.__self__
            else:
                process = self.sub_pipeline

            self.scene().subpipeline_clicked.emit(
                self.name, process, int(event.modifiers())
            )
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        item = self.scene().itemAt(event.scenePos(), Qt.QTransform())
        # print('NodeGWidget click, item:', item)
        if isinstance(item, Plug):
            item.mousePressEvent(event)
            return
        super().mousePressEvent(event)
        process = get_ref(self.process)
        if event.button() == QtCore.Qt.RightButton and process is not None:
            self.scene().node_right_clicked.emit(self.name, process)
            event.accept()

        if event.button() == QtCore.Qt.LeftButton and process is not None:
            if isinstance(process, Process):
                self.scene().process_clicked.emit(self.name, process)
            else:
                self.scene().node_clicked.emit(self.name, process)

        if (
            event.button() == QtCore.Qt.LeftButton
            and event.modifiers() == QtCore.Qt.ControlModifier
        ):
            self.scene().node_clicked_ctrl.emit(self.name, process)
            self.scene().clearSelection()
            self.box.setSelected(True)
            return QtGui.QGraphicsItem.mousePressEvent(self, event)
            event.accept()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        if event.key() == QtCore.Qt.Key_Up:
            self.setPos(self.x(), self.y() - 1)
        if event.key() == QtCore.Qt.Key_Down:
            self.setPos(self.x(), self.y() + 1)
        if event.key() == QtCore.Qt.Key_Left:
            self.setPos(self.x() - 1, self.y())
        if event.key() == QtCore.Qt.Key_Right:
            self.setPos(self.x() + 1, self.y())

        return QtGui.QGraphicsItem.keyPressEvent(self, event)
        event.accept()


class HandleItem(QtGui.QGraphicsRectItem):
    """A handle that can be moved by the mouse"""

    def __init__(self, parent=None):
        super().__init__(Qt.QRectF(-10.0, -10.0, 10.0, 10.0), parent)
        #         self.setRect(Qt.QRectF(-4.0,-4.0,4.0,4.0))
        self.posChangeCallbacks = []
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.setBrush(QtGui.QBrush(QtCore.Qt.yellow))
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemSendsScenePositionChanges, True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
        self.wmin = 0.0
        self.hmin = 0.0
        self.hmax = 0.0

        self.effectiveOpacity()
        self.setOpacity(0.01)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            self.x, self.y = value.x(), value.y()
            if self.x < self.wmin:
                self.x = self.wmin
            if self.y < self.hmin:
                self.y = self.hmin
            # TODO: make this a signal?
            # This cannot be a signal because this is not a QObject
            for cb in self.posChangeCallbacks:
                res = cb(self.x, self.y)

                if res:
                    self.x, self.y = res
                    if self.x < self.wmin:
                        self.x = self.wmin
                    if self.y < self.hmin:
                        self.y = self.hmin

                    value = QtCore.QPointF(self.x, self.y)
            #                     value = Qt.QPointF(x, y)      #### ??
            self.hmax = value.y()
            return value
        # Call superclass method:

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, mouseEvent):
        self.setSelected(False)
        self.setPos(self.x, self.y)
        return QtGui.QGraphicsRectItem.mouseReleaseEvent(self, mouseEvent)


class Link(QtGui.QGraphicsPathItem):
    def __init__(self, origin, target, active, weak, color, parent=None):
        super().__init__(parent)

        self._set_pen(active, weak, color)

        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(
            origin.x() + 90,
            origin.y(),
            target.x() - 90,
            target.y(),
            target.x() - 5,
            target.y(),
        )
        self.setPath(path)
        self.setZValue(0.5)
        self.active = active
        self.weak = weak
        self.color = color
        self.effectiveOpacity()

    def _set_pen(self, active, weak, color):
        self.pen = QtGui.QPen()
        self.pen.setWidth(3)

        if active:
            self.pen.setBrush(color)
        else:
            self.pen.setBrush(QtCore.Qt.gray)
        if weak:
            self.pen.setStyle(QtCore.Qt.DashLine)
        self.pen.setCapStyle(QtCore.Qt.RoundCap)
        self.pen.setJoinStyle(QtCore.Qt.RoundJoin)
        self.setPen(self.pen)

    def update(self, origin, target):
        path = QtGui.QPainterPath()
        path.moveTo(origin.x(), origin.y())
        path.cubicTo(
            origin.x() + 90,
            origin.y(),
            target.x() - 90,
            target.y(),
            target.x() - 5,
            target.y(),
        )

        self.setPath(path)

    def update_activation(self, active, weak, color):
        if color == "current":
            color = self.color
        self._set_pen(active, weak, color)
        self.active = active
        self.weak = weak

    def fonced_viewer(self, det):
        if det:
            #             color=QtGui.QColor(150, 150, 250)
            self.setOpacity(0.2)
        else:
            #             color=self.color
            self.setOpacity(1)

    #         self._set_pen(self.active, self.weak, color)

    def mousePressEvent(self, event):
        item = self.scene().itemAt(event.scenePos(), Qt.QTransform())
        # print('Link click, item:', item)
        if event.button() == QtCore.Qt.RightButton:
            # not a signal since we don't jhave enough identity information in
            # self: the scene has to help us.
            self.scene()._link_right_clicked(self)
        else:
            super().mousePressEvent(event)
        event.accept()

    def focusInEvent(self, event):
        self.setPen(
            QtGui.QPen(QtGui.QColor(150, 150, 250), 3, QtCore.Qt.DashDotDotLine)
        )
        return QtGui.QGraphicsPathItem.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.setPen(self.pen)
        return QtGui.QGraphicsPathItem.focusOutEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.scene()._link_keydelete_clicked(self)
            event.accept()
        else:
            super().keyPressEvent(event)


class PipelineScene(QtGui.QGraphicsScene):
    # Signal emitted when a sub pipeline has to be open.
    # subpipeline_clicked = QtCore.Signal(str, Process,
    # QtCore.Qt.KeyboardModifiers)
    subpipeline_clicked = QtCore.Signal(str, Process, int)
    # Signal emitted when a node box is clicked
    process_clicked = QtCore.Signal(str, Process)
    node_clicked = QtCore.Signal(str, Node)
    # Signal emitted when a node box is clicked with ctrl
    node_clicked_ctrl = QtCore.Signal(str, Process)
    # Signal emitted when a switch box is clicked
    switch_clicked = QtCore.Signal(str, Switch)
    # Signal emitted when a node box is right-clicked
    node_right_clicked = QtCore.Signal(str, Controller)
    # Signal emitted when a plug is clicked
    plug_clicked = QtCore.Signal(str)
    # Signal emitted when a plug is clicked with the right mouse button
    plug_right_clicked = QtCore.Signal(str)
    # Signal emitted when a link is right-clicked
    link_right_clicked = QtCore.Signal(str, str, str, str)

    link_keydelete_clicked = QtCore.Signal(str, str, str, str)

    node_keydelete_clicked = QtCore.Signal(str)

    def __init__(self, parent=None, userlevel=0):
        super().__init__(parent)

        self.gnodes = {}
        self.glinks = {}
        self._pos = 50
        self.pos = {}
        self.dim = {}  # add by Irmage OM for recorded dimension of Nodes
        self.colored_parameters = True
        self.logical_view = False
        self._enable_edition = False
        self.labels = []
        self._userlevel = userlevel

        #         pen = QtGui.QPen(QtGui.QColor(250,100,0),2)
        #         self.l = QtCore.QLineF(-10,0,10,0)
        #         self.addLine(self.l,pen)
        #         self.l = QtCore.QLineF(0,-10,0,10)
        #         self.addLine(self.l,pen)

        self.colType = ColorType()

        self._update_pipeline_timer = Qt.QTimer()
        self._update_pipeline_timer.setSingleShot(True)
        self._update_pipeline_timer.timeout.connect(
            proxy_method(self, "update_pipeline_now")
        )

        self.changed.connect(self.update_paths)

    def __del__(self):
        # print('PipelineScene.__del__')
        try:
            self._release()
        except RuntimeError:
            pass  # C++ object deleted, attributes are already destroyed

    def _release(self):
        # print('PipelineScene._release')
        if hasattr(self, "pos"):
            del self.pos
        if hasattr(self, "dim"):
            del self.dim
        if hasattr(self, "labels"):
            del self.labels
        if hasattr(self, "glinks"):
            del self.glinks
        if "gnodes" in self.__dict__:
            import sip

            for gnode in self.gnodes.values():
                gnode._release()
                self.removeItem(gnode)
                sip.transferback(gnode)
            gnode = None
            del self.gnodes

        try:
            self.changed.disconnect()
        except TypeError:
            pass  # already done

        # force delete gnodes: needs to use gc.collect()
        import gc

        gc.collect()

    @property
    def userlevel(self):
        return self._userlevel

    @userlevel.setter
    def userlevel(self, value):
        if self._userlevel != value:
            self._userlevel = value
            for name, gnode in self.gnodes.items():
                gnode.userlevel = value
            self.update_pipeline()

    def _add_node(self, name, gnode):
        self.addItem(gnode)

        ################# add by Irmage OM ####################
        dim = self.dim.get(name)
        #         print("_add_node : dim : ",dim," , type =",type(dim).__name__)

        if dim is not None:
            if isinstance(dim, Qt.QPointF):
                dim = (dim.x(), dim.y())

            gnode.updateSize(dim[0], dim[1])
            # gnode.sizer.setPos(dim[0],dim[1])

        #         gnode.update_node()

        ######################################################

        pos = self.pos.get(name)
        if pos is None:
            gnode.setPos(2 * self._pos, self._pos)
            self._pos += 100
        else:
            if not isinstance(pos, Qt.QPointF):
                pos = Qt.QPointF(pos[0], pos[1])
            gnode.setPos(pos)

        self.gnodes[name] = gnode
        #         gnode.update_node()

        # repositioning 'inputs' node
        if name == "inputs":
            pos_left_most = (0, 0)
            for el in self.gnodes:
                if el != "inputs" and el != "outputs":
                    if pos_left_most[0] > self.gnodes[el].pos().x():
                        pos_left_most = (
                            self.gnodes[el].pos().x(),
                            self.gnodes[el].pos().y(),
                        )
            xl = pos_left_most[0] - (
                2 * self.gnodes[name].boundingRect().size().width()
            )
            yl = pos_left_most[1]
            self.gnodes[name].setPos(xl, yl)
        #             gnode.update_node()

        # repositioning 'outputs' node
        if name == "outputs":
            pos_right_most = (0, 0)
            for el in self.gnodes:
                if el != "inputs" and el != "outputs":
                    if (
                        pos_right_most[0]
                        < self.gnodes[el].pos().x()
                        + self.gnodes[el].boundingRect().size().width()
                    ):
                        pos_right_most = (
                            self.gnodes[el].pos().x()
                            + self.gnodes[el].boundingRect().size().width(),
                            self.gnodes[el].pos().y(),
                        )
            xl = pos_right_most[0] + self.gnodes[name].boundingRect().size().width()
            yl = pos_right_most[1]
            self.gnodes[name].setPos(xl, yl)
        #             gnode.update_node()

        ################" add by Irmage #############################################
        self.setSceneRect(QtCore.QRectF())
        #############################################################################_node_keydelete_clicked

    def add_node(self, node_name, node):
        process = node
        if isinstance(node, Pipeline):
            sub_pipeline = process
        elif process and isinstance(process, ProcessIteration):
            sub_pipeline = process.process
        else:
            sub_pipeline = None
        gnode = NodeGWidget(
            node_name,
            node.plugs,
            self.pipeline,
            sub_pipeline=sub_pipeline,
            process=process,
            colored_parameters=self.colored_parameters,
            logical_view=self.logical_view,
            labels=self.labels,
            userlevel=self.userlevel,
        )
        self._add_node(node_name, gnode)
        gnode.update_node()
        return gnode

    def add_link(self, source, dest, active, weak):
        #         print("add link ", source, dest)
        source_gnode_name, source_param = source
        if not source_gnode_name:
            source_gnode_name = "inputs"
        dest_gnode_name, dest_param = dest
        if not dest_gnode_name:
            dest_gnode_name = "outputs"
        if self.logical_view:
            source_param = "outputs"
            dest_param = "inputs"
        try:
            typeq = self.typeLink(source_gnode_name, source_param)
            #             color = self.colorLink(typeq)
            color = self.colType.colorLink(typeq)

        except Exception:
            color = ORANGE_2
        #         verif=((str(dest_gnode_name), str(dest_param)))
        #         print(str(verif) in str(self.glinks.keys()))
        source_dest = (
            (str(source_gnode_name), str(source_param)),
            (str(dest_gnode_name), str(dest_param)),
        )
        if source_dest in self.glinks:
            # already done
            if self.logical_view:
                # keep strongest link representation
                glink = self.glinks[source_dest]
                if active or glink.active:
                    active = True
                if not weak or not glink.weak:
                    weak = False
                if glink.weak != weak or glink.active != active:
                    glink.update_activation(active, weak, "current")
            return  # already done
        source_gnode = self.gnodes[source_gnode_name]
        dest_gnode = self.gnodes.get(dest_gnode_name)

        if dest_gnode is not None:
            if (
                dest_param in dest_gnode.in_plugs
                and source_param in source_gnode.out_plugs
            ):
                glink = Link(
                    source_gnode.mapToScene(
                        source_gnode.out_plugs[source_param].get_plug_point()
                    ),
                    dest_gnode.mapToScene(
                        dest_gnode.in_plugs[dest_param].get_plug_point()
                    ),
                    active,
                    weak,
                    color,
                )
                self.glinks[source_dest] = glink
                self.addItem(glink)

    def _remove_link(self, source_dest):
        source, dest = source_dest
        source_gnode_name, source_param = source
        if not source_gnode_name:
            source_gnode_name = "inputs"
        source_gnode = self.gnodes.get(source_gnode_name)
        dest_gnode_name, dest_param = dest
        if not dest_gnode_name:
            dest_gnode_name = "outputs"
        if self.logical_view:
            # is it useful ?
            source_param = "outputs"
            dest_param = "inputs"
        dest_gnode = self.gnodes.get(dest_gnode_name)
        new_source_dest = (
            (str(source_gnode_name), str(source_param)),
            (str(dest_gnode_name), str(dest_param)),
        )
        glink = self.glinks.get(new_source_dest)
        if glink is not None:
            self.removeItem(glink)
            del self.glinks[new_source_dest]

    def update_paths(self, regions=None):
        for name, i in self.gnodes.items():
            self.pos[i.name] = i.pos()
            br = i.box.boundingRect()
            self.dim[i.name] = (br.width(), br.height())

        dropped = []
        for source_dest, glink in self.glinks.items():
            source, dest = source_dest
            source_gnode_name, source_param = source
            dest_gnode_name, dest_param = dest
            source_gnode = self.gnodes[source_gnode_name]
            dest_gnode = self.gnodes[dest_gnode_name]
            if (
                source_param not in source_gnode.out_plugs
                or dest_param not in dest_gnode.in_plugs
            ):
                dropped.append(source_dest)
            else:
                glink.update(
                    source_gnode.mapToScene(
                        source_gnode.out_plugs[source_param].get_plug_point()
                    ),
                    dest_gnode.mapToScene(
                        dest_gnode.in_plugs[dest_param].get_plug_point()
                    ),
                )
        for source_dest in dropped:
            self._remove_link(source_dest)

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline

        self.labels = []
        pipeline_inputs = SortedDictionary()
        pipeline_outputs = SortedDictionary()
        if pipeline is not None:
            for name, plug in pipeline.nodes[""].plugs.items():
                if plug.output:
                    pipeline_outputs[name] = plug
                else:
                    pipeline_inputs[name] = plug
            if pipeline_inputs:
                self._add_node(
                    "inputs",
                    NodeGWidget(
                        "inputs",
                        pipeline_inputs,
                        pipeline,
                        process=pipeline,
                        colored_parameters=self.colored_parameters,
                        logical_view=self.logical_view,
                        userlevel=self.userlevel,
                    ),
                )
            for node_name, node in pipeline.nodes.items():
                if not node_name:
                    continue
                self.add_node(node_name, node)
            if pipeline_outputs:
                self._add_node(
                    "outputs",
                    NodeGWidget(
                        "outputs",
                        pipeline_outputs,
                        pipeline,
                        process=pipeline,
                        colored_parameters=self.colored_parameters,
                        logical_view=self.logical_view,
                        userlevel=self.userlevel,
                    ),
                )

            for source_node_name, source_node in pipeline.nodes.items():
                for source_parameter, source_plug in source_node.plugs.items():
                    for (
                        dest_node_name,
                        dest_parameter,
                        dest_node,
                        dest_plug,
                        weak_link,
                    ) in source_plug.links_to:
                        if dest_node is pipeline.nodes.get(dest_node_name):
                            self.add_link(
                                (source_node_name, source_parameter),
                                (dest_node_name, dest_parameter),
                                active=source_plug.activated and dest_plug.activated,
                                weak=weak_link,
                            )

    def update_pipeline(self):
        self._update_pipeline_timer.start(20)

    def update_pipeline_now(self):
        if self.logical_view:
            self._update_logical_pipeline()
        else:
            self._update_regular_pipeline()

    def _update_regular_pipeline(self):
        # normal view
        pipeline = self.pipeline
        removed_nodes = []

        #         print(self.gnodes)
        for node_name, gnode in self.gnodes.items():
            removed = False
            if gnode.logical_view:
                gnode.clear_plugs()
                gnode.logical_view = False
            if node_name in ("inputs", "outputs"):
                node = pipeline.nodes[""]
                # in case fields have been added/removed
                if node_name == "inputs":
                    pipeline_inputs = SortedDictionary()
                    for name, plug in node.plugs.items():
                        if not plug.output:
                            field = node.field(name)
                            if not getattr(field, "hidden", False) and (
                                getattr(field, "userlevel", None) is None
                                or field.userlevel <= self.userlevel
                            ):
                                pipeline_inputs[name] = plug
                    gnode.parameters = pipeline_inputs
                    if len(gnode.parameters) == 0:
                        # no inputs: remove the gnode
                        removed_nodes.append(node_name)
                        removed = True
                else:
                    pipeline_outputs = SortedDictionary()
                    for name, plug in node.plugs.items():
                        if plug.output:
                            field = node.field(name)
                            if not getattr(field, "hidden", False) and (
                                getattr(field, "userlevel", None) is None
                                or field.userlevel <= self.userlevel
                            ):
                                pipeline_outputs[name] = plug
                    gnode.parameters = pipeline_outputs
                    if len(gnode.parameters) == 0:
                        # no outputs: remove the gnode
                        removed_nodes.append(node_name)
                        removed = True
            else:
                node = pipeline.nodes.get(node_name)
                if node is None:  # removed node
                    removed_nodes.append(node_name)
                    removed = True
                    continue
            if not removed:
                gnode.active = node.activated
                gnode.update_node()

        # handle removed nodes
        for node_name in removed_nodes:
            gnode = self.gnodes[node_name]
            self.removeItem(gnode)
            self.gnodes.pop(node_name, None)
            self.dim.pop(node_name, None)
            self.pos.pop(node_name, None)
            import sip

            sip.transferback(gnode)
            # import objgraph
            # objgraph.show_backrefs(gnode)
            del gnode

        # check for added nodes
        added_nodes = []
        for node_name, node in pipeline.nodes.items():
            if node_name == "":
                pipeline_inputs = SortedDictionary()
                pipeline_outputs = SortedDictionary()
                for name, plug in node.plugs.items():
                    if plug.output:
                        pipeline_outputs[name] = plug
                    else:
                        pipeline_inputs[name] = plug
                if pipeline_inputs and "inputs" not in self.gnodes:
                    self._add_node(
                        "inputs",
                        NodeGWidget(
                            "inputs",
                            pipeline_inputs,
                            pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view,
                            userlevel=self.userlevel,
                        ),
                    )
                if pipeline_outputs and "outputs" not in self.gnodes:
                    self._add_node(
                        "outputs",
                        NodeGWidget(
                            "outputs",
                            pipeline_outputs,
                            pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view,
                            userlevel=self.userlevel,
                        ),
                    )
            elif node_name not in self.gnodes:
                process = node
                if isinstance(node, Pipeline):
                    sub_pipeline = node
                else:
                    sub_pipeline = None
                self.add_node(node_name, node)

        # links
        to_remove = []
        for source_dest, glink in self.glinks.items():
            source, dest = source_dest
            source_node_name, source_param = source
            dest_node_name, dest_param = dest
            if source_node_name == "inputs":
                source_node_name = ""
            if dest_node_name == "outputs":
                dest_node_name = ""
            source_node = pipeline.nodes.get(source_node_name)
            if source_node is None:
                to_remove.append(source_dest)
                continue
            source_plug = source_node.plugs.get(source_param)
            dest_node = pipeline.nodes.get(dest_node_name)
            if dest_node is None:
                to_remove.append(source_dest)
                continue
            dest_plug = dest_node.plugs.get(dest_param)
            remove_glink = False
            if source_plug is None or dest_plug is None:
                # plug[s] removed
                remove_glink = True
            else:
                active = source_plug.activated and dest_plug.activated
                weak = [
                    x[4]
                    for x in source_plug.links_to
                    if x[:2] == (dest_node_name, dest_param)
                ]
                if len(weak) == 0:
                    # link removed
                    remove_glink = True
                else:
                    weak = weak[0]
            if remove_glink:
                to_remove.append(source_dest)
            else:
                glink.update_activation(active, weak, "current")
        for source_dest in to_remove:
            self._remove_link(source_dest)
        # check added links
        for source_node_name, source_node in pipeline.nodes.items():
            for source_parameter, source_plug in source_node.plugs.items():
                for (
                    dest_node_name,
                    dest_parameter,
                    dest_node,
                    dest_plug,
                    weak_link,
                ) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated and dest_plug.activated,
                            weak=weak_link,
                        )
        self._update_steps()

    def _update_steps(self):
        pipeline = self.pipeline
        if not hasattr(pipeline, "pipeline_steps"):
            return
        steps = pipeline.pipeline_steps
        if steps is None:
            return
        for node_name, node in pipeline.nodes.items():
            gnode = self.gnodes.get(node_name)
            if gnode is None:
                continue
            labels = [
                "step: %s" % n.name
                for n in steps.fields()
                if node_name in getattr(n, "nodes", set())
            ]
            # print('update step labels on', node_name, ':', labels)
            gnode.update_labels(labels)

    def _update_logical_pipeline(self):
        # update nodes plugs and links in logical view mode
        pipeline = self.pipeline
        # nodes state
        removed_nodes = []
        for node_name, gnode in self.gnodes.items():
            if not gnode.logical_view:
                gnode.clear_plugs()
                gnode.logical_view = True
            if node_name in ("inputs", "outputs"):
                node = pipeline.nodes[""]
            else:
                node = pipeline.nodes.get(node_name)
                if node is None:  # removed node
                    removed_nodes.append(node_name)
                    continue
            gnode.active = node.activated
            gnode.update_node()

        # handle removed nodes
        for node_name in removed_nodes:
            self.removeItem(self.gnodes[node_name])
            import sip

            sip.transferback(self.gnodes[node_name])
            del self.gnodes[node_name]

        # check for added nodes
        added_nodes = []
        for node_name, node in pipeline.nodes.items():
            if node_name == "":
                pipeline_inputs = SortedDictionary()
                pipeline_outputs = SortedDictionary()
                for name, plug in node.plugs.items():
                    if plug.output:
                        pipeline_outputs["outputs"] = plug
                    else:
                        pipeline_inputs["inputs"] = plug
                if pipeline_inputs and "inputs" not in self.gnodes:
                    self._add_node(
                        "inputs",
                        NodeGWidget(
                            "inputs",
                            pipeline_inputs,
                            pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view,
                            userlevel=self.userlevel,
                        ),
                    )
                if pipeline_outputs and "outputs" not in self.gnodes:
                    self._add_node(
                        "outputs",
                        NodeGWidget(
                            "outputs",
                            pipeline_outputs,
                            pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view,
                            userlevel=self.userlevel,
                        ),
                    )
            elif node_name not in self.gnodes:
                process = node
                if isinstance(node, Pipeline):
                    sub_pipeline = node
                else:
                    sub_pipeline = None
                self.add_node(node_name, node)

        # links
        # delete all links
        for source_dest, glink in self.glinks.items():
            self.removeItem(glink)
        self.glinks = {}
        # recreate links
        for source_node_name, source_node in pipeline.nodes.items():
            for source_parameter, source_plug in source_node.plugs.items():
                for (
                    dest_node_name,
                    dest_parameter,
                    dest_node,
                    dest_plug,
                    weak_link,
                ) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated and dest_plug.activated,
                            weak=weak_link,
                        )
        self._update_steps()

    def set_enable_edition(self, state=True):
        self._enable_edition = state

    def edition_enabled(self):
        return self._enable_edition

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if not event.isAccepted():
            if event.key() == QtCore.Qt.Key_P:
                # print position of boxes
                event.accept()
                pview = self.parent()
                pview.print_node_positions()
            elif event.key() == QtCore.Qt.Key_T:
                for item in self.items():
                    if isinstance(item, boxItem):
                        item.focusOutEvent(Qt.QFocusEvent(Qt.QEvent.FocusOut))
                # toggle logical / full view
                pview = self.parent()
                pview.switch_logical_view()
                event.accept()
            elif event.key() == QtCore.Qt.Key_A:
                # auto-set nodes positions
                pview = self.parent()
                pview.auto_dot_node_positions()

        #             elif Qt.QKeySequence(event.key()+int(event.modifiers())) == Qt.QKeySequence("Ctrl+Z"):
        #                 self.undoTyping_clicked.emit()

    def link_tooltip_text(self, source_dest):
        """Tooltip text for the fiven link

        Parameters
        ----------
        source_dest: tuple (2 tuples of 2 strings)
            link description:
            ((source_node, source_param), (dest_node, dest_param))
        """
        source_node_name = source_dest[0][0]
        dest_node_name = source_dest[1][0]
        if source_node_name in ("inputs", "outputs"):
            proc = self.pipeline
            source_node_name = ""
            source_node = self.pipeline.nodes[source_node_name]
        else:
            source_node = self.pipeline.nodes[source_node_name]
            proc = source_node
        if dest_node_name in ("inputs", "outputs"):
            dest_node_name = ""
        splug = source_node.plugs[source_dest[0][1]]
        link = [
            l
            for l in splug.links_to
            if l[0] == dest_node_name and l[1] == source_dest[1][1]
        ][0]
        if splug.activated and link[3].activated:
            active = '<font color="#ffa000">activated</font>'
        else:
            active = '<font color="#a0a0a0">inactive</font>'
        if link[4]:
            weak = '<font color="#e0c0c0">weak</font>'
        else:
            weak = "<b>strong</b>"
        name = source_dest[0][1]
        value = getattr(proc, name, undefined)
        field = proc.field(name)
        field_type_str = field.type_str()
        inst_type = self.get_instance_type_string(value)
        typestr = (
            ("%s (%s)" % (inst_type, field_type_str)).replace("<", "").replace(">", "")
        )
        msg = """<h3>%s</h3>
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
""" % (
            source_dest[0][1],
            active,
            weak,
            typestr,
            html.escape(str(value)),
        )
        if field.is_path() or field.type is sc.Any:
            if self.is_existing_path(value):
                msg += """    <tr>
      <td></td>
      <td>existing path</td>
    </tr>
"""
            elif field.type is not sc.Any:
                msg += """    <tr>
      <td></td>
      <td><font color="#a0a0a0">non-existing path</font></td>
    </tr>
"""
        msg += "</table>"
        return msg

    @staticmethod
    def get_instance_type_string(value):
        if value is None:
            return "None"
        if value is undefined:
            return "undefined"
        return type(value).__name__

    @staticmethod
    def is_existing_path(value):
        if (
            value not in (None, undefined)
            and isinstance(value, str)
            and os.path.exists(value)
        ):
            return True
        return False

    @staticmethod
    def html_doc(doc_text):
        # TODO: sphinx transform
        text = doc_text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def plug_tooltip_text(self, node, name):
        """Tooltip text for a node plug"""
        if node.name in ("inputs", "outputs"):
            proc = self.pipeline
            splug = self.pipeline.plugs[name]
        else:
            src = self.pipeline.nodes[node.name]
            splug = src.plugs.get(name)
            if not splug:
                return None
            proc = src
        if splug.output:
            output = '<font color="#d00000">output</font>'
        else:
            output = '<font color="#00d000">input</font>'
        if splug.enabled:
            enabled = "enabled"
        else:
            enabled = '<font color="#a0a0a0">disabled</font>'
        if splug.activated:
            activated = "activated"
        else:
            activated = '<font color="#a0a0a0">inactive</font>'
        if splug.optional:
            optional = '<font color="#00d000">optional</font>'
        else:
            optional = "mandatory"
        value = getattr(proc, name, undefined)
        field = proc.field(name)
        field_type_str = field.type_str()
        if field.metadata("output", False) and field.metadata("write", None) is False:
            field_type_str += ", output filename"
        typestr = (
            ("%s (%s)" % (self.get_instance_type_string(value), field_type_str))
            .replace("<", "")
            .replace(">", "")
        )
        msg = """<h3>%s</h3>
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
""" % (
            name,
            output,
            optional,
            enabled,
            activated,
            typestr,
            html.escape(str(value)),
        )
        if field.is_path() or field.type is sc.Any:
            if self.is_existing_path(value):
                msg += """    <tr>
      <td></td>
      <td>existing path</td>
    </tr>
"""
            elif field.type is not sc.Any:
                msg += """    <tr>
      <td></td>
      <td><font color="#a0a0a0">non-existing path</font></td>
    </tr>
"""
        msg += "</table>"
        doc = field.metadata("doc", None)
        if doc:
            msg += "\n<h3>Description:</h3>\n"
            msg += self.html_doc(doc)
        return msg

    def node_tooltip_text(self, gnode):
        process = gnode.process
        msg = getattr(process, "__doc__", "")
        # msg = self.html_doc(doc)
        return msg

    def _parentgnode(self, item):
        if qt_backend.get_qt_backend() != "PyQt5":
            return item.parentItem()
        # in PyQt5 (certain versions at least, Ubuntu 16.04) parentItem()
        # returns something inappropriate, having the wrong type
        # QGraphicsVideoItem, probably a cast mistake, and which leads to
        # a segfault, so we have to get it a different way.
        nodes = [node for node in self.gnodes.values() if item in node.childItems()]
        if len(nodes) == 1:
            return nodes[0]

    def helpEvent(self, event):
        """
        Display tooltips on plugs and links
        """
        if self.logical_view:
            event.setAccepted(False)
            super().helpEvent(event)
            return
        item = self.itemAt(event.scenePos(), Qt.QTransform())
        if isinstance(item, Link):
            for source_dest, glink in self.glinks.items():
                if glink is item:
                    text = self.link_tooltip_text(source_dest)
                    item.setToolTip(text)
                    break
        elif isinstance(item, Plug):
            node = self._parentgnode(item)
            found = False
            for name, plug in node.in_plugs.items():
                if plug is item:
                    found = True
                    break
            if not found:
                for name, plug in node.out_plugs.items():
                    if plug is item:
                        found = True
                        break
            if found:
                text = self.plug_tooltip_text(node, name)
                item.setToolTip(text)
        elif isinstance(item, QtGui.QGraphicsRectItem):
            node = self._parentgnode(item)
            if isinstance(node, NodeGWidget):
                text = self.node_tooltip_text(node)
                item.setToolTip(text)
        elif isinstance(item, QtGui.QGraphicsProxyWidget):
            # PROBLEM: tooltips in child graphics scenes seem not to popup.
            #
            # to force them we would have to translate the event position to
            # the sub-scene position, and call the child scene helpEvent()
            # method, with a custom event.
            # However this is not possible, since QGraphicsSceneHelpEvent
            # does not provide a public (nor even protected) constructor, and
            # secondarily helpEvent() is protected.
            event.setAccepted(False)

        super().helpEvent(event)

    def remove_node(self, node_name):
        print(self.gnodes)
        gnode = self.gnodes.get(node_name)
        if gnode is None:
            # already done (possibly via a notification)
            return
        todel = set()
        import sip

        for link, glink in self.glinks.items():
            if link[0][0] == node_name or link[1][0] == node_name:
                self.removeItem(glink)
                todel.add(link)
        for link in todel:
            del self.glinks[link]
        self.removeItem(gnode)
        sip.transferback(self.gnodes[node_name])
        del self.gnodes[node_name]

    def _link_right_clicked(self, link):
        # find the link in list
        # print('Scene._link_right_clicked:', link)
        for source_dest, glink in self.glinks.items():
            if glink is link:
                self.link_right_clicked.emit(
                    source_dest[0][0],
                    source_dest[0][1],
                    source_dest[1][0],
                    source_dest[1][1],
                )
                break

    def _link_keydelete_clicked(self, link):
        for source_dest, glink in self.glinks.items():
            if glink is link:
                self.link_keydelete_clicked.emit(
                    source_dest[0][0],
                    source_dest[0][1],
                    source_dest[1][0],
                    source_dest[1][1],
                )
                break

    def _node_keydelete_clicked(self, node):
        self.node_keydelete_clicked.emit(node.name)

    def typeLink(self, name_node, name_plug):
        if name_node in ("inputs", "outputs"):
            proc = self.pipeline
            splug = self.pipeline.plugs[name_plug]
        else:
            src = self.pipeline.nodes[name_node]
            splug = src.plugs[name_plug]
            proc = src

        value = getattr(proc, name_plug)

        field_type_str = proc.field(name_plug).type_str()
        return field_type_str


class PipelineDeveloperView(QGraphicsView):
    """
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
    process_clicked
    node_clicked
    node_clicked_ctrl
    plug_clicked
    plug_right_clicked
    link_right_clicked
    colored_parameters
    scene

    Methods
    -------
    __init__
    set_pipeline
    is_logical_view
    set_logical_view
    zoom_in
    zoom_out
    openProcessController
    add_embedded_subpipeline
    onLoadSubPipelineClicked
    onOpenProcessController
    enableNode
    enable_step
    disable_preceding_steps
    disable_following_steps
    enable_preceding_steps
    enable_following_steps
    set_switch_value
    disable_done_steps
    enable_all_steps
    check_files
    auto_dot_node_positions
    save_dot_image_ui
    reset_initial_nodes_positions
    window
    """

    # subpipeline_clicked = QtCore.Signal(str, Process,
    # QtCore.Qt.KeyboardModifiers)
    subpipeline_clicked = QtCore.Signal(str, Process, int)
    """Signal emitted when a sub pipeline has to be open."""
    process_clicked = QtCore.Signal(str, Process)
    node_clicked = QtCore.Signal(str, Node)
    """Signal emitted when a node box has to be open."""
    node_clicked_ctrl = QtCore.Signal(str, Process)
    """Signal emitted when a node box has to be in the foreground."""
    switch_clicked = QtCore.Signal(str, Switch)
    """Signal emitted when a switch box has to be open."""
    node_right_clicked = QtCore.Signal(str, Controller)
    """Signal emitted when a node box is right-clicked"""
    plug_clicked = QtCore.Signal(str)
    """Signal emitted when a plug is clicked"""
    plug_right_clicked = QtCore.Signal(str)
    """Signal emitted when a plug is right-clicked"""
    link_right_clicked = QtCore.Signal(str, str, str, str)
    """Signal emitted when a link is right-clicked"""
    edit_sub_pipeline = QtCore.Signal(Pipeline)
    """Signal emitted when a sub-pipeline has to be edited"""
    open_filter = QtCore.Signal(str)
    """Signal emitted when an Input Filter has to be opened"""
    export_to_db_scans = QtCore.Signal(str)
    """Signal emitted when an Input Filter has to be linked to database_scans"""
    link_keydelete_clicked = QtCore.Signal(str, str, str, str)
    node_keydelete_clicked = QtCore.Signal(str)

    scene = None
    """
    type: PipelineScene

    the main scene.
    """
    colored_parameters = True
    """
    If enabled (default), parameters in nodes boxes are displayed with color
    codes representing their state, and the state of their values: output
    parameters, empty values, existing files, non-existing files...

    When colored_parameters is set, however, callbacks have to be installed to
    track changes in fields values, so this actually has an overhead.
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
    """

    class ProcessNameEdit(Qt.QLineEdit):
        """A specialized QLineEdit with completion for process name"""

        def __init__(self, parent=None, class_type_check=is_executable):
            super().__init__(parent)
            self.compl = QtGui.QCompleter([])
            self.setCompleter(self.compl)
            self.textEdited.connect(self.on_text_edited)
            self.py_cache = {}  # cache for loaded python files
            self.class_type_check = class_type_check

        @staticmethod
        def _execfile(filename):
            glob_dict = {}
            exec(
                compile(open(filename, "rb").read(), filename, "exec"),
                glob_dict,
                glob_dict,
            )
            return glob_dict

        def load_py(self, filename):
            if filename not in self.py_cache:
                try:
                    self.py_cache[filename] = self._execfile(filename)
                except Exception as e:
                    print("exception while executing file %s:" % filename, e)
                    return {}
            return self.py_cache[filename]

        def get_processes_or_modules(self, filename):
            file_dict = self.load_py(filename)
            processes = []
            for name, item in file_dict.items():
                if self.class_type_check(item) or inspect.ismodule(item):
                    processes.append(name)
            return processes

        def on_text_edited(self, text):
            compl = set()
            modpath = str(text).split(".")
            current_mod = None
            paths = []
            sel = set()
            mod = None
            if len(modpath) > 1:
                current_mod = ".".join(modpath[:-1])
                try:
                    mod = importlib.import_module(current_mod)
                except ImportError:
                    mod = None
                if mod:
                    if os.path.basename(mod.__file__).startswith("__init__.py"):
                        paths = [os.path.dirname(mod.__file__)]
                    # add process/pipeline objects in current_mod
                    procs = [
                        item
                        for k, item in mod.__dict__.items()
                        if self.class_type_check(item) or inspect.ismodule(item)
                    ]
                    compl.update([".".join([current_mod, c.__name__]) for c in procs])
            if not mod:
                # no current module
                # is it a path name ?
                pathname, filename = os.path.split(str(text))
                if os.path.isdir(pathname):
                    # look for class in python file filename.py#classname
                    elements = filename.split(".py#")
                    if len(elements) == 2:
                        filename = elements[0] + ".py"
                        object_name = elements[1]
                        full_path = os.path.join(pathname, filename)
                        processes = self.get_processes_or_modules(full_path)
                        if object_name != "":
                            processes = [
                                p for p in processes if p.startswith(object_name)
                            ]
                        compl.update(["#".join((full_path, p)) for p in processes])
                    else:
                        # look for matching xml files
                        for f in os.listdir(pathname):
                            if (
                                f.endswith(".xml")
                                or os.path.isdir(os.path.join(pathname, f))
                            ) and f.startswith(filename):
                                compl.add(os.path.join(pathname, f))
                            elif f.endswith(".py"):
                                compl.add(os.path.join(pathname, f))
                else:
                    paths = sys.path
            for path in paths:
                if path == "":
                    path = "."
                try:
                    for f in os.listdir(path):
                        if f.endswith(".py"):
                            sel.add(f[:-3])
                        elif f.endswith(".pyc") or f.endswith(".pyo"):
                            sel.add(f[:-4])
                        elif f.endswith(".xml"):
                            sel.add(f)
                        elif "." not in f and os.path.isdir(os.path.join(path, f)):
                            sel.add(f)
                except OSError:
                    pass
            begin = modpath[-1]
            cm = []
            if current_mod is not None:
                cm = [current_mod]
            compl.update([".".join(cm + [f]) for f in sel if f.startswith(modpath[-1])])
            model = self.compl.model()
            model.setStringList(list(compl))

    def __init__(
        self,
        pipeline=None,
        parent=None,
        show_sub_pipelines=False,
        allow_open_controller=False,
        logical_view=False,
        enable_edition=False,
        userlevel=0,
    ):
        """PipelineDeveloperView

        Parameters
        ----------
        pipeline:  Pipeline (optional)
            pipeline object to be displayed
            If omitted an empty pipeline will be used, and edition mode will be
            activated.
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
        logical_view:  bool (optional)
            if set, plugs and links between plugs are hidden, only links
            between nodes are displayed.
        enable_edition: bool (optional)
            if set, pipeline edition features are available in GUI and menus:
            adding process boxes, drawing links etc. If pipeline is not
            specified, then edition will be activated anyway.
        """

        super().__init__(parent)

        # self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.centerOn(0, 0)

        self.setRenderHints(
            Qt.QPainter.Antialiasing | Qt.QPainter.SmoothPixmapTransform
        )
        self.setBackgroundBrush(QtGui.QColor(60, 60, 60))
        self.scene = None
        self.colored_parameters = True
        self._show_sub_pipelines = show_sub_pipelines
        self._allow_open_controller = allow_open_controller
        self._logical_view = logical_view
        self._enable_edition = enable_edition
        self._pipeline_filename = ""
        self._restricted_edition = False
        self.disable_overwrite = False
        self._userlevel = userlevel
        self.doc_browser = None

        self.set_pipeline(pipeline)
        self._grab = False
        self._grab_link = False
        self.plug_clicked.connect(self._plug_clicked)
        self.plug_right_clicked.connect(self._plug_right_clicked)
        self.link_right_clicked.connect(self._link_clicked)
        self.node_clicked_ctrl.connect(self._node_clicked_ctrl)
        self.link_keydelete_clicked.connect(self._link_delete_clicked)
        self.node_keydelete_clicked.connect(self._node_delete_clicked)

    def __del__(self):
        # print('PipelineDeveloperView.__del__')
        self.release_pipeline(delete=True)
        # super().__del__()

    @property
    def userlevel(self):
        return self._userlevel

    @userlevel.setter
    def userlevel(self, value):
        self._userlevel = value
        if self.scene:
            self.scene.userlevel = value
        for widget in self.findChildren(QtGui.QWidget):
            if hasattr(widget, "userlevel"):
                widget.userlevel = value

    def ensure_pipeline(self, pipeline):
        """
        Check that we have a pipeline or a process
        """
        if pipeline is None:
            pipeline = CustomPipeline()
            enable_edition = True

        if not isinstance(pipeline, Pipeline):
            if isinstance(pipeline, Process):
                process = pipeline
                pipeline = CustomPipeline()
                # pipeline.set_capsul_engine(process.get_completion_engine())
                pipeline.add_process(process.name, process)
                pipeline.autoexport_nodes_parameters()
                pipeline.node_position["inputs"] = (0.0, 0.0)
                pipeline.node_position[process.name] = (300.0, 0.0)
                pipeline.node_position["outputs"] = (600.0, 0.0)
                # pipeline.scene_scale_factor = 0.5
                pipeline.node_dimension[process.name] = (
                    300.0,
                    200.0,
                )  # add by Irmage OM
            else:
                raise Exception(
                    f"Expect a Pipeline or a Process, not a '{pipeline!r}'."
                )
        return pipeline

    def _set_pipeline(self, pipeline):
        pos = {}
        dim = {}
        if self.scene:
            pos = self.scene.pos
            dim = self.scene.dim  # add by Irmage OM
            # pprint(dict((i, (j.x(), j.y())) for i, j in pos.items()))
        if hasattr(pipeline, "node_position"):
            for i, j in pipeline.node_position.items():
                if isinstance(j, QtCore.QPointF):
                    pos[i] = j
                else:
                    pos[i] = QtCore.QPointF(*j)

        ############### add by Irmage OM #######################
        if hasattr(pipeline, "node_dimension"):
            for i, j in pipeline.node_dimension.items():
                if isinstance(j, QtCore.QPointF):
                    dim[i] = (j.x(), j.y())
                else:
                    dim[i] = j

        #         print("_set_pipeline : ",pos," ; ",dim)
        #######################################################
        self.release_pipeline()
        self.scene.set_pipeline(pipeline)
        self.scene.pos = pos
        self.scene.dim = dim
        if pipeline is not None:
            self.setWindowTitle(pipeline.name)
            # Try to initialize the scene scale factor
            if hasattr(pipeline, "scene_scale_factor"):
                self.scale(pipeline.scene_scale_factor, pipeline.scene_scale_factor)

            self.reset_initial_nodes_positions()

        ################" add by Irmage #############################################
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)
        #############################################################################

    def set_pipeline(self, pipeline):
        """
        Assigns a new pipeline to the view.
        """
        pipeline = self.ensure_pipeline(pipeline)
        self._set_pipeline(pipeline)
        if pipeline is not None:
            # Setup callback to update view when pipeline state is modified
            pipeline.selection_changed.add(proxy_method(self, "_reset_pipeline"))
            pipeline.on_fields_change.add(proxy_method(self, "_reset_pipeline"))
            if hasattr(pipeline, "pipeline_steps"):
                pipeline.pipeline_steps.on_attribute_change.add(
                    proxy_method(self, "_reset_pipeline")
                )

    def release_pipeline(self, delete=False):
        """
        Releases the pipeline currently viewed (and remove the callbacks)

        If ``delete`` is set, this means the view is within deletion process
        and a new scene should not be built
        """
        # Setup callback to update view when pipeline state is modified
        pipeline = None
        if self.scene is not None and hasattr(self.scene, "pipeline"):
            pipeline = self.scene.pipeline
        if pipeline is not None:
            if hasattr(pipeline, "pipeline_steps"):
                pipeline.pipeline_steps.on_attribute_change.remove(
                    proxy_method(self, "_reset_pipeline")
                )
            pipeline.selection_changed.remove(proxy_method(self, "_reset_pipeline"))
            pipeline.on_fields_change.remove(proxy_method(self, "_reset_pipeline"))
        self.setScene(None)
        if self.scene:
            # force destruction of scene internals now that the Qt object
            # still exists
            self.scene._release()
            # the scene is not deleted after all refs are released, even
            # after self.setScene(None). This is probably a bug in PyQt:
            # the C++ layer keeps ownership of the scene, whereas it should
            # not: the Qt doc specifies for QGraphicsView.setScene():
            # "The view does not take ownership of scene.", however in PyQt it
            # does, and only releases it when the QGraphicsView is deleted.
            # Thus we have to force it by hand:
            import sip

            sip.transferback(self.scene)
            self.scene = None
            import gc

            gc.collect()
        if not delete and (pipeline is not None or self.scene is None):
            self.scene = PipelineScene(self, userlevel=self.userlevel)
            self.scene.set_enable_edition(self._enable_edition)
            self.scene.logical_view = self._logical_view
            self.scene.colored_parameters = self.colored_parameters
            self.scene.subpipeline_clicked.connect(self.subpipeline_clicked)
            self.scene.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)
            self.scene.process_clicked.connect(self._node_clicked)
            self.scene.node_clicked.connect(self._node_clicked)
            self.scene.node_clicked_ctrl.connect(self._node_clicked_ctrl)
            self.scene.switch_clicked.connect(self.switch_clicked)
            self.scene.node_right_clicked.connect(self.node_right_clicked)
            self.scene.node_right_clicked.connect(self.onOpenProcessController)
            self.scene.plug_clicked.connect(self.plug_clicked)
            self.scene.plug_right_clicked.connect(self.plug_right_clicked)
            self.scene.link_right_clicked.connect(self.link_right_clicked)
            self.scene.link_keydelete_clicked.connect(self.link_keydelete_clicked)
            self.scene.node_keydelete_clicked.connect(self.node_keydelete_clicked)
            self.scene.pos = {}
            self.scene.dim = {}
            self.setWindowTitle("<no pipeline>")
            self.setScene(self.scene)

    def is_logical_view(self):
        """
        in logical view mode, plugs and links between plugs are hidden, only
        links between nodes are displayed.
        """
        return self._logical_view

    def set_logical_view(self, state):
        """
        in logical view mode, plugs and links between plugs are hidden, only
        links between nodes are displayed.

        Parameters
        ----------
        state:  bool (mandatory)
            to set/unset the logical view mode
        """
        self._logical_view = state
        self._reset_pipeline()

    def _reset_pipeline(self):
        # self._set_pipeline(pipeline)
        self.scene.logical_view = self._logical_view
        self.scene.update_pipeline()

    def zoom_in(self):
        """
        Zoom the view in, applying a 1.2 zoom factor
        """
        scf = 1.2
        self.scale(scf, scf)
        cur_pos = self.mapFromGlobal(Qt.QCursor.pos())
        c_pos = Qt.QPointF(self.width() / 2, self.height() / 2)
        p = (cur_pos - c_pos) * (scf - 1.0)
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() + int(p.x())
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + int(p.y()))

    def zoom_out(self):
        """
        Zoom the view out, applying a 1/1.2 zool factor
        """
        scf = 1.0 / 1.2
        self.scale(scf, scf)
        cur_pos = self.mapFromGlobal(Qt.QCursor.pos())
        c_pos = Qt.QPointF(self.width() / 2, self.height() / 2)
        p = (cur_pos - c_pos) * (scf - 1.0)
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() + int(p.x())
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + int(p.y()))

    def edition_enabled(self):
        """
        Get the editable state
        """
        return self._enable_edition

    def set_enable_edition(self, state=True):
        """
        Set the editable state. Edition allows to modify a pipeline: adding /
        removing process boxes and switches, drawing links, etc.
        """
        self._enable_edition = state
        self.scene.set_enable_edition(state)

    def is_restricted_edition_mode(self):
        """
        Get the restricted mode status

        Returns
        -------
        enabled: bool
        """
        return self._restricted_edition

    def set_restricted_edition_mode(self, enabled):
        """
        Set the restricted edition mode. In restricted mode, some background
        menu actions ("add process", "open node controller"...) are not
        available.

        Parameters
        ----------
        enabled: bool
        """
        self._restricted_edition = enabled

    def wheelEvent(self, event):
        done = False
        if event.modifiers() == QtCore.Qt.ControlModifier:
            item = self.itemAt(event.pos())
            if not isinstance(item, QtGui.QGraphicsProxyWidget):
                done = True
                if qt_backend.get_qt_backend() == "PyQt5":
                    delta = event.angleDelta().y()
                else:
                    delta = event.delta()
                if delta < 0:
                    self.zoom_out()
                else:
                    self.zoom_in()
                event.accept()
        if not done:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not event.isAccepted():
            if event.button() == QtCore.Qt.RightButton:
                self.open_background_menu()
            else:
                self._grab = True
                self._grabpos = event.pos()

            #             print("background clicked")

            for source_dest, glink in self.scene.glinks.items():
                glink.fonced_viewer(False)
            for node_name, gnode in self.scene.gnodes.items():
                gnode.fonced_viewer(False)

    def mouseReleaseEvent(self, event):
        self._grab = False
        if self._grab_link:
            event.accept()
            try:
                self._release_grab_link(event)
            except Exception as e:
                print("source to destination types are not compatible")
                print(e)

        super().mouseReleaseEvent(event)
        self.scene.update()

    def mouseMoveEvent(self, event):
        if self._grab:
            event.accept()
            translation = event.pos() - self._grabpos
            self._grabpos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(translation.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(translation.y())
            )
        elif self._grab_link:
            self._move_grab_link(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        """Event handler when the mouse enters the widget.

        :param event: event
        """

        if event.mimeData().hasFormat("component/name"):
            event.accept()

    def dragMoveEvent(self, event):
        """Event handler when the mouse moves in the widget.

        :param event: event
        """

        if event.mimeData().hasFormat("component/name"):
            event.accept()

    def dropEvent(self, event):
        """Event handler when something is dropped in the widget.

        :param event: event

        """

        if event.mimeData().hasFormat("component/name"):
            self.click_pos = QtGui.QCursor.pos()
            path = bytes(event.mimeData().data("component/name"))
            self.drop_process(path.decode("utf8"))

    def drop_process(self, path):
        """Find the dropped process in the system's paths.

        :param path: class's path (e.g. "nipype.interfaces.spm.Smooth") (str)
        """

        package_name, process_name = os.path.splitext(path)
        process_name = process_name[1:]
        __import__(package_name)
        pkg = sys.modules[package_name]
        for name, instance in sorted(list(pkg.__dict__.items())):
            if name == process_name:
                if issubclass(instance, Node):
                    # it's a node
                    try:
                        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                        self.add_named_node(None, instance)
                        QtGui.QApplication.restoreOverrideCursor()
                        return
                    except Exception as e:
                        print(e)
                        return
                try:
                    process = executable(instance)
                except Exception as e:
                    print(e)
                    return
                else:
                    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self.add_named_process(instance)
                    QtGui.QApplication.restoreOverrideCursor()

    def add_embedded_subpipeline(self, subpipeline_name, scale=None):
        """
        Adds an embedded sub-pipeline inside its parent node.
        """
        gnode = self.scene.gnodes.get(str(subpipeline_name))
        if gnode is not None:
            sub_pipeline = self.scene.pipeline.nodes[str(subpipeline_name)]
            gnode.add_subpipeline_view(
                sub_pipeline, self._allow_open_controller, scale=scale
            )

    def onLoadSubPipelineClicked(self, node_name, sub_pipeline, modifiers):
        """Event to load a open a sub-pipeline view.
        If ctrl is pressed the new view will be embedded in its parent node
        box.
        """
        if self._show_sub_pipelines:
            if modifiers & QtCore.Qt.ControlModifier:
                try:
                    self.add_embedded_subpipeline(node_name)
                    return
                except KeyError:
                    print("node not found in:")
                    print(list(self.scene.gnodes.keys()))
            sub_view = PipelineDeveloperView(
                sub_pipeline,
                show_sub_pipelines=self._show_sub_pipelines,
                allow_open_controller=self._allow_open_controller,
                enable_edition=self.edition_enabled(),
                logical_view=self._logical_view,
                userlevel=self.userlevel,
            )
            # set self.window() as QObject parent (not QWidget parent) to
            # prevent the sub_view to close/delete immediately
            QtCore.QObject.setParent(sub_view, self.window())
            sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            sub_view.setWindowTitle(node_name)
            sub_view.doc_browser = self
            self.scene.update()
            sub_view.show()

    def window(self):
        """
        window() is overloaded from QWidget.window() to handle embedded views
        cases.
        A PipelineDeveloperView may be displayed inside a NodeGWidget.
        In this case, we want to go up to the parent scene's window to the
        "real" top window, where QWidget.window() will end in the current
        graphics scene.
        """
        if hasattr(self, "_graphics_item"):
            return self._graphics_item.scene().views()[0].window()
        else:
            return super().window()

    def onOpenProcessController(self, node_name, process):
        """Event to open a sub-process/sub-pipeline controller"""
        if self._allow_open_controller:
            self.open_node_menu(node_name, process)

    def openProcessController(self):
        sub_view = QtGui.QScrollArea()
        node_name = self.current_node_name
        if node_name in ("inputs", "outputs"):
            node_name = ""
        process = self.scene.pipeline.nodes[node_name]

        cwidget = AttributedProcessWidget(
            process,
            enable_attr_from_filename=True,
            enable_load_buttons=True,
            user_level=self.userlevel,
        )
        sub_view.setWidget(cwidget)
        sub_view.setWidgetResizable(True)
        sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        sub_view.setWindowTitle(self.current_node_name)
        # try to resize to a width that doesn't need an horizontal scrollbar
        sub_view.resize(
            cwidget.controller_widget.parent().parent().sizeHint().width(),
            sub_view.sizeHint().height(),
        )
        sub_view.show()
        # set self.window() as QObject parent (not QWidget parent) to
        # prevent the sub_view to close/delete immediately
        QtCore.QObject.setParent(sub_view, self.window())

    def open_node_menu(self, node_name, process):
        """right-click popup menu for nodes"""
        node_type = "process"
        if isinstance(process, Switch):
            node_type = "switch"
        menu = QtGui.QMenu("Node: %s" % node_name, None)
        title = menu.addAction("Node: %s (%s)" % (node_name, node_type))
        title.setEnabled(False)
        menu.addSeparator()

        self.current_node_name = node_name
        self.current_process = process
        if node_name in ("inputs", "outputs"):
            node_name = ""
        node = self.scene.pipeline.nodes[node_name]

        # Input_Filter
        if process.name == "Input_Filter":
            open_filter = menu.addAction("Open filter")
            open_filter.triggered.connect(self.emit_open_filter)

            export_to_db_scans = menu.addAction("Export to database_scans")
            export_to_db_scans.triggered.connect(self.emit_export_to_db_scans)

            menu.addSeparator()

        if not self._restricted_edition:
            controller_action = QtGui.QAction("open node controller", menu)
            controller_action.triggered.connect(self.openProcessController)
            menu.addAction(controller_action)

        disable_action = QtGui.QAction("Enable/disable node", menu)
        disable_action.setCheckable(True)
        disable_action.setChecked(node.enabled)
        disable_action.toggled.connect(self.enableNode)
        menu.addAction(disable_action)

        steps = getattr(self.scene.pipeline, "pipeline_steps", None)
        if steps is not None:
            my_steps = [
                step.name
                for step in steps.fields()
                if node.name in step.metadata("nodes", set())
            ]
            for step in my_steps:
                step_action = menu.addAction("(enable) step: %s" % step)
                step_action.setCheckable(True)
                step_state = getattr(self.scene.pipeline.pipeline_steps, step)
                step_action.setChecked(step_state)
                step_action.toggled.connect(SomaPartial(self.enable_step, step))
            if len(my_steps) != 0:
                step = my_steps[0]
                disable_prec = menu.addAction("Disable preceding steps")
                disable_prec.triggered.connect(
                    SomaPartial(self.disable_preceding_steps, step)
                )
                enable_prec = menu.addAction("Enable preceding steps")
                enable_prec.triggered.connect(
                    SomaPartial(self.enable_preceding_steps, step)
                )
                step = my_steps[-1]
                disable_foll = menu.addAction("Disable following steps")
                disable_foll.triggered.connect(
                    SomaPartial(self.disable_following_steps, step)
                )
                enable_foll = menu.addAction("Enable following steps")
                enable_foll.triggered.connect(
                    SomaPartial(self.enable_following_steps, step)
                )

        enable_all_action = menu.addAction("Enable all steps")
        enable_all_action.triggered.connect(self.enable_all_steps)
        disable_done_action = menu.addAction("Disable steps with existing outputs")
        disable_done_action.triggered.connect(self.disable_done_steps)
        check_pipeline_action = menu.addAction("Check input / output files")
        check_pipeline_action.triggered.connect(self.check_files)

        if isinstance(node, Switch):
            # allow to select switch value from the menu
            submenu = menu.addMenu("Switch value")
            agroup = QtGui.QActionGroup(submenu)
            values = node.field("switch").subtypes()
            value = node.switch
            set_index = -1
            for item in values:
                action = submenu.addAction(item)
                action.setCheckable(True)
                action.triggered.connect(SomaPartial(self.set_switch_value, node, item))
                if item == value:
                    action.setChecked(True)

        if not self.get_doc_browser(create=False):
            menu.addSeparator()
            doc_action = menu.addAction("Show doc")
            doc_action.triggered.connect(self.show_doc)

        if self.edition_enabled():
            menu.addSeparator()
            del_node_action = menu.addAction("Delete node")
            del_node_action.triggered.connect(self.del_node)
            if node is not self.scene.pipeline:
                export_mandatory_plugs = menu.addAction(
                    "Export unconnected mandatory plugs"
                )
                export_mandatory_plugs.triggered.connect(
                    self.export_node_unconnected_mandatory_plugs
                )
                export_all_plugs = menu.addAction("Export all unconnected plugs")
                export_all_plugs.triggered.connect(
                    self.export_node_all_unconnected_plugs
                )
                export_mandatory_inputs = menu.addAction(
                    "Export unconnected mandatory inputs"
                )
                export_mandatory_inputs.triggered.connect(
                    self.export_node_unconnected_mandatory_inputs
                )
                export_all_inputs = menu.addAction("Export all unconnected inputs")
                export_all_inputs.triggered.connect(
                    self.export_node_all_unconnected_inputs
                )
                export_mandatory_outputs = menu.addAction(
                    "Export unconnected mandatory outputs"
                )
                export_mandatory_outputs.triggered.connect(
                    self.export_node_unconnected_mandatory_outputs
                )
                export_all_outputs = menu.addAction("Export all unconnected outputs")
                export_all_outputs.triggered.connect(
                    self.export_node_all_unconnected_outputs
                )
                step = None
                if steps is not None:
                    my_steps = [
                        step.name
                        for step in steps.fields()
                        if node.name in step.metadata("nodes", set())
                    ]
                    if len(my_steps) == 1:
                        step = my_steps[0]
                    elif len(my_steps) >= 2:
                        step = repr(my_steps)
                change_step = menu.addAction("change step: %s" % step)
                change_step.triggered.connect(self._change_step)

        # Added to choose to visualize optional parameters
        gnode = self.scene.gnodes[self.current_node_name]

        menu.addSeparator()
        show_opt_inputs = menu.addAction("Show optional inputs")
        show_opt_inputs.setCheckable(True)
        show_opt_inputs.triggered.connect(self.show_optional_inputs)
        if gnode.show_opt_inputs:
            show_opt_inputs.setChecked(True)

        show_opt_outputs = menu.addAction("Show optional outputs")
        show_opt_outputs.setCheckable(True)
        show_opt_outputs.triggered.connect(self.show_optional_outputs)
        if gnode.show_opt_outputs:
            show_opt_outputs.setChecked(True)

        # Emit a signal to edit the node if it is a Pipeline
        if isinstance(node, Pipeline):
            menu.addSeparator()
            edit_sub_pipeline = menu.addAction("Edit sub-pipeline")
            edit_sub_pipeline.triggered.connect(self.emit_edit_sub_pipeline)

        menu.exec_(QtGui.QCursor.pos())
        del self.current_node_name
        del self.current_process

    def emit_export_to_db_scans(self):
        self.export_to_db_scans.emit(self.current_node_name)

    def emit_open_filter(self):
        self.open_filter.emit(self.current_node_name)

    def emit_edit_sub_pipeline(self):
        node = self.scene.pipeline.nodes[self.current_node_name]
        sub_pipeline = get_ref(node)
        self.edit_sub_pipeline.emit(sub_pipeline)

    def show_optional_inputs(self):
        """
        Added to choose to visualize optional inputs.
        """

        gnode = self.scene.gnodes[self.current_node_name]
        connected_plugs = []

        # print(self.current_node_name)
        # print(gnode.in_plugs)

        # for source_dest, link in self.scene.glinks.items():
        #     print(source_dest,",",self.current_node_name in str(source_dest))

        # The show_opt_inputs attribute is not changed yet
        if gnode.show_opt_inputs:
            # Verifying that the plugs are not connected to another node
            for param, pipeline_plug in gnode.parameters.items():
                # print(param," : ",pipeline_plug.activated)
                output = (
                    not pipeline_plug.output
                    if gnode.name in ("inputs", "outputs")
                    else pipeline_plug.output
                )
                if not output:
                    if (
                        pipeline_plug.optional
                        and pipeline_plug.links_from
                        and gnode.show_opt_inputs
                    ):
                        connected_plugs.append(param)
            if connected_plugs:
                if len(connected_plugs) == 1:
                    text = "Please remove links from this plug:\n"
                else:
                    text = "Please remove links from these plugs:\n"
                for plug_name in connected_plugs:
                    text += plug_name + ", "
                text = text[:-2] + "."

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText(text)
                msg.setWindowTitle("Error while changing the view of the node")
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg.exec_()
                return

        # Changing the show_opt_outputs attribute
        gnode.change_input_view()
        self.scene.update_pipeline()

    def show_optional_outputs(self):
        """
        Added to choose to visualize optional outputs.
        """

        gnode = self.scene.gnodes[self.current_node_name]
        connected_plugs = []

        # The show_opt_outputs attribute is not changed yet
        if gnode.show_opt_outputs:
            # Verifying that the plugs are not connected to another node
            for param, pipeline_plug in gnode.parameters.items():
                output = (
                    not pipeline_plug.output
                    if gnode.name in ("inputs", "outputs")
                    else pipeline_plug.output
                )
                if output:
                    if (
                        pipeline_plug.optional
                        and pipeline_plug.links_to
                        and gnode.show_opt_outputs
                    ):
                        connected_plugs.append(param)
            if connected_plugs:
                if len(connected_plugs) == 1:
                    text = "Please remove links from this plug:\n"
                else:
                    text = "Please remove links from these plugs:\n"
                for plug_name in connected_plugs:
                    text += plug_name + ", "
                text = text[:-2] + "."

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText(text)
                msg.setWindowTitle("Error while changing the view of the node")
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg.exec_()
                return

        # Changing the show_opt_outputs attribute
        gnode.change_output_view()
        self.scene.update_pipeline()

    def open_background_menu(self):
        """
        Open the right-click menu when triggered from the pipeline background.
        """
        self.click_pos = QtGui.QCursor.pos()
        has_dot = distutils.spawn.find_executable("dot")
        menu = QtGui.QMenu("Pipeline level menu", None)
        title = menu.addAction("Pipeline level menu")
        title.setEnabled(False)
        menu.addSeparator()

        if self.is_logical_view():
            logical_view = menu.addAction("Switch to regular parameters view")
        else:
            logical_view = menu.addAction("Switch to logical pipeline view")
        logical_view.triggered.connect(self.switch_logical_view)
        auto_node_pos = menu.addAction("Auto arrange nodes positions")
        auto_node_pos.triggered.connect(self.auto_dot_node_positions)
        if not has_dot:
            auto_node_pos.setEnabled(False)
            auto_node_pos.setText(
                "Auto arrange nodes positions (needs graphviz/dot tool " "installed)"
            )
        init_node_pos = menu.addAction("Reset to initial nodes positions")
        init_node_pos.triggered.connect(self.reset_initial_nodes_positions)
        if (
            not hasattr(self.scene.pipeline, "node_position")
            or len(self.scene.pipeline.node_position) == 0
        ):
            init_node_pos.setEnabled(False)
            init_node_pos.setText("Reset to initial nodes positions (none defined")
        save_dot = menu.addAction("Save image of pipeline graph")
        save_dot.triggered.connect(self.save_dot_image_ui)
        if not has_dot:
            save_dot.setEnabled(False)
            save_dot.setText(
                "Save image of pipeline graph (needs graphviz/dot tool " "installed)"
            )
        menu.addSeparator()
        print_pos = menu.addAction("Print nodes positions")
        print_pos.triggered.connect(self.print_node_positions)

        if self._enable_edition:
            menu.addSeparator()
            if not self._restricted_edition:
                add_proc = menu.addAction("Add process in pipeline")
                add_proc.triggered.connect(self.add_process)
            add_switch = menu.addAction("Add switch in pipeline")
            add_switch.triggered.connect(self.add_switch)
            # add_optional_output_switch = menu.addAction(
            #     'Add optional output switch in pipeline')
            # add_optional_output_switch.triggered.connect(
            #     self.add_optional_output_switch)
            add_iter_proc = menu.addAction("Add iterative process in pipeline")
            add_iter_proc.triggered.connect(self.add_iterative_process)
            add_node = menu.addAction("Add custom node in pipeline")
            add_node.triggered.connect(self.add_node)

            menu.addSeparator()
            export_mandatory_plugs = menu.addAction(
                "Export unconnected mandatory plugs"
            )
            export_mandatory_plugs.triggered.connect(
                self.export_unconnected_mandatory_plugs
            )
            export_all_plugs = menu.addAction("Export all unconnected plugs")
            export_all_plugs.triggered.connect(self.export_all_unconnected_plugs)
            export_mandatory_inputs = menu.addAction(
                "Export unconnected mandatory inputs"
            )
            export_mandatory_inputs.triggered.connect(
                self.export_unconnected_mandatory_inputs
            )
            export_all_inputs = menu.addAction("Export all unconnected inputs")
            export_all_inputs.triggered.connect(self.export_all_unconnected_inputs)
            export_mandatory_outputs = menu.addAction(
                "Export unconnected mandatory outputs"
            )
            export_mandatory_outputs.triggered.connect(
                self.export_unconnected_mandatory_outputs
            )
            export_all_outputs = menu.addAction("Export all unconnected outputs")
            export_all_outputs.triggered.connect(self.export_all_unconnected_outputs)
            prune = menu.addAction("Prune unused pipeline plugs")
            prune.triggered.connect(self._prune_plugs)

            menu.addSeparator()
            new_pipeline = menu.addAction("New pipeline (clear current)")
            new_pipeline.triggered.connect(self.new_pipeline)
            load_pipeline = menu.addAction("Load pipeline (clear current)")
            load_pipeline.triggered.connect(self.load_pipeline)
            save_parameters = menu.addAction("Save pipeline parameters")
            save_parameters.triggered.connect(self.save_pipeline_parameters)
            load_parameters = menu.addAction("Load pipeline parameters")
            load_parameters.triggered.connect(self.load_pipeline_parameters)

        menu.addSeparator()
        save = menu.addAction("Save pipeline")
        save.triggered.connect(self.save_pipeline)

        menu.exec_(QtGui.QCursor.pos())
        del self.click_pos

    def enableNode(self, checked):
        if self.current_node_name in ["inputs", "outputs"]:
            node_name = ""
        else:
            node_name = self.current_node_name
        self.scene.pipeline.nodes[node_name].enabled = checked

    def enable_step(self, step_name, state):
        setattr(self.scene.pipeline.pipeline_steps, step_name, state)

    def disable_preceding_steps(self, step_name, dummy):
        # don't know why we get this additional dummy parameter (False)
        steps = self.scene.pipeline.pipeline_steps
        for field in steps.fields():
            step = field.name
            if step == step_name:
                break
            setattr(steps, step, False)

    def disable_following_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        found = False
        for field in steps.fields():
            step = field.name
            if found:
                setattr(steps, step, False)
            elif step == step_name:
                found = True

    def enable_preceding_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        for field in steps.fields():
            step = field.name
            if step == step_name:
                break
            setattr(steps, step, True)

    def enable_following_steps(self, step_name, dummy):
        steps = self.scene.pipeline.pipeline_steps
        found = False
        for field in steps.fields():
            step = field.name
            if found:
                setattr(steps, step, True)
            elif step == step_name:
                found = True

    def set_switch_value(self, switch, value, dummy):
        switch.switch = value

    def disable_done_steps(self):
        pipeline_tools.disable_runtime_steps_with_existing_outputs(self.scene.pipeline)

    def enable_all_steps(self):
        self.scene.pipeline.enable_all_pipeline_steps()

    def check_files(self):
        overwritten_outputs = pipeline_tools.nodes_with_existing_outputs(
            self.scene.pipeline
        )
        missing_inputs = pipeline_tools.nodes_with_missing_inputs(self.scene.pipeline)
        if len(overwritten_outputs) == 0 and len(missing_inputs) == 0:
            QtGui.QMessageBox.information(
                self,
                "Pipeline ready",
                "All input files are available. " "No output file will be overwritten.",
            )
        else:
            dialog = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(dialog)
            warn_widget = PipelineFileWarningWidget(missing_inputs, overwritten_outputs)
            layout.addWidget(warn_widget)
            hlay = QtGui.QHBoxLayout()
            layout.addLayout(hlay)
            hlay.addStretch()
            ok = QtGui.QPushButton("OK")
            self.ok_button = ok
            hlay.addWidget(ok)
            ok.clicked.connect(dialog.close)
            dialog.show()
            self._warn_files_widget = dialog

    def auto_dot_node_positions(self):
        """
        Calculate pipeline nodes positions using graphviz/dot, and place the
        pipeline view nodes accordingly.
        """
        scene = self.scene
        scale = 67.0  # dpi
        nodes_sizes = dict(
            [
                (name, (gnode.boundingRect().width(), gnode.boundingRect().height()))
                for name, gnode in scene.gnodes.items()
            ]
        )
        dgraph = pipeline_tools.dot_graph_from_pipeline(
            scene.pipeline, nodes_sizes=nodes_sizes
        )
        tfile, tfile_name = tempfile.mkstemp()
        os.close(tfile)
        pipeline_tools.save_dot_graph(dgraph, tfile_name)
        toutfile, toutfile_name = tempfile.mkstemp()
        os.close(toutfile)
        try:
            cmd = ["dot", "-Tplain", "-o", toutfile_name, tfile_name]
            try:
                soma.subprocess.check_call(cmd)
            except FileNotFoundError:
                # dot is not installed in the PATH. Give up
                return

            nodes_pos = self._read_dot_pos(toutfile_name)

            rects = dict(
                [(name, node.boundingRect()) for name, node in scene.gnodes.items()]
            )
            pos = dict(
                [
                    (
                        name,
                        (
                            -rects[name].width() / 2 + pos[0] * scale,
                            -rects[name].height() / 2 - pos[1] * scale,
                        ),
                    )
                    for id, name, pos in nodes_pos
                ]
            )
            minx = min([x[0] for x in pos.values()])
            miny = min([x[1] for x in pos.values()])
            pos = dict([(name, (p[0] - minx, p[1] - miny)) for name, p in pos.items()])
            #         print('pos:')
            #         print(pos)
            scene.pos = pos
            for node, position in pos.items():
                gnode = scene.gnodes[node]
                if isinstance(position, Qt.QPointF):
                    gnode.setPos(position)
                else:
                    gnode.setPos(*position)

        finally:
            os.unlink(tfile_name)
            os.unlink(toutfile_name)

    def _read_dot_pos(self, filename):
        """
        Read the nodes positions from a file generated by graphviz/dot, in
        "plain" text format.

        Returns
        -------
        nodes_pos: dict
            keys are nodes IDs (names), and values are 2D positions
        """
        fileobj = open(filename)
        nodes_pos = []
        if sys.version_info[0] >= 3:
            file_iter = fileobj.readlines()
        else:
            file_iter = fileobj
        for line in file_iter:
            if line.startswith("node"):
                line_els0 = line.split()
                line_els = []
                for el in line_els0:
                    if el.startswith('"') and el.endswith('"'):
                        line_els.append(el[1:-1])
                    else:
                        line_els.append(el)
                id = line_els[1]
                pos = tuple([float(x) for x in line_els[2:4]])
                name = line_els[6]
                nodes_pos.append((id, name, pos))
            elif line.startswith("edge"):
                break
        return nodes_pos

    def save_dot_image_ui(self):
        """
        Ask for a filename using the file dialog, and save a graphviz/dot
        representation of the pipeline.
        The pipeline representation follows the current visualization mode
        ("regular" or "logical" with smaller boxes) with one link of a given
        type (active, weak) between two given boxes: all parameters are not
        represented.
        """
        file_dialog = QtGui.QFileDialog(
            filter="Images (*.png *.xpm *.jpg *.ps *.eps);; All (*)"
        )
        file_dialog.setDefaultSuffix(".png")
        file_dialog.setFileMode(QtGui.QFileDialog.AnyFile)
        file_dialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
        if file_dialog.exec_():
            filename = file_dialog.selectedFiles()

        """filename = QtGui.QFileDialog.getSaveFileName(
            None, 'Save image of the pipeline', '',
            'Images (*.png *.xpm *.jpg *.ps *.eps);; All (*)')"""
        if filename:
            pipeline_tools.save_dot_image(self.scene.pipeline, filename[0])

    def reset_initial_nodes_positions(self):
        """
        Set each pipeline node to its "saved" position, ie the one which may
        be found in the "node_position" variable of the pipeline.
        """
        scene = self.scene
        if scene.pipeline is None:
            return

        #         ############## add by Irmage OM ###################
        #         dim = getattr(scene.pipeline, 'node_dimension')
        #         if dim is not None:
        #             scene.dim = dim
        #             print()
        #             for node, dimension in dim.items():
        #                 gnode = scene.gnodes.get(node)
        #                 if gnode is not None:
        #                     if isinstance(dimension, QtCore.QPointF):
        #                         dimension = (dim.x(),dim.y())
        # #                     else:
        # #                         dimension = dim.width(),dim.height()
        #                     gnode.update(0,0,*dimension)
        #         #####################################################

        pos = scene.pipeline.node_position
        if pos is not None:
            scene.pos = pos
            for node, position in pos.items():
                gnode = scene.gnodes.get(node)
                if gnode is not None:
                    if isinstance(position, QtCore.QPointF):
                        position = (position.x(), position.y())
                    gnode.setPos(*position)

    def switch_logical_view(self):
        self.set_logical_view(not self.is_logical_view())

    def print_node_positions(self):
        def conv_pos(p):
            if isinstance(p, Qt.QPointF):
                return (p.x(), p.y())
            return p

        posdict = dict(
            [(key, conv_pos(value)) for key, value in self.scene.pos.items()]
        )
        pprint(posdict)

    def del_node(self, node_name=None):
        pipeline = self.scene.pipeline

        if not node_name:
            node_name = self.current_node_name
        if node_name not in ("inputs", "outputs"):
            node = pipeline.nodes[node_name]
            pipeline.remove_node(node_name)
        elif node_name in self.scene.gnodes:
            # delete all input or output export plugs in the pipeline
            if node_name == "inputs":
                plugs = [
                    name
                    for name, plug in pipeline.pipeline_node.plugs.items()
                    if not plug.output
                ]
            else:
                plugs = [
                    name
                    for name, plug in pipeline.pipeline_node.plugs.items()
                    if plug.output
                ]
            for plug in plugs:
                self.scene.pipeline.remove_field(plug)

        self.scene.pipeline.update_nodes_and_plugs_activation()

    def export_node_plugs(self, node_name, inputs=True, outputs=True, optional=False):
        pipeline = self.scene.pipeline
        node = pipeline.nodes[node_name]
        for parameter_name, plug in node.plugs.items():
            if parameter_name in ("nodes_activation", "selection_changed"):
                continue
            if (
                (node_name, parameter_name) not in pipeline.do_not_export
                and (
                    (outputs and plug.output and not plug.links_to)
                    or (inputs and not plug.output and not plug.links_from)
                )
                and (
                    optional
                    or not node.field(parameter_name).metadata("optional", False)
                )
            ):
                pipeline.export_parameter(node_name, parameter_name)

    def export_plugs(self, inputs=True, outputs=True, optional=False):
        for node_name in self.scene.pipeline.nodes:
            if node_name != "":
                self.export_node_plugs(
                    node_name, inputs=inputs, outputs=outputs, optional=optional
                )

    def export_node_unconnected_mandatory_plugs(self):
        self.export_node_plugs(self.current_node_name)

    def export_node_all_unconnected_plugs(self):
        self.export_node_plugs(self.current_node_name, optional=True)

    def export_node_unconnected_mandatory_inputs(self):
        self.export_node_plugs(self.current_node_name, inputs=True, outputs=False)

    def export_node_all_unconnected_inputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=True, outputs=False, optional=True
        )

    def export_node_unconnected_mandatory_outputs(self):
        self.export_node_plugs(self.current_node_name, inputs=False, outputs=True)

    def export_node_all_unconnected_outputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=False, outputs=True, optional=True
        )

    def export_unconnected_mandatory_plugs(self):
        self.export_plugs()

    def export_all_unconnected_plugs(self):
        self.export_plugs(optional=True)

    def export_unconnected_mandatory_inputs(self):
        self.export_plugs(inputs=True, outputs=False)

    def export_all_unconnected_inputs(self):
        self.export_plugs(inputs=True, outputs=False, optional=True)

    def export_unconnected_mandatory_outputs(self):
        self.export_plugs(inputs=False, outputs=True)

    def export_all_unconnected_outputs(self):
        self.export_plugs(inputs=False, outputs=True, optional=True)

    def _change_step(self):
        node_name = self.current_node_name
        node = self.scene.pipeline.nodes[node_name]
        steps = getattr(self.scene.pipeline, "pipeline_steps", None)
        steps_defined = True
        if steps is None:
            steps = Controller()
            steps_defined = False

        wid = Qt.QDialog()
        wid.setModal(True)
        lay = Qt.QVBoxLayout()
        wid.setLayout(lay)

        listw = Qt.QListWidget()
        listw.setSelectionMode(listw.MultiSelection)
        lay.addWidget(listw)
        n = 0
        for field in steps.fields():
            step = field.name
            listw.addItem(step)
            nodes = step.metadata("nodes", set())
            if node_name in nodes:
                item = listw.item(n)
                item.setSelected(True)
            n += 1
        addlay = Qt.QHBoxLayout()
        lay.addLayout(addlay)
        addb = Qt.QPushButton("+")
        addlay.addWidget(addb)
        remb = Qt.QPushButton("-")
        addlay.addWidget(remb)

        def add_clicked():
            d = Qt.QDialog()
            d.setModal(True)
            la = Qt.QHBoxLayout()
            d.setLayout(la)
            l = Qt.QLineEdit()
            la.addWidget(l)
            l.returnPressed.connect(d.accept)
            r = d.exec_()
            if r:
                name = l.text()
                if steps.field(name) is None:
                    n = listw.count()
                    listw.addItem(name)
                    listw.item(n).setSelected(True)

        def remove_clicked():
            selected = []
            for i in range(listw.count()):
                item = listw.item(i)
                if item.isSelected():
                    selected.append((i, item.text()))
            if len(selected) != 0:
                r = Qt.QMessageBox.question(
                    wid,
                    "remove steps",
                    "remove the following steps from the whole pipeline ?\n%s"
                    % repr([s[1] for s in selected]),
                )
                if r == Qt.QMessageBox.Yes:
                    for s in reversed(selected):
                        listw.takeItem(s[0])

        def up_clicked():
            selected = []
            for i in range(listw.count()):
                item = listw.item(i)
                if item.isSelected():
                    selected.append(i)
            if len(selected) != 0 and selected[0] != 0:
                for i in selected:
                    item = listw.takeItem(i)
                    listw.insertItem(i - 1, item)
                    item.setSelected(True)

        def down_clicked():
            selected = []
            for i in range(listw.count()):
                item = listw.item(i)
                if item.isSelected():
                    selected.append(i)
            if len(selected) != 0 and selected[-1] != listw.count() - 1:
                for i in reversed(selected):
                    item = listw.takeItem(i)
                    listw.insertItem(i + 1, item)
                    item.setSelected(True)

        addb.clicked.connect(add_clicked)
        remb.clicked.connect(remove_clicked)
        up = Qt.QPushButton("^")
        addlay.addWidget(up)
        down = Qt.QPushButton("v")
        addlay.addWidget(down)
        up.clicked.connect(up_clicked)
        down.clicked.connect(down_clicked)

        oklay = Qt.QHBoxLayout()
        lay.addLayout(oklay)
        ok = Qt.QPushButton("OK")
        oklay.addWidget(ok)
        cancel = Qt.QPushButton("Cancel")
        oklay.addWidget(cancel)
        ok.clicked.connect(wid.accept)
        cancel.clicked.connect(wid.reject)

        res = wid.exec_()
        if res:
            items = set()
            sitems = []
            for i in range(listw.count()):
                item = listw.item(i)
                name = item.text()
                sel = item.isSelected()
                items.add(name)
                sitems.append(name)
                field = steps.field(name)
                if sel:
                    if field is None:
                        self.scene.pipeline.add_pipeline_step(name, [node_name])
                        steps = self.scene.pipeline.pipeline_steps
                    else:
                        nodes = field.metadata("nodes")
                        if node_name not in nodes:
                            nodes.append(node_name)
                elif field is not None:
                    if node_name in field.metadata("nodes"):
                        field.metadata("nodes").remove(node_name)
            steps = [field.name for field in steps.fields()]
            for step in steps:
                if step not in items:
                    self.scene.pipeline.remove_pipeline_step(step)
            # reorder fields if needed
            steps = self.scene.pipeline.pipeline_steps
            if [field.name for field in steps.fields()] != sitems:
                values = [step.metadata("nodes") for step in sitems]
                for step in sitems:
                    steps.remove_field(step)
                for step, nodes in zip(sitems, values):
                    self.scene.pipeline.add_pipeline_step(step, nodes)

            self.scene.update_pipeline()

    class ProcessModuleInput(QtGui.QDialog):
        def __init__(
            self, display_str="process module/name", class_type_check=is_executable
        ):
            super().__init__()
            self.setWindowTitle("%s:" % display_str)
            layout = QtGui.QGridLayout(self)
            layout.addWidget(QtGui.QLabel("module/process:"), 0, 0)
            self.proc_line = PipelineDeveloperView.ProcessNameEdit(
                class_type_check=class_type_check
            )
            layout.addWidget(self.proc_line, 0, 1)
            layout.addWidget(QtGui.QLabel("node name"), 1, 0)
            self.name_line = QtGui.QLineEdit()
            layout.addWidget(self.name_line, 1, 1)
            # hlay = QtGui.QHBoxLayout()
            # layout.addLayout(hlay, 1, 1)
            ok = QtGui.QPushButton("OK")
            layout.addWidget(ok, 2, 0)
            cancel = QtGui.QPushButton("Cancel")
            layout.addWidget(cancel, 2, 1)
            ok.clicked.connect(self.accept)
            cancel.clicked.connect(self.reject)

    def add_process(self):
        """
        Insert a process node in the pipeline. Asks for the process
        module/name, and the node name before inserting.
        """

        proc_name_gui = PipelineDeveloperView.ProcessModuleInput()
        proc_name_gui.resize(800, proc_name_gui.sizeHint().height())

        res = proc_name_gui.exec_()
        if res:
            proc_module = str(proc_name_gui.proc_line.text())
            node_name = str(proc_name_gui.name_line.text())
            self.add_named_process(proc_module, node_name)

    def add_named_process(self, proc_module, node_name=None):
        pipeline = self.scene.pipeline

        if not node_name:
            if isinstance(proc_module, str):
                class_name = proc_module
            else:
                class_name = proc_module.__name__
            i = 1
            node_name = "%s_%d" % (class_name.lower(), i)

            while node_name in pipeline.nodes and i < 100:
                i += 1
                node_name = "%s_%d" % (class_name.lower(), i)

        capsul = getattr(pipeline, "capsul", None)
        if capsul is None:
            capsul = getattr(self, "capsul", None)
            if capsul is None:
                capsul = Capsul()
                self.capsul = capsul
        try:
            process = capsul.executable(proc_module)
        except Exception as e:
            traceback.print_exc()
            return
        pipeline.add_process(node_name, process)

        node = pipeline.nodes[node_name]
        gnode = self.scene.add_node(node_name, node)
        gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

        return process

    def add_node(self):
        """
        Insert a custom node in the pipeline. Asks for the node
        module/name, and the node name before inserting.
        """

        def is_pipeline_node(item):
            return item is not Node and isinstance(item, Node)

        node_name_gui = PipelineDeveloperView.ProcessModuleInput(
            display_str="node module/name", class_type_check=is_pipeline_node
        )
        node_name_gui.resize(800, node_name_gui.sizeHint().height())

        res = node_name_gui.exec_()
        if res:
            node_module = str(node_name_gui.proc_line.text())
            node_name = str(node_name_gui.name_line.text())
            self.add_named_node(node_name, node_module)

    def add_named_node(self, node_name, node_module):
        def configure_node(cls):
            conf_controller = cls.configure_controller()
            w = Qt.QDialog()
            w.setWindowTitle("Custom node parameterization")
            l = Qt.QVBoxLayout()
            w.setLayout(l)
            c = ControllerWidget(conf_controller)
            l.addWidget(c)
            h = Qt.QHBoxLayout()
            l.addLayout(h)
            ok = Qt.QPushButton("OK")
            h.addWidget(ok)
            cancel = Qt.QPushButton("Cancel")
            h.addWidget(cancel)
            ok.clicked.connect(w.accept)
            cancel.clicked.connect(w.reject)
            res = w.exec_()
            if res:
                return conf_controller
            else:
                return None

        def get_node_instance(class_str, pipeline):
            cls_and_name = get_node_class(class_str)
            if cls_and_name is None:
                return None
            name, cls = cls_and_name
            if hasattr(cls, "configure_controller"):
                conf_controller = configure_node(cls)
                if conf_controller is None:
                    return None  # abort
            else:
                conf_controller = Controller()
            if hasattr(cls, "build_node"):
                node = cls.build_node(pipeline, name, conf_controller)
            else:
                # probably bound to fail...
                node = cls(pipeline, name, [], [])
            return node

        pipeline = self.scene.pipeline
        try:
            node = get_node_instance(node_module, pipeline)
        except Exception as e:
            print(e)
            traceback.print_exc()
            return
        if node is None:
            return

        if not node_name and node:
            class_name = node.__class__.__name__
            i = 1
            node_name = class_name.lower() + str(i)

            while node_name in pipeline.nodes and i < 100:
                i += 1
                node_name = class_name.lower() + str(i)

        pipeline.nodes[node_name] = node

        gnode = self.scene.add_node(node_name, node)
        gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    class IterativeProcessInput(ProcessModuleInput):
        def __init__(self, engine):
            super().__init__()
            # hlay = Qt.QHBoxLayout()
            # self.layout().addLayout(hlay)
            lay = self.layout()
            item = lay.itemAtPosition(2, 0)
            widget = item.widget()
            lay.removeItem(item)
            lay.addWidget(widget, 3, 0)
            item = lay.itemAtPosition(2, 1)
            widget = item.widget()
            lay.removeItem(item)
            lay.addWidget(widget, 3, 1)
            lay.addWidget(Qt.QLabel("iterative plugs:"), 2, 0)
            self.plugs = Qt.QListWidget()
            self.plugs.setEditTriggers(Qt.QListWidget.NoEditTriggers)
            self.plugs.setSelectionMode(Qt.QListWidget.ExtendedSelection)
            lay.addWidget(self.plugs, 2, 1)
            self.proc_line.textChanged.connect(self.set_plugs)
            # self.proc_line.editingFinished.connect(self.set_plugs)
            self.engine = engine

        def set_plugs(self, text):
            self.plugs.clear()
            try:
                process = executable(text)
            except Exception:
                return
            fields = [field.name for field in process.fields()]
            self.plugs.addItems(fields)

        def iterative_plugs(self):
            return [item.text() for item in self.plugs.selectedItems()]

    def add_iterative_process(self):
        """
        Insert an iterative process node in the pipeline. Asks for the process
        module/name, the node name, and iterative plugs before inserting.
        """
        pipeline = self.scene.pipeline
        # engine = pipeline.get_capsul_engine()
        engine = None
        proc_name_gui = PipelineDeveloperView.IterativeProcessInput(engine)
        proc_name_gui.resize(800, proc_name_gui.sizeHint().height())

        res = proc_name_gui.exec_()
        if res:
            proc_module = str(proc_name_gui.proc_line.text())
            node_name = str(proc_name_gui.name_line.text())
            try:
                process = executable(str(proc_name_gui.proc_line.text()))
            except Exception as e:
                print(e)
                return
            iterative_plugs = proc_name_gui.iterative_plugs()
            do_not_export = [field.name for field in process.fields()]
            pipeline.add_iterative_process(
                node_name, process, iterative_plugs, do_not_export=do_not_export
            )

            node = pipeline.nodes[node_name]
            gnode = self.scene.add_node(node_name, node)
            gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    def add_switch(self):
        """
        Insert a switch node in the pipeline. Asks for the switch
        inputs/outputs, and the node name before inserting.
        """

        class SwitchInput(QtGui.QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("switch parameters/name:")
                layout = QtGui.QGridLayout(self)
                layout.addWidget(QtGui.QLabel("inputs:"), 0, 0)
                self.inputs_line = QtGui.QLineEdit()
                layout.addWidget(self.inputs_line, 0, 1)
                layout.addWidget(QtGui.QLabel("outputs:"), 1, 0)
                self.outputs_line = QtGui.QLineEdit()
                layout.addWidget(self.outputs_line, 1, 1)
                layout.addWidget(QtGui.QLabel("node name"), 2, 0)
                self.name_line = QtGui.QLineEdit()
                layout.addWidget(self.name_line, 2, 1)
                ok = QtGui.QPushButton("OK")
                layout.addWidget(ok, 3, 0)
                cancel = QtGui.QPushButton("Cancel")
                layout.addWidget(cancel, 3, 1)
                ok.clicked.connect(self.accept)
                cancel.clicked.connect(self.reject)

        switch_name_gui = SwitchInput()
        switch_name_gui.resize(600, switch_name_gui.sizeHint().height())

        res = switch_name_gui.exec_()
        if res:
            pipeline = self.scene.pipeline
            node_name = str(switch_name_gui.name_line.text()).strip()
            inputs = str(switch_name_gui.inputs_line.text()).split()
            outputs = str(switch_name_gui.outputs_line.text()).split()
            pipeline.add_switch(node_name, inputs, outputs)
            # add_switch triggers an update
            gnode = self.scene.gnodes[node_name]
            gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    # def add_optional_output_switch(self):
    #     '''
    #     Insert an optional output switch node in the pipeline. Asks for the
    #     switch inputs/outputs, and the node name before inserting.
    #     '''

    #     class SwitchInput(QtGui.QDialog):
    #         def __init__(self):
    #             super().__init__()
    #             self.setWindowTitle('switch parameters/name:')
    #             layout = QtGui.QGridLayout(self)
    #             layout.addWidget(QtGui.QLabel('input:'), 0, 0)
    #             self.inputs_line = QtGui.QLineEdit()
    #             layout.addWidget(self.inputs_line, 0, 1)
    #             layout.addWidget(QtGui.QLabel('output:'), 1, 0)
    #             self.outputs_line = QtGui.QLineEdit()
    #             layout.addWidget(self.outputs_line, 1, 1)
    #             layout.addWidget(QtGui.QLabel('node name'), 2, 0)
    #             self.name_line = QtGui.QLineEdit()
    #             layout.addWidget(self.name_line, 2, 1)
    #             ok = QtGui.QPushButton('OK')
    #             layout.addWidget(ok, 3, 0)
    #             cancel = QtGui.QPushButton('Cancel')
    #             layout.addWidget(cancel, 3, 1)
    #             ok.clicked.connect(self.accept)
    #             cancel.clicked.connect(self.reject)

    #     switch_name_gui = SwitchInput()
    #     switch_name_gui.resize(600, switch_name_gui.sizeHint().height())

    #     res = switch_name_gui.exec_()
    #     if res:
    #         pipeline = self.scene.pipeline
    #         node_name = str(switch_name_gui.name_line.text()).strip()
    #         input = str(switch_name_gui.inputs_line.text()).strip()
    #         output = str(switch_name_gui.outputs_line.text()).strip()
    #         if output == '' and node_name != '':
    #             output = node_name
    #         elif output != '' and node_name == '':
    #             node_name = output
    #         pipeline.add_optional_output_switch(node_name, input, output)
    #         # add_optional_output_switch does *not* trigger an update
    #         self._reset_pipeline()
    #         gnode = self.scene.gnodes[node_name]
    #         gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    def _plug_clicked(self, name):
        if self.is_logical_view() or not self.edition_enabled():
            # in logival view, links are not editable since they do not reflect
            # the details of reality
            return
        node_name, plug_name = str(name).split(":")
        plug_name = str(plug_name)
        gnode = self.scene.gnodes[node_name]
        plug = gnode.out_plugs.get(plug_name)

        typeq = self.scene.typeLink(node_name, plug_name)
        try:
            #             color = self.scene.colorLink(typeq)
            color = self.scene.colType.colorLink(typeq)

        except Exception:
            color = ORANGE_2
        if not plug:
            return  # probably an input plug
        plug_pos = plug.mapToScene(plug.mapFromParent(plug.get_plug_point()))
        self._grabpos = self.mapFromScene(plug_pos)
        self._temp_link = Link(
            plug_pos,
            self.mapToScene(self.mapFromGlobal(QtGui.QCursor.pos())),
            True,
            False,
            color,
        )
        self._temp_link.pen.setBrush(RED_2)
        self.scene.addItem(self._temp_link)

        self._grab_link = True
        self._grabbed_plug = (node_name, plug_name)

    def _move_grab_link(self, event):
        pos = self.mapToScene(event.pos())
        self._temp_link.update(self.mapToScene(self._grabpos), pos)

    def _release_grab_link(self, event, ret=False):
        max_square_dist = 100.0
        self._grab_link = False
        # delete the temp link
        self.scene.removeItem(self._temp_link)
        del self._temp_link
        pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(pos, Qt.QTransform())
        plug = None
        if isinstance(item, Link):
            # look for its dest plug
            plug = None
            for source_dest, link in self.scene.glinks.items():
                if link is item:
                    plug = source_dest[1]
                    break
            if plug is not None:
                # check the plug is not too far from the drop point
                gnode = self.scene.gnodes[plug[0]]
                gplug = gnode.in_plugs[plug[1]]
                plug_pos = gplug.mapToScene(gplug.mapFromParent(gplug.get_plug_point()))
                pdiff = plug_pos - pos
                dist2 = pdiff.x() * pdiff.x() + pdiff.y() * pdiff.y()
                if dist2 > max_square_dist:
                    plug = None
        elif isinstance(item, Plug):
            plug = str(item.name).split(":")
        if plug is not None:
            if self._grabbed_plug[0] not in ("", "inputs"):
                src = "%s.%s" % self._grabbed_plug
            else:
                src = self._grabbed_plug[1]
            if plug[0] not in ("", "outputs"):
                dst = "%s.%s" % tuple(plug)
            else:
                dst = plug[1]
            #             if (src != dst) and ("inputs."+src != dst) and not self.isInputYet(dst) :

            if (src != dst) and ("inputs." + src != dst):
                self.scene.pipeline.add_link("%s->%s" % (src, dst))
                self.scene.update_pipeline()

            if ret:
                self._grabbed_plug = None
                return "%s->%s" % (src, dst)
        self._grabbed_plug = None

    #     def isInputYet(self,dest):##################################################################### add by OM
    #         for listK in self.scene.glinks.keys():
    #             if ( eval(str(eval(str(listK))[1]))[0]+"."+ eval(str(eval(str(listK))[1]))[1]==dest or eval(str(eval(str(listK))[1]))[0]+"."+ eval(str(eval(str(listK))[1]))[1]=="outputs."+dest):
    #                 print("input '",dest, "' already used !!")
    #                 return True
    #         return False

    def _node_delete_clicked(self, name_node):
        self.current_node_name = name_node
        self.del_node()

    def _link_delete_clicked(self, src_node, src_plug, dst_node, dst_plug):
        src_node = str(src_node)
        src_plug = str(src_plug)
        dst_node = str(dst_node)
        dst_plug = str(dst_plug)

        #         print(src_node,",",src_plug,",",dst_node,",",dst_plug)

        if self.is_logical_view() or not self.edition_enabled():
            # in logical view, links are not real links
            return
        if src_node in ("", "inputs"):
            src = src_plug
            snode = self.scene.pipeline
        else:
            src = "%s.%s" % (src_node, src_plug)
            snode = self.scene.pipeline.nodes[src_node]
        if dst_node in ("", "outputs"):
            dst = dst_plug
            dnode = self.scene.pipeline
        else:
            dst = "%s.%s" % (dst_node, dst_plug)
            dnode = self.scene.pipeline.nodes[dst_node]
        name = "%s->%s" % (src, dst)
        self._current_link = name  # (src_node, src_plug, dst_node, dst_plug)
        self._del_link()
        del self._current_link

    def _link_clicked(self, src_node, src_plug, dst_node, dst_plug):
        src_node = str(src_node)
        src_plug = str(src_plug)
        dst_node = str(dst_node)
        dst_plug = str(dst_plug)
        if self.is_logical_view() or not self.edition_enabled():
            # in logical view, links are not real links
            return
        if src_node in ("", "inputs"):
            src = src_plug
            snode = self.scene.pipeline
        else:
            src = "%s.%s" % (src_node, src_plug)
            snode = self.scene.pipeline.nodes[src_node]
        if dst_node in ("", "outputs"):
            dst = dst_plug
            dnode = self.scene.pipeline
        else:
            dst = "%s.%s" % (dst_node, dst_plug)
            dnode = self.scene.pipeline.nodes[dst_node]
        name = "%s->%s" % (src, dst)
        self._current_link = name  # (src_node, src_plug, dst_node, dst_plug)
        self._current_link_def = (src_node, src_plug, dst_node, dst_plug)

        menu = QtGui.QMenu("Link: %s" % name)
        title = menu.addAction("Link: %s" % name)
        title.setEnabled(False)
        menu.addSeparator()

        weak = False
        splug = snode.plugs[src_plug]
        for link in splug.links_to:
            if link[0] == dst_node and link[1] == dst_plug:
                weak = link[4]
                break
        weak_action = menu.addAction("Weak link")
        weak_action.setCheckable(True)
        weak_action.setChecked(bool(weak))
        weak_action.toggled.connect(self._change_weak_link)

        menu.addSeparator()
        del_link = menu.addAction("Delete link")
        del_link.triggered.connect(self._del_link)

        menu.exec_(QtGui.QCursor.pos())
        del self._current_link
        del self._current_link_def

    def get_doc_browser(self, create=False):
        doc_browser = self.doc_browser
        pv = self
        proxy = False
        while isinstance(doc_browser, PipelineDeveloperView):
            # it's a proxy to a parent view
            pv = doc_browser
            doc_browser = pv.doc_browser
            proxy = True
        if doc_browser or not create:
            return doc_browser
        try:
            # use the newer Qt5 QtWebEngine
            from soma.qt_gui.qt_backend import QtWebEngine
            from soma.qt_gui.qt_backend.QtWebEngineWidgets import (
                QWebEnginePage,
                QWebEngineView,
            )

            use_webengine = True
        except ImportError:
            from soma.qt_gui.qt_backend import QtWebKit

            QWebEngineView = QtWebKit.QWebView
            QWebPage = QtWebKit.QWebPage
            QWebEnginePage = QWebPage
            use_webengine = False
        self._use_webengine = use_webengine

        class DocBrowser(QWebEngineView):
            def __init__(self, pview, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.setAttribute(Qt.Qt.WA_DeleteOnClose)
                self.pview = pview

            def closeEvent(self, event):
                self.pview.doc_browser = None
                event.accept()
                super().closeEvent(event)

        doc_browser = DocBrowser(pv)  # QWebEngineView()
        pv.doc_browser = doc_browser
        doc_browser.show()

        return doc_browser

    def _node_clicked(self, name, node):
        self.show_node_doc(node)
        if isinstance(node, Process):
            self.process_clicked.emit(name, node)
        else:
            self.node_clicked.emit(name, node)

    @staticmethod
    def get_node_html_doc(node):
        doc_path = getattr(node, "_doc_path", None)
        if doc_path and os.path.isabs(doc_path):
            return doc_path
        modname = node.__module__
        init_modname = modname
        while True:
            mod = sys.modules[modname]
            mod_doc_path = getattr(mod, "_doc_path", None)
            if mod_doc_path:
                if doc_path:
                    return os.path.join(mod_doc_path, doc_path)
                node_type = "process"
                if isinstance(node, Pipeline):
                    node_type = "pipeline"
                path = os.path.join(
                    mod_doc_path,
                    node_type,
                    "%s.html" % ".".join((node.__module__, node.__class__.__name__)),
                )
                if (
                    os.path.exists(path)
                    or path.startswith("http://")
                    or path.startswith("https://")
                ):
                    return path
                # try using the 1st sub-module
                modsplit = init_modname.split(".")
                if len(modsplit) >= 3:
                    path = os.path.join(
                        mod_doc_path,
                        modsplit[1],
                        node_type,
                        "%s.html"
                        % ".".join((node.__module__, node.__class__.__name__)),
                    )
                    if (
                        os.path.exists(path)
                        or path.startswith("http://")
                        or path.startswith("https://")
                    ):
                        return path
                return None
            s = modname.rsplit(".", 1)
            if len(s) == 1:
                break
            modname = s[0]

    def show_doc(self, node_name=None):
        pipeline = self.scene.pipeline
        if not node_name:
            node_name = self.current_node_name
        if node_name in ("inputs", "outputs"):
            node = pipeline
        else:
            node = pipeline.nodes[node_name]
        doc_browser = self.get_doc_browser(create=True)
        self.show_node_doc(node)

    def show_node_doc(self, node):
        doc_browser = self.get_doc_browser()
        if doc_browser:
            doc_path = self.get_node_html_doc(node)
            if doc_path:
                if (
                    not doc_path.startswith("http://")
                    and not doc_path.startswith("https://")
                    and not doc_path.startswith("file://")
                ):
                    doc_path = "file://%s" % os.path.abspath(doc_path)
                doc_browser.setUrl(Qt.QUrl(doc_path))
            else:
                gethelp = node.get_help
                msg = None
                if gethelp:
                    msg = node.get_help(returnhelp=True)
                if not msg:
                    msg = node.getattr(node, "__doc__", None)
                if msg:
                    doc_browser.setContent(
                        Qt.QByteArray(msg.encode("utf-8")), "text/plain"
                    )

    def _node_clicked_ctrl(self, name, process):
        for source_dest, glink in self.scene.glinks.items():
            glink.fonced_viewer(False)
            #             print("source-dest ",source_dest)
            if name not in str(source_dest):
                glink.fonced_viewer(True)
        #             else:
        #                 print(source_dest[0])
        for node_name, gnode in self.scene.gnodes.items():
            #             print("    node_name",node_name)
            gnode.fonced_viewer(False)
            if name not in str(node_name):
                gnode.fonced_viewer(True)

    def _change_weak_link(self, weak):
        # src_node, src_plug, dst_node, dst_plug = self._current_link
        link_def = self._current_link
        self.scene.pipeline.remove_link(link_def)
        self.scene.pipeline.add_link(link_def, weak_link=weak)
        self.scene.update_pipeline()

    def _del_link(self):
        print("\nRemoving the link: ", self._current_link)
        src_node, src_plug, dst_node, dst_plug = self._current_link_def
        link_def = self._current_link
        pipeline = self.scene.pipeline
        pipeline.remove_link(link_def)
        if src_node in ("", "inputs") and len(pipeline.plugs[src_plug].links_to) == 0:
            # remove orphan pipeline plug
            pipeline.remove_field(src_plug)
        elif (
            dst_node in ("", "outputs")
            and len(pipeline.plugs[dst_plug].links_from) == 0
        ):
            # remove orphan pipeline plug
            pipeline.remove_field(dst_plug)
        self.scene.update_pipeline()

    def _plug_right_clicked(self, name):
        for node_name, gnode in self.scene.gnodes.items():
            if node_name in "inputs":
                self.inputYet = True
            if node_name in "outputs":
                self.outputYet = False

        if self.is_logical_view() or not self.edition_enabled():
            # in logival view, links are not editable since they do not reflect
            # the details of reality
            return
        node_name, plug_name = str(name).split(":")
        plug_name = str(plug_name)
        if node_name in ("inputs", "outputs"):
            node = self.scene.pipeline
        else:
            node = self.scene.pipeline.nodes[node_name]
        plug = node.plugs[plug_name]
        output = plug.output
        self._temp_node = node
        self._temp_plug = plug
        self._temp_plug_name = (node_name, plug_name)

        menu = QtGui.QMenu("Plug: %s" % name)
        title = menu.addAction("Plug: %s" % name)
        title.setEnabled(False)
        menu.addSeparator()

        if node_name not in ("inputs", "outputs"):
            # not a main node: allow export
            if output:
                links = plug.links_to
            else:
                links = plug.links_from
            existing = False
            for link in links:
                if link[0] == "":
                    existing = True
                    break
            export_action = menu.addAction("export plug")
            export_action.triggered.connect(self._export_plug)
            if existing:
                export_action.setEnabled(False)
            if isinstance(node, ProcessIteration):
                iter_action = menu.addAction("iterative plug")
                iter_action.setCheckable(True)
                iter_action.setChecked(plug_name in node.iterative_parameters)
                iter_action.toggled[bool].connect(self._change_iterative_plug)

        else:
            del_plug = menu.addAction("Remove plug")
            del_plug.triggered.connect(self._remove_plug)
            edit_plug = menu.addAction("Rename / edit plug")
            edit_plug.triggered.connect(self._edit_plug)

        protect_action = menu.addAction("protected")
        protect_action.setCheckable(True)
        protect_action.setChecked(node.is_parameter_protected(plug_name))
        protect_action.toggled[bool].connect(self._protect_plug)
        complete_action = menu.addAction("completion enabled")
        complete_action.setCheckable(True)
        complete_action.setChecked(
            not node.field(plug_name).metadata("forbid_completion", False)
        )
        complete_action.toggled[bool].connect(self._enable_plug_completion)

        menu.exec_(QtGui.QCursor.pos())
        del self._temp_plug
        del self._temp_plug_name
        del self._temp_node

    class _PlugEdit(QtGui.QDialog):
        def __init__(self, show_weak=True, parent=None):
            super().__init__(parent)
            layout = QtGui.QVBoxLayout(self)
            hlay1 = QtGui.QHBoxLayout()
            layout.addLayout(hlay1)
            hlay1.addWidget(QtGui.QLabel("Plug name:"))
            self.name_line = QtGui.QLineEdit()
            hlay1.addWidget(self.name_line)
            hlay2 = QtGui.QHBoxLayout()
            layout.addLayout(hlay2)
            self.optional = QtGui.QCheckBox("Optional")
            hlay2.addWidget(self.optional)
            if show_weak:
                self.weak = QtGui.QCheckBox("Weak link")
                hlay2.addWidget(self.weak)
            hlay3 = QtGui.QHBoxLayout()
            layout.addLayout(hlay3)
            ok = QtGui.QPushButton("OK")
            hlay3.addWidget(ok)
            cancel = QtGui.QPushButton("Cancel")
            hlay3.addWidget(cancel)
            ok.clicked.connect(self.accept)
            cancel.clicked.connect(self.reject)

    def _export_plug(self):
        dial = self._PlugEdit()
        dial.name_line.setText(self._temp_plug_name[1])
        dial.optional.setChecked(self._temp_plug.optional)

        res = dial.exec_()
        if res:
            # for node_name, gnode in self.scene.gnodes.items():
            #     print("list Nodes",node_name)
            try:
                self.scene.pipeline.export_parameter(
                    self._temp_plug_name[0],
                    self._temp_plug_name[1],
                    pipeline_parameter=str(dial.name_line.text()),
                    is_optional=dial.optional.isChecked(),
                    weak_link=dial.weak.isChecked(),
                )
            #             print(str(dial.name_line.text()))
            #             self.scene.gnodes.changeHmin(15)
            except Exception as e:
                print("exception while export plug:", e)
                # traceback.print_exc()
                pass

            self.scene.update_pipeline()

    def _change_iterative_plug(self, checked):
        node = self._temp_node
        node_name, name = self._temp_plug_name
        node.change_iterative_plug(name, checked)
        self.scene.update_pipeline()

    def _protect_plug(self, checked):
        node = self._temp_node
        node_name, name = self._temp_plug_name
        node.protect_parameter(name, checked)

    def _enable_plug_completion(self, checked):
        node = self._temp_node
        node_name, name = self._temp_plug_name
        node.field(name).forbid_completion = not checked

    def _remove_plug(self):
        if self._temp_plug_name[0] in ("inputs", "outputs"):
            # print 'remove plug:', self._temp_plug_name[1]
            # print('#' * 50)
            # print(self._temp_plug_name)
            # print(self._temp_plug)

            self.scene.pipeline.remove_field(self._temp_plug_name[1])
            self.scene.update_pipeline()

    def _edit_plug(self):
        dial = self._PlugEdit(show_weak=False)
        dial.name_line.setText(self._temp_plug_name[1])
        dial.name_line.setEnabled(False)  ## FIXME
        dial.optional.setChecked(self._temp_plug.optional)
        res = dial.exec_()
        if res:
            plug = self._temp_plug
            plug.optional = dial.optional.isChecked()

            # print 'TODO.'
            self.scene.update_pipeline()

    def _prune_plugs(self):
        pipeline = self.scene.pipeline
        pnode = pipeline
        to_del = []
        for plug_name, plug in pnode.plugs.items():
            if plug.output and len(plug.links_from) == 0:
                to_del.append(plug_name)
            elif not plug.output and len(plug.links_to) == 0:
                to_del.append(plug_name)
        for plug_name in to_del:
            pipeline.remove_field(plug_name)
        self.scene.update_pipeline()

    def confirm_erase_pipeline(self):
        if len(self.scene.pipeline.nodes) <= 1:
            return True
        confirm = Qt.QMessageBox.warning(
            self,
            "New pipeline",
            "The current pipeline will be lost. Continue ?",
            Qt.QMessageBox.Ok | Qt.QMessageBox.Cancel,
            Qt.QMessageBox.Cancel,
        )
        if confirm != Qt.QMessageBox.Ok:
            return False
        return True

    def new_pipeline(self):
        if not self.confirm_erase_pipeline():
            return
        w = Qt.QDialog(self)
        w.setModal(True)
        w.setWindowTitle("Pipeline name")
        l = Qt.QVBoxLayout()
        w.setLayout(l)
        le = Qt.QLineEdit()
        l.addWidget(le)
        l2 = Qt.QHBoxLayout()
        l.addLayout(l2)
        ok = Qt.QPushButton("OK")
        l2.addWidget(ok)
        cancel = Qt.QPushButton("Cancel")
        l2.addWidget(cancel)
        ok.clicked.connect(w.accept)
        cancel.clicked.connect(w.reject)
        le.returnPressed.connect(w.accept)

        res = w.exec_()
        if res:
            class_kwargs = {
                "__module__": "__main__",
                "do_autoexport_nodes_parameters": False,
                "node_position": {},
                "node_dimension": {},
            }
            name = le.text()
            pipeline_class = type(name, (Pipeline,), class_kwargs)
            pipeline = pipeline_class()
            self.set_pipeline(pipeline)
            self._pipeline_filename = ""

    def load_pipeline(self, filename="", load_pipeline=True):
        class LoadProcessUi(Qt.QDialog):
            def __init__(self, parent=None, old_filename=""):
                super().__init__(parent)
                self.old_filename = old_filename
                lay = Qt.QVBoxLayout()
                self.setLayout(lay)
                l2 = Qt.QHBoxLayout()
                lay.addLayout(l2)
                l2.addWidget(Qt.QLabel("Pipeline:"))
                self.proc_edit = PipelineDeveloperView.ProcessNameEdit()
                l2.addWidget(self.proc_edit)
                self.loadbt = Qt.QPushButton("...")
                l2.addWidget(self.loadbt)
                l3 = Qt.QHBoxLayout()
                lay.addLayout(l3)
                ok = Qt.QPushButton("OK")
                l3.addWidget(ok)
                cancel = Qt.QPushButton("Cancel")
                l3.addWidget(cancel)
                ok.clicked.connect(self.accept)
                cancel.clicked.connect(self.reject)
                self.loadbt.clicked.connect(self.get_filename)
                self.proc_edit.returnPressed.connect(self.accept)

            def get_filename(self):
                filename = qt_backend.getOpenFileName(
                    None,
                    "Load the pipeline",
                    self.old_filename,
                    "Compatible files (*.xml *.py);; All (*)",
                )
                if filename:
                    self.proc_edit.setText(filename)

        if not self.confirm_erase_pipeline():
            return

        if not filename:
            old_filename = getattr(self, "_pipeline_filename", "")
            dialog = LoadProcessUi(self, old_filename=old_filename)
            dialog.setWindowTitle("Load pipeline")
            dialog.setModal(True)
            dialog.resize(800, dialog.sizeHint().height())
            res = dialog.exec_()

            if res:
                filename = dialog.proc_edit.text()

        if filename:
            if not load_pipeline:
                return filename
            else:
                try:
                    pipeline = executable(filename)
                except Exception as e:
                    print(e)
                    pipeline = None
                if pipeline is not None:
                    self.set_pipeline(pipeline)
                    self._pipeline_filename = filename
                    return filename

    def save_pipeline(self):
        """
        Ask for a filename using the file dialog, and save the pipeline as a
        XML or python file.
        """
        pipeline = self.scene.pipeline
        old_filename = getattr(self, "_pipeline_filename", "")
        filename = qt_backend.getSaveFileName(
            None,
            "Save the pipeline",
            old_filename,
            "Compatible files (*.xml *.py);; All (*)",
        )
        if filename:
            posdict = {}
            for key, value in self.scene.pos.items():
                if hasattr(value, "x"):
                    posdict[key] = (value.x(), value.y())
                else:
                    posdict[key] = (value[0], value[1])
            dimdict = {}
            for key, value in self.scene.dim.items():
                if hasattr(value, "boundingRect"):
                    dimdict[key] = (
                        value.boundingRect().width(),
                        value.boundingRect().height(),
                    )
                else:
                    dimdict[key] = (value[0], value[1])

            pipeline.node_dimension = dimdict
            old_pos = pipeline.node_position
            old_dim = pipeline.node_dimension
            pipeline.node_position = posdict
            pipeline_tools.save_pipeline(pipeline, filename)
            self._pipeline_filename = str(filename)
            pipeline.node_position = old_pos
            pipeline.node_dimension = old_dim

    # def load_pipeline_parameters(self):
    # """
    # Loading and setting pipeline parameters (inputs and outputs) from a Json file.
    # """
    # pipeline = self.scene.pipeline
    # filename = qt_backend.getOpenFileName(
    # None, 'Load pipeline parameters', '',
    #'Compatible files (*.json)')

    # pipeline_tools.load_pipeline_parameters(filename, pipeline)

    # def save_pipeline_parameters(self):
    # """
    # Saving pipeline parameters (inputs and outputs) to a Json file.
    # """
    # pipeline = self.scene.pipeline
    # filename = qt_backend.getSaveFileName(
    # None, 'Save pipeline parameters', '',
    #'Compatible files (*.json)')

    # pipeline_tools.save_pipeline_parameters(filename, pipeline)

    def load_pipeline_parameters(self, root_path=""):
        """
        Loading and setting pipeline parameters (inputs and outputs) from a Json file.
        :return:
        """

        def hinted_tuple_hook(obj):
            if "__tuple__" in obj:
                return tuple(obj["items"])

            else:
                return obj

        filename = qt_backend.getOpenFileName(
            None, "Load the pipeline parameters", root_path, "Compatible files (*.json)"
        )

        if filename:
            with open(filename, "r", encoding="utf8") as fileJson:
                dic = json.load(fileJson)

            dic = json.loads(dic, object_hook=hinted_tuple_hook)

            if "pipeline_parameters" not in list(dic.keys()):
                raise KeyError(f'No "pipeline_parameters" key found in {filename}.')

            for field_name, field_value in dic["pipeline_parameters"].items():
                if field_name not in [
                    field.name for field in self.scene.pipeline.fields()
                ]:
                    print(f'No "{field_name}" parameter in pipeline.')

                try:
                    setattr(self.scene.pipeline, field_name, field_value)

                except dataclasses.ValidationError:
                    print(f"Error for the plug {field_name}")

            self.scene.pipeline.update_nodes_and_plugs_activation()

    def save_pipeline_parameters(self):
        """
        Saving pipeline parameters (inputs and outputs) to a Json file.
        :return:
        """

        class MultiDimensionalArrayEncoder(json.JSONEncoder):
            def encode(self, obj):
                def hint_tuples(item):
                    if isinstance(item, tuple):
                        return {
                            "__tuple__": True,
                            "items": [hint_tuples(e) for e in item],
                        }

                    if isinstance(item, list):
                        return [hint_tuples(e) for e in item]

                    if isinstance(item, dict):
                        return dict(
                            (key, hint_tuples(value)) for key, value in item.items()
                        )

                    else:
                        return item

                return super().encode(hint_tuples(obj))

        pipeline = self.scene.pipeline

        filename = qt_backend.getSaveFileName(
            None, "Save the pipeline parameters", "", "Compatible files (*.json)"
        )

        if not filename:  # save widget was cancelled by the user
            return ""

        if os.path.splitext(filename)[1] == "":  # which means no extension
            filename += ".json"

        elif os.path.splitext(filename)[1] != ".json":
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText(
                'The parameters must be saved in the ".json" format, '
                f'not the "{os.path.splitext(filename)[1]}" format'
            )
            msg.setWindowTitle("Warning")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.buttonClicked.connect(msg.close)
            msg.exec_()
            self.save_pipeline_parameters()
            return ""

        if os.path.exists(filename) and self.disable_overwrite:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText(
                "This file already exists, you do not have the "
                "rights to overwrite it."
            )
            msg.setWindowTitle("Warning")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.buttonClicked.connect(msg.close)
            msg.exec_()
            self.save_pipeline_parameters()
            return ""

        if filename:
            # Generating the dictionary
            param_dic = {}

            for field in pipeline.fields():
                field_name = field.name

                if field_name in ["nodes_activation"]:
                    continue

                value = getattr(pipeline, field_name, undefined)

                if value is undefined:
                    value = ""

                param_dic[field_name] = value

            # In the future, more information may be added to this dictionary
            dic = {}
            dic["pipeline_parameters"] = param_dic
            jsonstring = MultiDimensionalArrayEncoder().encode(dic)

            # Saving the dictionary in the Json file
            if sys.version_info[0] >= 3:
                with open(filename, "w", encoding="utf8") as file:
                    json.dump(jsonstring, file)
            else:
                with open(filename, "w") as file:
                    json.dump(jsonstring, file)
