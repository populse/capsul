##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
import os
from pprint import pprint
import weakref
import tempfile
import subprocess
import distutils.spawn
import importlib
import sys
import types
import inspect
import six

# Capsul import
from soma.qt_gui.qt_backend import QtCore, QtGui, Qt
from soma.qt_gui.qt_backend.Qt import QMessageBox
from soma.sorted_dictionary import SortedDictionary
from capsul.api import Switch, PipelineNode, OptionalOutputSwitch
from capsul.pipeline import pipeline_tools
from capsul.api import Pipeline
from capsul.api import Process
from capsul.api import get_process_instance
from capsul.pipeline.process_iteration import ProcessIteration
from capsul.qt_gui.widgets.pipeline_file_warning_widget \
    import PipelineFileWarningWidget
import capsul.pipeline.xml as capsulxml
from capsul.study_config import process_instance
from soma.controller import Controller
from soma.utils.functiontools import SomaPartial

try:
    from traits import api as traits
except ImportError:
    from enthought.traits import api as traits

from soma.qt_gui import qt_backend
qt_backend.init_traitsui_handler()

#from soma.qt_gui.controller_widget import ScrollControllerWidget
from capsul.qt_gui.widgets.attributed_process_widget \
    import AttributedProcessWidget

if sys.version_info[0] >= 3:
    unicode = str
    def values(d):
        return list(d.values())
else:
    def values(d):
        return d.values()

# -----------------------------------------------------------------------------
# Globals and constants
# -----------------------------------------------------------------------------

GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
GRAY_2 = QtGui.QColor.fromRgbF(0.4, 0.4, 0.4, 1)
LIGHT_GRAY_1 = QtGui.QColor.fromRgbF(0.7, 0.7, 0.8, 1)
LIGHT_GRAY_2 = QtGui.QColor.fromRgbF(0.6, 0.6, 0.7, 1)

RED_2 = QtGui.QColor.fromRgb(234, 131, 31)


# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------

class Plug(QtGui.QGraphicsPolygonItem):

    def __init__(self, name, height, width, activated=True,
                 optional=False, parent=None):
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
        #print('plug pressed.')
        super(Plug, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.scene().plug_clicked.emit(self.name)
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            #print('plug: right click')
            self.scene().plug_right_clicked.emit(self.name)
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

    def __init__(self, name, parameters, pipeline,
                 parent=None, process=None, sub_pipeline=None,
                 colored_parameters=True,
                 logical_view=False, labels=[],
                 show_opt_inputs=False, show_opt_outputs=True):
        super(NodeGWidget, self).__init__(parent)
        self.style = 'default'
        self.name = name
        self.parameters = SortedDictionary(
            [(pname, param) for pname, param in six.iteritems(parameters)
             if not getattr(param, 'hidden', False)])
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.in_plugs = {}
        self.in_params = {}
        self.out_plugs = {}
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
        self.scene_labels = labels
        self.label_items = []
        my_labels = []
        steps = getattr(pipeline, 'pipeline_steps', None)
        if steps:
            for step_name, step in six.iteritems(steps.user_traits()):
                step_nodes = step.nodes
                if name in step_nodes:
                    my_labels.append('step: %s' % step_name)
        selects = pipeline.get_processes_selections()
        for sel_plug in selects:
            groups = pipeline.get_processes_selection_groups(sel_plug)
            for group, nodes in six.iteritems(groups):
                if name in nodes:
                    my_labels.append('select: %s' % sel_plug)

        for label in my_labels:
            self._get_label(label)

        self._set_brush()
        self.setAcceptedMouseButtons(
            QtCore.Qt.LeftButton|QtCore.Qt.RightButton|QtCore.Qt.MiddleButton)

        self._build()
        if colored_parameters:
            process.on_trait_change(self._repaint_parameter, dispatch='ui')

    def __del__(self):
        if self.colored_parameters:
            self.process.on_trait_change(self._repaint_parameter, remove=True)
        #super(NodeGWidget, self).__del__()

    def get_title(self):
        if self.sub_pipeline is None:
            return self.name
        else:
            return "[{0}]".format(self.name)

    def _get_label(self, label, register=True):
        class Label(object):
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
        colors = [[1, 0.3, 0.3],
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
                  [0., 1., 0.7],
                  [0.7, 1, 0.7],
                  [0.7, 0, 1],
                  [0., 0.7, 1],
                  [0.7, 0.7, 1],
                  [1, 1, 0.5],
                  [0.5, 1, 1],
                  [1, 0.5, 1]]
        c = colors[num % len(colors)]
        code = (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
        return code

    def _repaint_parameter(self, param_name, new_value):
        if self.logical_view or param_name not in self.parameters:
            return
        param_text = self._parameter_text(param_name)
        param_item = self.in_params.get(param_name)
        if param_item is None:
            param_item = self.out_params[param_name]
        if isinstance(param_item, QtGui.QGraphicsProxyWidget):
            # colored parameters are widgets
            param_item.widget().findChild(
                QtGui.QLabel, 'label').setText(param_text)
        else:
            param_item.setHtml(param_text)

    def _build(self):
        margin = 5
        self.title = QtGui.QGraphicsTextItem(self.get_title(), self)
        font = self.title.font()
        font.setWeight(QtGui.QFont.Bold)
        self.title.setFont(font)
        self.title.setPos(margin, margin)
        self.title.setZValue(2)
        self.title.setParentItem(self)

        if self.logical_view:
            self._build_logical_view_plugs()
        else:
            self._build_regular_view_plugs()
        self._create_label_marks()

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

    def _colored_text_item(self, label, text=None, margin=2):
        labelc = self._get_label(label, False)
        color = labelc.color
        if text is None:
            text = label
        # I can't make rounded borders with appropriate padding
        # without using 2 QLabels. This is probably overkill. We could
        # replace this code of we find a simpler way.
        label_w = QtGui.QLabel('')
        label_w.setStyleSheet("background: rgba(255, 255, 255, 0);")
        lay = QtGui.QVBoxLayout()
        lay.setContentsMargins(margin, margin, margin, margin)
        label_w.setLayout(lay)
        label2 = QtGui.QLabel(text)
        label2.setObjectName('label')
        label2.setStyleSheet(
            "background: rgba({0}, {1}, {2}, 255); "
            "border-radius: 7px; border: 0px solid; "
            "padding: 1px;".format(*color))
        lay.addWidget(label2)
        label_item = QtGui.QGraphicsProxyWidget(self)
        label_item.setWidget(label_w)
        return label_item

    def _build_regular_view_plugs(self):
        margin = 5
        plug_width = 12
        pos = margin + margin + self.title.boundingRect().size().height()
        if self.name == 'inputs':
            selections = self.pipeline.get_processes_selections()
        else:
            selections = []

        for in_param, pipeline_plug in six.iteritems(self.parameters):
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output or (not self.show_opt_inputs and pipeline_plug.optional):
                continue
            param_text = self._parameter_text(in_param)
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml(param_text)

            plug_name = '%s:%s' % (self.name, in_param)
            plug = Plug(plug_name,
                        param_name.boundingRect().size().height(),
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

        for out_param, pipeline_plug in six.iteritems(self.parameters):
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if not output or (not self.show_opt_outputs and pipeline_plug.optional):
                continue
            param_text = self._parameter_text(out_param)
            if out_param in selections:
                param_name = self._colored_text_item('select: ' + out_param,
                                                     param_text, 0)
            else:
                param_name = QtGui.QGraphicsTextItem(self)
                param_name.setHtml(param_text)

            plug_name = '%s:%s' % (self.name, out_param)
            plug = Plug(plug_name,
                        param_name.boundingRect().size().height(),
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

        for in_param, pipeline_plug in six.iteritems(self.parameters):
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                has_output = True
            else:
                has_input = True
            if has_input and has_output:
                break

        if has_input:
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml('')
            plug_name = '%s:inputs' % self.name
            plug = Plug(plug_name,
                        param_name.boundingRect().size().height(),
                        plug_width, activated=True,
                        optional=False, parent=self)
            param_name.setZValue(2)
            plug.setPos(margin, pos)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.in_plugs['inputs'] = plug
            self.in_params['inputs'] = param_name

        if has_output:
            param_name = QtGui.QGraphicsTextItem(self)
            param_name.setHtml('')
            plug_name = '%s:outputs' % self.name
            plug = Plug(plug_name,
                        param_name.boundingRect().size().height(),
                        plug_width, activated=True,
                        optional=False, parent=self)
            param_name.setZValue(2)
            param_name.setPos(plug.boundingRect().size().width() + margin, pos)
            plug.setPos(self.title.boundingRect().width()
                        - plug.boundingRect().width(), pos)
            param_name.setParentItem(self)
            plug.setParentItem(self)
            self.out_plugs['outputs'] = plug
            self.out_params['outputs'] = param_name

    def _create_label_marks(self):
        labels = self.labels
        if labels:
            margin = 5
            plug_width = 12
            xpos = margin + plug_width
            ypos = 0
            if self.out_params:
                params = self.out_params
            elif self.in_params:
                params = self.in_params
            if params:
                ypos = max([p.boundingRect().bottom()
                            for p in params.values()])
            else:
                ypos = margin * 2 + self.title.boundingRect().size().height()
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

    def clear_plugs(self):
        for plugs, params in ((self.in_plugs, self.in_params),
                              (self.out_plugs, self.out_params)):
            for plug_name, plug in six.iteritems(plugs):
                param_item = params[plug_name]
                self.scene().removeItem(param_item)
                self.scene().removeItem(plug)
        self.in_params = {}
        self.in_plugs = {}
        self.out_params = {}
        self.out_plugs = {}

    def _set_brush(self):
        pipeline = self.pipeline
        if self.name in ('inputs', 'outputs'):
            node = pipeline.pipeline_node
        else:
            node = pipeline.nodes[self.name]
        color_1, color_2, color_3, style = pipeline_tools.pipeline_node_colors(
            pipeline, node)
        self.style = style
        color_1 = QtGui.QColor.fromRgbF(*color_1)
        color_2 = QtGui.QColor.fromRgbF(*color_2)
        gradient = QtGui.QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, color_1)
        gradient.setColorAt(1, color_2)
        self.bg_brush = QtGui.QBrush(gradient)

        if node.activated:
            color_1 = GRAY_1
            color_2 = GRAY_2
        else:
            color_1 = LIGHT_GRAY_1
            color_2 = LIGHT_GRAY_2
        if node in pipeline.disabled_pipeline_steps_nodes():
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
        if self.logical_view:
            if output:
                param_name = 'outputs'
            else:
                param_name = 'inputs'
        param_text = self._parameter_text(param_name)
        if self.name == 'inputs' and not self.logical_view \
                and 'select: ' + param_name in \
                    [l.text for l in self.scene_labels]:
            param_name_item = self._colored_text_item('select: ' + param_name,
                                                      param_text, 0)
        else:
            param_name_item = QtGui.QGraphicsTextItem(self)
            param_name_item.setHtml(param_text)
        plug_name = '%s:%s' % (self.name, param_name)
        plug = Plug(plug_name,
                    param_name_item.boundingRect().size().height(),
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
        if self.logical_view:
            params_size = 0
            if output:
                pxpos = self.title.boundingRect().width() \
                    - plug.boundingRect().width()
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
                param_item = None
            else:
                param_item = values(self.out_params)[0]
        else:
            param_item = values(self.in_params)[0]
        ni = 0
        no = 0
        bottom_pos = 0
        if param_item:
            for param_name, pipeline_plug in six.iteritems(self.parameters):
                output = (not pipeline_plug.output if self.name in (
                    'inputs', 'outputs') else pipeline_plug.output)
                if output:
                    # Added to choose to visualize optional parameters
                    if not pipeline_plug.optional or (self.show_opt_outputs and pipeline_plug.optional):
                        params = self.out_params
                        plugs = self.out_plugs
                        npos = no + len(self.in_params)
                        no += 1
                    else:
                        continue
                else:
                    # Added to choose to visualize optional parameters
                    if not pipeline_plug.optional or (self.show_opt_inputs and pipeline_plug.optional):
                        params = self.in_params
                        plugs = self.in_plugs
                        npos = ni
                        ni += 1
                    else:
                        continue
                pos = margin * 2 + self.title.boundingRect().size().height() \
                    + param_item.boundingRect().size().height() * npos
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
            pos = margin * 2 + self.title.boundingRect().size().height() \
                + param_item.boundingRect().size().height() * nparams
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
        self.scene().removeItem(param_item)
        plug = plugs[param_name]
        self.scene().removeItem(plug)
        del params[param_name]
        del plugs[param_name]
        self._shift_params()

    def _parameter_text(self, param_name):
        if self.logical_view:
            return ''
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
        self._set_brush()
        self.box_title.setBrush(self.title_brush)
        self.box.setBrush(self.bg_brush)
        for param, pipeline_plug in six.iteritems(self.parameters):
            output = (not pipeline_plug.output if self.name in (
                'inputs', 'outputs') else pipeline_plug.output)
            if output:
                plugs = self.out_plugs
                params = self.out_params
                if self.logical_view:
                    param = 'outputs'
            else:
                plugs = self.in_plugs
                params = self.in_params
                if self.logical_view:
                    param = 'inputs'
            gplug = plugs.get(param)
            if gplug is None: # new parameter ?
                self._create_parameter(param, pipeline_plug)
                gplug = plugs.get(param)
            if not self.logical_view:
                gplug.update_plug(pipeline_plug.activated,
                                  pipeline_plug.optional)
                if isinstance(params[param], QtGui.QGraphicsProxyWidget):
                    # colored parameters are widgets
                    params[param].widget().findChild(
                        QtGui.QLabel, 'label').setText(
                            self._parameter_text(param))
                else:
                    params[param].setHtml(self._parameter_text(param))

        if not self.logical_view:
            # check removed params
            to_remove = []

            # Added to choose to visualize optional parameters
            for param, pipeline_plug in six.iteritems(self.parameters):
                output = (not pipeline_plug.output if self.name in (
                    'inputs', 'outputs') else pipeline_plug.output)
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

        rect = self.title.mapRectToParent(self.title.boundingRect())
        margin = 5
        brect = self.boundingRect()
        brect.setWidth(brect.right() - margin)
        rect.setWidth(brect.width())
        self.box_title.setRect(rect)
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
        for name, param in six.iteritems(self.out_params):
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
        for name, param in six.iteritems(self.out_params):
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
        for param_name, param in six.iteritems(self.in_params):
            if param.boundingRect().width() > width:
                width = param.boundingRect().width()
            if pwidth == 0:
                plug = self.in_plugs[param_name]
                pwidth = plug.boundingRect().width()
        return width + margin + pwidth

    def out_params_width(self):
        width = 0
        for param_name, param in six.iteritems(self.out_params):
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
                allow_open_controller=allow_open_controller,
                enable_edition=self.scene().edition_enabled())
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
        item = self.scene().itemAt(event.scenePos(), Qt.QTransform())
        #print('NodeGWidget click, item:', item)
        if isinstance(item, Plug):
            item.mousePressEvent(event)
            return
        super(NodeGWidget, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.RightButton \
                and self.process is not None:
            self.scene().node_right_clicked.emit(self.name, self.process)
            event.accept()

        if event.button() == QtCore.Qt.LeftButton \
                and self.process is not None:
            self.scene().node_clicked.emit(self.name, self.process)
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
        self.active = active
        self.weak = weak

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
        self.active = active
        self.weak = weak

    def mousePressEvent(self, event):
        item = self.scene().itemAt(event.scenePos(), Qt.QTransform())
        #print('Link click, item:', item)
        if event.button() == QtCore.Qt.RightButton:
            # not a signal since we don't jhave enough identity information in
            # self: the scene has to help us.
            self.scene()._link_right_clicked(self)
            event.accept()
        else:
            super(Link, self).mousePressEvent(event)


class PipelineScene(QtGui.QGraphicsScene):
    # Signal emitted when a sub pipeline has to be open.
    subpipeline_clicked = QtCore.Signal(str, Process,
                                        QtCore.Qt.KeyboardModifiers)
    # Signal emitted when a node box is clicked
    node_clicked = QtCore.Signal(str, Process)
    # Signal emitted when a node box is right-clicked
    node_right_clicked = QtCore.Signal(str, Controller)
    # Signal emitted when a plug is clicked
    plug_clicked = QtCore.Signal(str)
    # Signal emitted when a plug is clicked with the right mouse button
    plug_right_clicked = QtCore.Signal(str)
    # Signal emitted when a link is right-clicked
    link_right_clicked = QtCore.Signal(str, str, str, str)

    def __init__(self, parent=None):
        super(PipelineScene, self).__init__(parent)
        self.gnodes = {}
        self.glinks = {}
        self._pos = 50
        self.pos = {}
        self.colored_parameters = True
        self.logical_view = False
        self._enable_edition = False
        self.labels = []

        self.changed.connect(self.update_paths)

    def _add_node(self, name, gnode):
        self.addItem(gnode)
        pos = self.pos.get(name)
        if pos is None:
            gnode.setPos(self._pos, self._pos)
            self._pos += 100
        else:
            if not isinstance(pos, Qt.QPointF):
                pos = Qt.QPointF(pos[0], pos[1])
            gnode.setPos(pos)
        self.gnodes[name] = gnode

    def add_node(self, node_name, node):
        if isinstance(node, Switch):
            process = node
        if hasattr(node, 'process'):
            process = node.process
        if isinstance(node, PipelineNode):
            sub_pipeline = process
        elif process and isinstance(process, ProcessIteration):
            sub_pipeline = process.process
        else:
            sub_pipeline = None
        gnode = NodeGWidget(
            node_name, node.plugs, self.pipeline,
            sub_pipeline=sub_pipeline, process=process,
            colored_parameters=self.colored_parameters,
            logical_view=self.logical_view, labels=self.labels)
        self._add_node(node_name, gnode)
        return gnode

    def add_link(self, source, dest, active, weak):
        source_gnode_name, source_param = source
        if not source_gnode_name:
            source_gnode_name = 'inputs'
        dest_gnode_name, dest_param = dest
        if not dest_gnode_name:
            dest_gnode_name = 'outputs'
        if self.logical_view:
            source_param = 'outputs'
            dest_param = 'inputs'
        source_dest = ((str(source_gnode_name), str(source_param)),
            (str(dest_gnode_name), str(dest_param)))
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
                    glink.update_activation(active, weak)
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
        if self.logical_view:
            # is it useful ?
            source_param = 'outputs'
            dest_param = 'inputs'
        dest_gnode = self.gnodes.get(dest_gnode_name)
        new_source_dest = ((str(source_gnode_name), str(source_param)),
                           (str(dest_gnode_name), str(dest_param)))
        glink = self.glinks.get(new_source_dest)
        if glink is not None:
            self.removeItem(glink)
            del self.glinks[new_source_dest]

    def update_paths(self):
        for i in self.items():
            if isinstance(i, NodeGWidget):
                self.pos[i.name] = i.pos()

        for source_dest, glink in six.iteritems(self.glinks):
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
        self.labels = []
        pipeline_inputs = SortedDictionary()
        pipeline_outputs = SortedDictionary()
        for name, plug in six.iteritems(pipeline.nodes[''].plugs):
            if plug.output:
                pipeline_outputs[name] = plug
            else:
                pipeline_inputs[name] = plug
        if pipeline_inputs:
            self._add_node(
                'inputs', NodeGWidget('inputs', pipeline_inputs, pipeline,
                    process=pipeline,
                    colored_parameters=self.colored_parameters,
                    logical_view=self.logical_view))
        for node_name, node in six.iteritems(pipeline.nodes):
            if not node_name:
                continue
            self.add_node(node_name, node)
        if pipeline_outputs:
            self._add_node(
                'outputs', NodeGWidget(
                    'outputs', pipeline_outputs, pipeline,
                    process=pipeline,
                    colored_parameters=self.colored_parameters,
                    logical_view=self.logical_view))

        for source_node_name, source_node in six.iteritems(pipeline.nodes):
            for source_parameter, source_plug \
                    in six.iteritems(source_node.plugs):
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated \
                                and dest_plug.activated,
                            weak=weak_link)

    def update_pipeline(self):
        if self.logical_view:
            self._update_logical_pipeline()
        else:
            self._update_regular_pipeline()

    def _update_regular_pipeline(self):
        # normal view
        pipeline = self.pipeline
        removed_nodes = []
        for node_name, gnode in six.iteritems(self.gnodes):
            if gnode.logical_view:
                gnode.clear_plugs()
                gnode.logical_view = False
            if node_name in ('inputs', 'outputs'):
                node = pipeline.nodes['']
                # in case traits have been added/removed
                if node_name == 'inputs':
                    pipeline_inputs = SortedDictionary()
                    for name, plug in six.iteritems(node.plugs):
                        if not plug.output:
                            pipeline_inputs[name] = plug
                    gnode.parameters = pipeline_inputs
                else:
                    pipeline_outputs = SortedDictionary()
                    for name, plug in six.iteritems(node.plugs):
                        if plug.output:
                            pipeline_outputs[name] = plug
                    gnode.parameters = pipeline_outputs
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
            del self.gnodes[node_name]

        # check for added nodes
        added_nodes = []
        for node_name, node in six.iteritems(pipeline.nodes):
            if node_name == '':
                pipeline_inputs = SortedDictionary()
                pipeline_outputs = SortedDictionary()
                for name, plug in six.iteritems(node.plugs):
                    if plug.output:
                        pipeline_outputs[name] = plug
                    else:
                        pipeline_inputs[name] = plug
                if pipeline_inputs and 'inputs' not in self.gnodes:
                    self._add_node(
                        'inputs', NodeGWidget(
                            'inputs', pipeline_inputs, pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view))
                if pipeline_outputs and 'outputs' not in self.gnodes:
                    self._add_node(
                        'outputs', NodeGWidget(
                            'outputs', pipeline_outputs, pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view))
            elif node_name not in self.gnodes:
                process = None
                if isinstance(node, Switch):
                    process = node
                if hasattr(node, 'process'):
                    process = node.process
                if isinstance(node, PipelineNode):
                    sub_pipeline = node.process
                else:
                    sub_pipeline = None
                self.add_node(node_name, node)

        # links
        to_remove = []
        for source_dest, glink in six.iteritems(self.glinks):
            source, dest = source_dest
            source_node_name, source_param = source
            dest_node_name, dest_param = dest
            if source_node_name == 'inputs':
                source_node_name = ''
            if dest_node_name == 'outputs':
                dest_node_name = ''
            source_node = pipeline.nodes.get(source_node_name)
            if source_node is None:
                to_remove.append(source_dest)
                continue
            source_plug = source_node.plugs.get(source_param)
            dest_node = pipeline.nodes.get(dest_node_name)
            if dest_node is None:
                to_remove.append(dest_node_name)
                continue
            dest_plug = dest_node.plugs.get(dest_param)
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
        for source_node_name, source_node in six.iteritems(pipeline.nodes):
            for source_parameter, source_plug \
                    in six.iteritems(source_node.plugs):
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated \
                                and dest_plug.activated,
                            weak=weak_link)

    def _update_logical_pipeline(self):
        # update nodes plugs and links in logical view mode
        pipeline = self.pipeline
        # nodes state
        removed_nodes = []
        for node_name, gnode in six.iteritems(self.gnodes):
            if not gnode.logical_view:
                gnode.clear_plugs()
                gnode.logical_view = True
            if node_name in ('inputs', 'outputs'):
                node = pipeline.nodes['']
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
            del self.gnodes[node_name]

        # check for added nodes
        added_nodes = []
        for node_name, node in six.iteritems(pipeline.nodes):
            if node_name == '':
                pipeline_inputs = SortedDictionary()
                pipeline_outputs = SortedDictionary()
                for name, plug in six.iteritems(node.plugs):
                    if plug.output:
                        pipeline_outputs['outputs'] = plug
                    else:
                        pipeline_inputs['inputs'] = plug
                if pipeline_inputs and 'inputs' not in self.gnodes:
                    self._add_node(
                        'inputs', NodeGWidget(
                            'inputs', pipeline_inputs, pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view))
                if pipeline_outputs and 'outputs' not in self.gnodes:
                    self._add_node(
                        'outputs', NodeGWidget(
                            'outputs', pipeline_outputs, pipeline,
                            process=pipeline,
                            colored_parameters=self.colored_parameters,
                            logical_view=self.logical_view))
            elif node_name not in self.gnodes:
                process = None
                if isinstance(node, Switch):
                    process = node
                if hasattr(node, 'process'):
                    process = node.process
                if isinstance(node, PipelineNode):
                    sub_pipeline = node.process
                else:
                    sub_pipeline = None
                self.add_node(node_name, node)

        # links
        # delete all links
        for source_dest, glink in six.iteritems(self.glinks):
            self.removeItem(glink)
        self.glinks = {}
        # recreate links
        for source_node_name, source_node in six.iteritems(pipeline.nodes):
            for source_parameter, source_plug \
                    in six.iteritems(source_node.plugs):
                for (dest_node_name, dest_parameter, dest_node, dest_plug,
                     weak_link) in source_plug.links_to:
                    if dest_node is pipeline.nodes.get(dest_node_name):
                        self.add_link(
                            (source_node_name, source_parameter),
                            (dest_node_name, dest_parameter),
                            active=source_plug.activated \
                                and dest_plug.activated,
                            weak=weak_link)

    def set_enable_edition(self, state=True):
        self._enable_edition = state

    def edition_enabled(self):
        return self._enable_edition

    def keyPressEvent(self, event):
        super(PipelineScene, self).keyPressEvent(event)
        if not event.isAccepted():
            if event.key() == QtCore.Qt.Key_P:
                # print position of boxes
                event.accept()
                pview = self.parent()
                pview.print_node_positions()
            elif event.key() == QtCore.Qt.Key_T:
                # toggle logical / full view
                pview = self.parent()
                pview.switch_logical_view()
                event.accept()
            elif event.key() == QtCore.Qt.Key_A:
                # auto-set nodes positions
                pview = self.parent()
                pview.auto_dot_node_positions()

    def link_tooltip_text(self, source_dest):
        '''Tooltip text for the fiven link

        Parameters
        ----------
        source_dest: tupe (2 tuples of 2 strings)
            link description:
            ((source_node, source_param), (dest_node, dest_param))
        '''
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

    @staticmethod
    def html_doc(doc_text):
        # TODO: sphinx transform
        text = doc_text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text

    def plug_tooltip_text(self, node, name):
        '''Tooltip text for a node plug
        '''
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
        trait = proc.user_traits()[name]
        trait_type = trait.trait_type
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
        desc = trait.desc
        if desc:
            msg += '\n<h3>Description:</h3>\n'
            msg += self.html_doc(desc)
        return msg


    def node_tooltip_text(self, node):
        process = node.process
        msg = getattr(process, '__doc__', '')
        #msg = self.html_doc(doc)
        return msg


    def _parentgnode(self, item):
        if qt_backend.get_qt_backend() != 'PyQt5':
            return item.parentItem()
        # in PyQt5 (certain versions at least, Ubuntu 16.04) parentItem()
        # returns something inappropriate, having the wrong type
        # QGraphicsVideoItem, probably a cast mistake, and which leads to
        # a segfault, so we have to get it a different way.
        nodes = [node for node in self.gnodes.values()
                 if item in node.childItems()]
        if len(nodes) == 1:
            return nodes[0]

    def helpEvent(self, event):
        '''
        Display tooltips on plugs and links
        '''
        if self.logical_view:
            event.setAccepted(False)
            super(PipelineScene, self).helpEvent(event)
            return
        item = self.itemAt(event.scenePos(), Qt.QTransform())
        if isinstance(item, Link):
            for source_dest, glink in six.iteritems(self.glinks):
                if glink is item:
                    text = self.link_tooltip_text(source_dest)
                    item.setToolTip(text)
                    break
        elif isinstance(item, Plug):
            node = self._parentgnode(item)
            found = False
            for name, plug in six.iteritems(node.in_plugs):
                if plug is item:
                    found = True
                    break
            if not found:
              for name, plug in six.iteritems(node.out_plugs):
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

        super(PipelineScene, self).helpEvent(event)

    def remove_node(self, node_name):
        gnode = self.gnodes[node_name]
        todel = set()
        for link, glink in six.iteritems(self.glinks):
            if link[0][0] == node_name or link[1][0] == node_name:
                self.removeItem(glink)
                todel.add(link)
        for link in todel:
            del self.glinks[link]
        self.removeItem(gnode)
        del self.gnodes[node_name]

    def _link_right_clicked(self, link):
        # find the link in list
        #print('Scene._link_right_clicked:', link)
        for source_dest, glink in six.iteritems(self.glinks):
            if glink is link:
                self.link_right_clicked.emit(
                    source_dest[0][0], source_dest[0][1],
                    source_dest[1][0], source_dest[1][1])
                break


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
    node_clicked
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
    '''
    subpipeline_clicked = QtCore.Signal(str, Process,
                                        QtCore.Qt.KeyboardModifiers)
    '''Signal emitted when a sub pipeline has to be open.'''
    node_clicked = QtCore.Signal(str, Process)
    '''Signal emitted when a node box has to be open.'''
    node_right_clicked = QtCore.Signal(str, Controller)
    '''Signal emitted when a node box is right-clicked'''
    plug_clicked = QtCore.Signal(str)
    '''Signal emitted when a plug is clicked'''
    plug_right_clicked = QtCore.Signal(str)
    '''Signal emitted when a plug is right-clicked'''
    link_right_clicked = QtCore.Signal(str, str, str, str)
    '''Signal emitted when a link is right-clicked'''
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

    class ProcessNameEdit(Qt.QLineEdit):
        ''' A specialized QLineEdit with completion for process name
        '''
        def __init__(self, parent=None):
            super(PipelineDevelopperView.ProcessNameEdit,
                  self).__init__(parent)
            self.compl = QtGui.QCompleter([])
            self.setCompleter(self.compl)
            self.textEdited.connect(self.on_text_edited)
            self.py_cache = {} # cache for loaded python files

        @staticmethod
        def _execfile(filename):
            # This chunk of code cannot be put inline in python 2.6
            glob_dict = {}
            exec(compile(open(filename, "rb").read(), filename, 'exec'),
                  glob_dict, glob_dict)
            return glob_dict

        def load_py(self, filename):
            if filename not in self.py_cache:
                try:
                    self.py_cache[filename] \
                        = PipelineDevelopperView.ProcessNameEdit._execfile(
                            filename)
                except Exception as e:
                    print('exception while executing file %s:' % filename, e)
                    return {}
            return self.py_cache[filename]

        def get_processes_or_modules(self, filename):
            file_dict = self.load_py(filename)
            processes = []
            for name, item in six.iteritems(file_dict):
                if process_instance.is_process(item) or inspect.ismodule(item):
                    processes.append(name)
            return processes

        def on_text_edited(self, text):
            compl = set()
            modpath = str(text).split('.')
            current_mod = None
            paths = []
            sel = set()
            mod = None
            if len(modpath) > 1:
                current_mod = '.'.join(modpath[:-1])
                try:
                    mod = importlib.import_module(current_mod)
                except ImportError:
                    mod = None
                if mod:
                    if os.path.basename(mod.__file__).startswith(
                            '__init__.py'):
                        paths = [os.path.dirname(mod.__file__)]
                    # add process/pipeline objects in current_mod
                    procs = [item for k, item
                                in six.iteritems(mod.__dict__)
                             if process_instance.is_process(item)
                                or inspect.ismodule(item)]
                    compl.update(['.'.join([current_mod, c.__name__])
                                  for c in procs])
            if not mod:
                # no current module
                # is it a path name ?
                pathname, filename = os.path.split(str(text))
                if os.path.isdir(pathname):
                    # look for class in python file filename.py#classname
                    elements = filename.split('.py#')
                    if len(elements) == 2:
                        filename = elements[0] + '.py'
                        object_name = elements[1]
                        full_path = os.path.join(pathname, filename)
                        processes = self.get_processes_or_modules(full_path)
                        if object_name != '':
                            processes = [p for p in processes
                                         if p.startswith(object_name)]
                        compl.update(['#'.join((full_path, p))
                                      for p in processes])
                    else:
                        # look for matching xml files
                        for f in os.listdir(pathname):
                            if (f.endswith('.xml')
                                    or os.path.isdir(os.path.join(pathname,
                                                                  f))) \
                                    and f.startswith(filename):
                                compl.add(os.path.join(pathname, f))
                            elif f.endswith('.py'):
                                compl.add(os.path.join(pathname, f))
                else:
                    paths = sys.path
            for path in paths:
                if path == '':
                    path = '.'
                try:
                    for f in os.listdir(path):
                        if f.endswith('.py'):
                            sel.add(f[:-3])
                        elif f.endswith('.pyc') or f.endswith('.pyo'):
                            sel.add(f[:-4])
                        elif f.endswith('.xml'):
                            sel.add(f)
                        elif '.' not in f \
                                and os.path.isdir(os.path.join(
                                    path, f)):
                            sel.add(f)
                except OSError:
                    pass
            begin = modpath[-1]
            cm = []
            if current_mod is not None:
                cm = [current_mod]
            compl.update(['.'.join(cm + [f]) for f in sel \
                if f.startswith(modpath[-1])])
            model = self.compl.model()
            model.setStringList(list(compl))

    def __init__(self, pipeline=None, parent=None, show_sub_pipelines=False,
            allow_open_controller=False, logical_view=False,
            enable_edition=False):
        '''PipelineDevelopperView

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
        '''
        super(PipelineDevelopperView, self).__init__(parent)
        self.scene = None
        self.colored_parameters = True
        self._show_sub_pipelines = show_sub_pipelines
        self._allow_open_controller = allow_open_controller
        self._logical_view = logical_view
        self._enable_edition = enable_edition

        if pipeline is None:
            pipeline = Pipeline()
            enable_edition = True

        # Check that we have a pipeline or a process
        if not isinstance(pipeline, Pipeline):
            if isinstance(pipeline, Process):
                process = pipeline
                pipeline = Pipeline()
                pipeline.add_process(process.name, process)
                pipeline.autoexport_nodes_parameters()
                pipeline.node_position["inputs"] = (0., 0.)
                pipeline.node_position[process.name] = (300., 0.)
                pipeline.node_position["outputs"] = (600., 0.)
                #pipeline.scene_scale_factor = 0.5
            else:
                raise Exception("Expect a Pipeline or a Process, not a "
                                "'{0}'.".format(repr(pipeline)))

        self.set_pipeline(pipeline)
        self._grab = False
        self._grab_link = False
        self.plug_clicked.connect(self._plug_clicked)
        self.plug_right_clicked.connect(self._plug_right_clicked)
        self.link_right_clicked.connect(self._link_clicked)

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
        pos = {}
        if self.scene:
            pos = self.scene.pos
            #pprint(dict((i, (j.x(), j.y())) for i, j in six.iteritems(pos)))
        for i, j in six.iteritems(pipeline.node_position):
            if isinstance(j, QtCore.QPointF):
                pos[i] = j
            else:
                pos[i] = QtCore.QPointF(*j)
        self.scene = PipelineScene(self)
        self.scene.set_enable_edition(self._enable_edition)
        self.scene.logical_view = self._logical_view
        self.scene.colored_parameters = self.colored_parameters
        self.scene.subpipeline_clicked.connect(self.subpipeline_clicked)
        self.scene.subpipeline_clicked.connect(self.onLoadSubPipelineClicked)
        self.scene.node_clicked.connect(self.node_clicked)
        self.scene.node_right_clicked.connect(self.node_right_clicked)
        self.scene.node_right_clicked.connect(self.onOpenProcessController)
        self.scene.plug_clicked.connect(self.plug_clicked)
        self.scene.plug_right_clicked.connect(self.plug_right_clicked)
        self.scene.link_right_clicked.connect(self.link_right_clicked)
        self.scene.pos = pos
        self.scene.set_pipeline(pipeline)
        self.setWindowTitle(pipeline.name)
        self.setScene(self.scene)

        # Try to initialize the scene scale factor
        if hasattr(pipeline, "scene_scale_factor"):
            self.scale(
                pipeline.scene_scale_factor, pipeline.scene_scale_factor)
        self.reset_initial_nodes_positions()


    def set_pipeline(self, pipeline):
        '''
        Assigns a new pipeline to the view.
        '''
        self._set_pipeline(pipeline)

        # Setup callback to update view when pipeline state is modified
        pipeline.on_trait_change(self._reset_pipeline, 'selection_changed',
                                 dispatch='ui')
        pipeline.on_trait_change(self._reset_pipeline, 'user_traits_changed',
                                 dispatch='ui')
        if hasattr(pipeline, 'pipeline_steps'):
            pipeline.pipeline_steps.on_trait_change(
                self._reset_pipeline, dispatch='ui')

    def is_logical_view(self):
        '''
        in logical view mode, plugs and links between plugs are hidden, only
        links between nodes are displayed.
        '''
        return self._logical_view

    def set_logical_view(self, state):
        '''
        in logical view mode, plugs and links between plugs are hidden, only
        links between nodes are displayed.

        Parameters
        ----------
        state:  bool (mandatory)
            to set/unset the logical view mode
        '''
        self._logical_view = state
        self._reset_pipeline()

    def _reset_pipeline(self):
        # print('reset pipeline')
        #self._set_pipeline(pipeline)
        self.scene.logical_view = self._logical_view
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

    def edition_enabled(self):
        '''
        Get the editable state
        '''
        return self._enable_edition

    def set_enable_edition(self, state=True):
        '''
        Set the editable state. Edition allows to modify a pipeline: adding /
        removing process boxes and switches, drawing links, etc.
        '''
        self._enable_edition = state
        self.scene.set_enable_edition(state)

    def wheelEvent(self, event):
        done = False
        if event.modifiers() == QtCore.Qt.ControlModifier:
            item = self.itemAt(event.pos())
            if not isinstance(item, QtGui.QGraphicsProxyWidget):
                done = True
                if qt_backend.get_qt_backend() == 'PyQt5':
                    delta = event.angleDelta().y()
                else:
                    delta = event.delta()
                if delta < 0:
                    self.zoom_out()
                else:
                    self.zoom_in()
                event.accept()
        if not done:
            super(PipelineDevelopperView, self).wheelEvent(event)

    def mousePressEvent(self, event):
        super(PipelineDevelopperView, self).mousePressEvent(event)
        if not event.isAccepted():
            if event.button() == QtCore.Qt.RightButton:
                self.open_background_menu()
            else:
                self._grab = True
                self._grabpos = event.pos()

    def mouseReleaseEvent(self, event):
        self._grab = False
        if self._grab_link:
            event.accept()
            self._release_grab_link(event)
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
        elif self._grab_link:
            self._move_grab_link(event)
            event.accept()
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
        If ctrl is pressed the new view will be embedded in its parent node
        box.
        """
        if self._show_sub_pipelines:
            if modifiers & QtCore.Qt.ControlModifier:
                try:
                    self.add_embedded_subpipeline(node_name)
                    return
                except KeyError:
                    print('node not found in:')
                    print(self.scene.gnodes.keys())
            sub_view = PipelineDevelopperView(sub_pipeline,
                show_sub_pipelines=self._show_sub_pipelines,
                allow_open_controller=self._allow_open_controller,
                enable_edition=self.edition_enabled(),
                logical_view=self._logical_view)
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
            self.open_node_menu(node_name, process)

    def openProcessController(self):
        sub_view = QtGui.QScrollArea()
        node_name = self.current_node_name
        if node_name in ('inputs', 'outputs'):
            node_name = ''
        process = self.scene.pipeline.nodes[node_name]
        if hasattr(process, 'process'):
            process = process.process
        cwidget = AttributedProcessWidget(
            process, enable_attr_from_filename=True, enable_load_buttons=True)
        cwidget.setParent(sub_view)
        sub_view.setWidget(cwidget)
        sub_view.setWidgetResizable(True)
        sub_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        sub_view.setWindowTitle(self.current_node_name)
        sub_view.show()
        # set self.window() as QObject parent (not QWidget parent) to
        # prevent the sub_view to close/delete immediately
        QtCore.QObject.setParent(sub_view, self.window())

    def open_node_menu(self, node_name, process):
        """ right-click popup menu for nodes
        """
        node_name = unicode(node_name) # in case it is a QString
        node_type = 'process'
        if isinstance(process, OptionalOutputSwitch):
            node_type = 'opt. output switch'
        elif isinstance(process, Switch):
            node_type = 'switch'
        menu = QtGui.QMenu('Node: %s' % node_name, None)
        title = menu.addAction('Node: %s (%s)' % (node_name, node_type))
        title.setEnabled(False)
        menu.addSeparator()

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
        menu.addAction(disable_action)

        steps = getattr(self.scene.pipeline, 'pipeline_steps', None)
        if steps is not None:
            my_steps = [step_name for step_name in steps.user_traits()
                        if node.name in steps.trait(step_name).nodes]
            for step in my_steps:
                step_action = menu.addAction('(enable) step: %s' % step)
                step_action.setCheckable(True)
                step_state = getattr(self.scene.pipeline.pipeline_steps, step)
                step_action.setChecked(step_state)
                step_action.toggled.connect(SomaPartial(self.enable_step,
                                                        step))
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

        enable_all_action = menu.addAction('Enable all steps')
        enable_all_action.triggered.connect(self.enable_all_steps)
        disable_done_action = menu.addAction(
            'Disable steps with existing outputs')
        disable_done_action.triggered.connect(self.disable_done_steps)
        check_pipeline_action = menu.addAction(
            'Check input / output files')
        check_pipeline_action.triggered.connect(self.check_files)

        if isinstance(node, Switch) \
                and not isinstance(node, OptionalOutputSwitch):
            # allow to select switch value from the menu
            submenu = menu.addMenu('Switch value')
            agroup = QtGui.QActionGroup(submenu)
            values = node.trait('switch').trait_type.values
            value = node.switch
            set_index = -1
            for item in values:
                action = submenu.addAction(item)
                action.setCheckable(True)
                action.triggered.connect(SomaPartial(
                    self.set_switch_value, node, item))
                if item == value:
                    action.setChecked(True)

        if self.edition_enabled() \
                and node is not self.scene.pipeline.pipeline_node:
            menu.addSeparator()
            del_node_action = menu.addAction('Delete node')
            del_node_action.triggered.connect(self.del_node)
            export_mandatory_plugs = menu.addAction(
                'Export unconnected mandatory plugs')
            export_mandatory_plugs.triggered.connect(
                self.export_node_unconnected_mandatory_plugs)
            export_all_plugs = menu.addAction(
                'Export all unconnected plugs')
            export_all_plugs.triggered.connect(
                self.export_node_all_unconnected_plugs)
            export_mandatory_inputs = menu.addAction(
                'Export unconnected mandatory inputs')
            export_mandatory_inputs.triggered.connect(
                self.export_node_unconnected_mandatory_inputs)
            export_all_inputs = menu.addAction(
                'Export all unconnected inputs')
            export_all_inputs.triggered.connect(
                self.export_node_all_unconnected_inputs)
            export_mandatory_outputs = menu.addAction(
                'Export unconnected mandatory outputs')
            export_mandatory_outputs.triggered.connect(
                self.export_node_unconnected_mandatory_outputs)
            export_all_outputs = menu.addAction(
                'Export all unconnected outputs')
            export_all_outputs.triggered.connect(
                self.export_node_all_unconnected_outputs)

        # Added to choose to visualize optional parameters
        gnode = self.scene.gnodes[self.current_node_name]

        menu.addSeparator()
        show_opt_inputs = menu.addAction(
            'Show optional inputs')
        show_opt_inputs.setCheckable(True)
        show_opt_inputs.triggered.connect(
            self.show_optional_inputs
        )
        if gnode.show_opt_inputs:
            show_opt_inputs.setChecked(True)

        show_opt_outputs = menu.addAction(
            'Show optional outputs')
        show_opt_outputs.setCheckable(True)
        show_opt_outputs.triggered.connect(
            self.show_optional_outputs
        )
        if gnode.show_opt_outputs:
            show_opt_outputs.setChecked(True)

        menu.exec_(QtGui.QCursor.pos())
        del self.current_node_name
        del self.current_process

    def show_optional_inputs(self):
        '''
        Added to choose to visualize optional inputs.
        '''

        gnode = self.scene.gnodes[self.current_node_name]
        connected_plugs = []

        # The show_opt_inputs attribute is not changed yet
        if gnode.show_opt_inputs:
            # Verifying that the plugs are not connected to another node
            for param, pipeline_plug in six.iteritems(gnode.parameters):
                output = (not pipeline_plug.output if gnode.name in (
                    'inputs', 'outputs') else pipeline_plug.output)
                if not output:
                    if pipeline_plug.optional and pipeline_plug.links_from and gnode.show_opt_inputs:
                        connected_plugs.append(param)
            if connected_plugs:
                if len(connected_plugs) == 1:
                    text = "Please remove links from this plug:\n"
                else:
                    text = "Please remove links from these plugs:\n"
                for plug_name in connected_plugs:
                    text += plug_name + ", "
                text = text[:-2] + '.'

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
        '''
        Added to choose to visualize optional outputs.
        '''

        gnode = self.scene.gnodes[self.current_node_name]
        connected_plugs = []

        # The show_opt_outputs attribute is not changed yet
        if gnode.show_opt_outputs:
            # Verifying that the plugs are not connected to another node
            for param, pipeline_plug in six.iteritems(gnode.parameters):
                output = (not pipeline_plug.output if gnode.name in (
                    'inputs', 'outputs') else pipeline_plug.output)
                if output:
                    if pipeline_plug.optional and pipeline_plug.links_to and gnode.show_opt_outputs:
                        connected_plugs.append(param)
            if connected_plugs:
                if len(connected_plugs) == 1:
                    text = "Please remove links from this plug:\n"
                else:
                    text = "Please remove links from these plugs:\n"
                for plug_name in connected_plugs:
                    text += plug_name + ", "
                text = text[:-2] + '.'

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
        '''
        Open the right-click menu when triggered from the pipeline backround.
        '''
        self.click_pos = QtGui.QCursor.pos()
        has_dot = distutils.spawn.find_executable('dot')
        menu = QtGui.QMenu('Pipeline level menu', None)
        title = menu.addAction('Pipeline level menu')
        title.setEnabled(False)
        menu.addSeparator()

        if self.is_logical_view():
            logical_view = menu.addAction('Switch to regular parameters view')
        else:
            logical_view = menu.addAction('Switch to logical pipeline view')
        logical_view.triggered.connect(self.switch_logical_view)
        auto_node_pos = menu.addAction('Auto arrange nodes positions')
        auto_node_pos.triggered.connect(self.auto_dot_node_positions)
        if not has_dot:
            auto_node_pos.setEnabled(False)
            auto_node_pos.setText(
                'Auto arrange nodes positions (needs graphviz/dot tool '
                'installed)')
        init_node_pos = menu.addAction('Reset to initial nodes positions')
        init_node_pos.triggered.connect(self.reset_initial_nodes_positions)
        if not hasattr(self.scene.pipeline, 'node_position') \
                or len(self.scene.pipeline.node_position) == 0:
            init_node_pos.setEnabled(False)
            init_node_pos.setText(
                'Reset to initial nodes positions (none defined')
        save_dot = menu.addAction('Save image of pipeline graph')
        save_dot.triggered.connect(self.save_dot_image_ui)
        if not has_dot:
            save_dot.setEnabled(False)
            save_dot.setText(
                'Save image of pipeline graph (needs graphviz/dot tool '
                'installed)')
        menu.addSeparator()
        print_pos = menu.addAction('Print nodes positions')
        print_pos.triggered.connect(self.print_node_positions)

        if self._enable_edition:
            menu.addSeparator()
            add_proc = menu.addAction('Add process in pipeline')
            add_proc.triggered.connect(self.add_process)
            add_switch = menu.addAction('Add switch in pipeline')
            add_switch.triggered.connect(self.add_switch)
            add_optional_output_switch = menu.addAction(
                'Add optional output switch in pipeline')
            add_optional_output_switch.triggered.connect(
                self.add_optional_output_switch)
            add_iter_proc = menu.addAction('Add iterative process in pipeline')
            add_iter_proc.triggered.connect(self.add_iterative_process)

            menu.addSeparator()
            export_mandatory_plugs = menu.addAction(
                'Export unconnected mandatory plugs')
            export_mandatory_plugs.triggered.connect(
                self.export_unconnected_mandatory_plugs)
            export_all_plugs = menu.addAction(
                'Export all unconnected plugs')
            export_all_plugs.triggered.connect(
                self.export_all_unconnected_plugs)
            export_mandatory_inputs = menu.addAction(
                'Export unconnected mandatory inputs')
            export_mandatory_inputs.triggered.connect(
                self.export_unconnected_mandatory_inputs)
            export_all_inputs = menu.addAction(
                'Export all unconnected inputs')
            export_all_inputs.triggered.connect(
                self.export_all_unconnected_inputs)
            export_mandatory_outputs = menu.addAction(
                'Export unconnected mandatory outputs')
            export_mandatory_outputs.triggered.connect(
                self.export_unconnected_mandatory_outputs)
            export_all_outputs = menu.addAction(
                'Export all unconnected outputs')
            export_all_outputs.triggered.connect(
                self.export_all_unconnected_outputs)
            prune = menu.addAction('Prune unused pipeline plugs')
            prune.triggered.connect(self._prune_plugs)

            menu.addSeparator()
            new_pipeline = menu.addAction('New pipeline (clear current)')
            new_pipeline.triggered.connect(self.new_pipeline)
            load_pipeline = menu.addAction('Load pipeline (clear current)')
            load_pipeline.triggered.connect(self.load_pipeline)

        menu.addSeparator()
        save = menu.addAction('Save pipeline')
        save.triggered.connect(self.save_pipeline)

        menu.exec_(QtGui.QCursor.pos())
        del self.click_pos

    def enableNode(self, checked):
        self.scene.pipeline.nodes[self.current_node_name].enabled = checked

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

    def set_switch_value(self, switch, value, dummy):
        switch.switch = value

    def disable_done_steps(self):
        pipeline_tools.disable_runtime_steps_with_existing_outputs(
            self.scene.pipeline)

    def enable_all_steps(self):
        self.scene.pipeline.enable_all_pipeline_steps()

    def check_files(self):
        overwritten_outputs = pipeline_tools.nodes_with_existing_outputs(
            self.scene.pipeline)
        missing_inputs = pipeline_tools.nodes_with_missing_inputs(
            self.scene.pipeline)
        if len(overwritten_outputs) == 0 and len(missing_inputs) == 0:
            QtGui.QMessageBox.information(
                self, 'Pipeline ready', 'All input files are available. '
                'No output file will be overwritten.')
        else:
            dialog = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(dialog)
            warn_widget = PipelineFileWarningWidget(
                missing_inputs, overwritten_outputs)
            layout.addWidget(warn_widget)
            hlay = QtGui.QHBoxLayout()
            layout.addLayout(hlay)
            hlay.addStretch()
            ok = QtGui.QPushButton('OK')
            self.ok_button = ok
            hlay.addWidget(ok)
            ok.clicked.connect(dialog.close)
            dialog.show()
            self._warn_files_widget = dialog

    def auto_dot_node_positions(self):
        '''
        Calculate pipeline nodes positions using graphviz/dot, and place the
        pipeline view nodes accordingly.
        '''
        scene = self.scene
        scale = 67. # dpi
        nodes_sizes = dict([(name,
                             (gnode.boundingRect().width(),
                              gnode.boundingRect().height()))
                             for name, gnode in six.iteritems(scene.gnodes)])
        dgraph = pipeline_tools.dot_graph_from_pipeline(
            scene.pipeline, nodes_sizes=nodes_sizes)
        tfile, tfile_name = tempfile.mkstemp()
        os.close(tfile)
        pipeline_tools.save_dot_graph(dgraph, tfile_name)
        toutfile, toutfile_name = tempfile.mkstemp()
        os.close(toutfile)
        cmd = ['dot', '-Tplain', '-o', toutfile_name, tfile_name]
        subprocess.check_call(cmd)

        nodes_pos = self._read_dot_pos(toutfile_name)

        rects = dict([(name, node.boundingRect())
                      for name, node in six.iteritems(scene.gnodes)])
        pos = dict([(name, (-rects[name].width()/2 + pos[0]*scale,
                            -rects[name].height()/2 - pos[1]*scale))
                    for id, name, pos in nodes_pos])
        minx = min([x[0] for x in six.itervalues(pos)])
        miny = min([x[1] for x in six.itervalues(pos)])
        pos = dict([(name, (p[0] - minx, p[1] - miny))
                    for name, p in six.iteritems(pos)])
        print('pos:')
        print(pos)
        scene.pos = pos
        for node, position in six.iteritems(pos):
            gnode = scene.gnodes[node]
            if isinstance(position, Qt.QPointF):
                gnode.setPos(position)
            else:
                gnode.setPos(*position)

        os.unlink(tfile_name)
        os.unlink(toutfile_name)

    def _read_dot_pos(self, filename):
        '''
        Read the nodes positions from a file generated by graphviz/dot, in
        "plain" text format.

        Returns
        -------
        nodes_pos: dict
            keys are nodes IDs (names), and values are 2D positions
        '''
        fileobj = open(filename)
        nodes_pos = []
        if sys.version_info[0] >= 3:
            file_iter = fileobj.readlines()
        else:
            file_iter = fileobj.xreadlines()
        for line in file_iter:
            if line.startswith('node'):
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
            elif line.startswith('edge'):
                break
        return nodes_pos

    def save_dot_image_ui(self):
        '''
        Ask for a filename using the file dialog, and save a graphviz/dot
        representation of the pipeline.
        The pipeline representation follows the current visualization mode
        ("regular" or "logical" with smaller boxes) with one link of a given
        type (active, weak) between two given boxes: all parameters are not
        represented.
        '''
        filename = QtGui.QFileDialog.getSaveFileName(
            None, 'Save image of the pipeline', '',
            'Images (*.png *.xpm *.jpg *.ps *.eps);; All (*)')
        if filename:
            pipeline_tools.save_dot_image(self.scene.pipeline, filename)

    def reset_initial_nodes_positions(self):
        '''
        Set each pipeline node to its "saved" position, ie the one which may
        be found in the "node_position" variable of the pipeline.
        '''
        scene = self.scene
        pos = getattr(scene.pipeline, 'node_position')
        if pos is not None:
            scene.pos = pos
            for node, position in six.iteritems(pos):
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
        posdict = dict([(key, conv_pos(value)) \
                        for key, value in six.iteritems(self.scene.pos)])
        pprint(posdict)

    def del_node(self, node_name=None):
        pipeline = self.scene.pipeline
        if not node_name:
            node_name = self.current_node_name
        node = pipeline.nodes[node_name]
        # FIXME: should rather be in a method Pipeline.remove_node()
        for plug_name, plug in six.iteritems(node.plugs):
            if not plug.output:
                for link_def in list(plug.links_from):
                    src_node, src_plug = link_def[:2]
                    link_descr = '%s.%s->%s.%s' \
                        % (src_node, src_plug, node_name, plug_name)
                    pipeline.remove_link(link_descr)
            else:
                for link_def in list(plug.links_to):
                    dst_node, dst_plug = link_def[:2]
                    link_descr = '%s.%s->%s.%s' \
                        % (node_name, plug_name, dst_node, dst_plug)
                    pipeline.remove_link(link_descr)
        #pipeline.remove_node(node) # unfortunately this method doesn't exist
        del pipeline.nodes[node_name]
        if hasattr(node, 'process'):
            pipeline.list_process_in_pipeline.remove(node.process)
            pipeline.nodes_activation.on_trait_change(
                pipeline._set_node_enabled, node_name, remove=True)
            pipeline.nodes_activation.remove_trait(node_name)
        self.scene.remove_node(node_name)
        self.scene.pipeline.update_nodes_and_plugs_activation()

    def export_node_plugs(self, node_name, inputs=True, outputs=True,
                          optional=False):
        pipeline = self.scene.pipeline
        node = pipeline.nodes[node_name]
        for parameter_name, plug in six.iteritems(node.plugs):
            if parameter_name in ("nodes_activation", "selection_changed"):
                continue
            if (((node_name, parameter_name) not in pipeline.do_not_export and
                ((outputs and plug.output and not plug.links_to) or
                    (inputs and not plug.output and not plug.links_from)) and
                (optional or not node.get_trait(parameter_name).optional))):
                pipeline.export_parameter(node_name, parameter_name)

    def export_plugs(self, inputs=True, outputs=True, optional=False):
        for node_name in self.scene.pipeline.nodes:
            if node_name != "":
                self.export_node_plugs(node_name, inputs=inputs,
                                       outputs=outputs, optional=optional)

    def export_node_unconnected_mandatory_plugs(self):
        self.export_node_plugs(self.current_node_name)

    def export_node_all_unconnected_plugs(self):
        self.export_node_plugs(self.current_node_name, optional=True)

    def export_node_unconnected_mandatory_inputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=True, outputs=False)

    def export_node_all_unconnected_inputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=True, outputs=False, optional=True)

    def export_node_unconnected_mandatory_outputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=False, outputs=True)

    def export_node_all_unconnected_outputs(self):
        self.export_node_plugs(
            self.current_node_name, inputs=False, outputs=True, optional=True)

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

    class ProcessModuleInput(QtGui.QDialog):
        def __init__(self):
            super(PipelineDevelopperView.ProcessModuleInput, self).__init__()
            self.setWindowTitle('process module/name:')
            layout = QtGui.QGridLayout(self)
            layout.addWidget(QtGui.QLabel('module/process:'), 0, 0)
            self.proc_line = PipelineDevelopperView.ProcessNameEdit()
            layout.addWidget(self.proc_line, 0, 1)
            layout.addWidget(QtGui.QLabel('node name'), 1, 0)
            self.name_line = QtGui.QLineEdit()
            layout.addWidget(self.name_line, 1, 1)
            #hlay = QtGui.QHBoxLayout()
            #layout.addLayout(hlay, 1, 1)
            ok = QtGui.QPushButton('OK')
            layout.addWidget(ok, 2, 0)
            cancel = QtGui.QPushButton('Cancel')
            layout.addWidget(cancel, 2, 1)
            ok.clicked.connect(self.accept)
            cancel.clicked.connect(self.reject)

    def add_process(self):
        '''
        Insert a process node in the pipeline. Asks for the process
        module/name, and the node name before inserting.
        '''

        proc_name_gui = PipelineDevelopperView.ProcessModuleInput()
        proc_name_gui.resize(800, proc_name_gui.sizeHint().height())

        res = proc_name_gui.exec_()
        if res:
            proc_module = unicode(proc_name_gui.proc_line.text())
            node_name = str(proc_name_gui.name_line.text())
            pipeline = self.scene.pipeline
            try:
                process = get_process_instance(
                  unicode(proc_name_gui.proc_line.text()))
            except Exception as e:
                print(e)
                return
            pipeline.add_process(node_name, process)

            node = pipeline.nodes[node_name]
            gnode = self.scene.add_node(node_name, node)
            gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    class IterativeProcessInput(ProcessModuleInput):
        def __init__(self):
            super(PipelineDevelopperView.IterativeProcessInput,
                  self).__init__()
            #hlay = Qt.QHBoxLayout()
            #self.layout().addLayout(hlay)
            lay = self.layout()
            item = lay.itemAtPosition(2, 0)
            widget = item.widget()
            lay.removeItem(item)
            lay.addWidget(widget, 3, 0)
            item = lay.itemAtPosition(2, 1)
            widget = item.widget()
            lay.removeItem(item)
            lay.addWidget(widget, 3, 1)
            lay.addWidget(Qt.QLabel('iterative plugs:'), 2, 0)
            self.plugs = Qt.QListWidget()
            self.plugs.setEditTriggers(Qt.QListWidget.NoEditTriggers)
            self.plugs.setSelectionMode(Qt.QListWidget.ExtendedSelection)
            lay.addWidget(self.plugs, 2, 1)
            self.proc_line.textChanged.connect(self.set_plugs)
            #self.proc_line.editingFinished.connect(self.set_plugs)

        def set_plugs(self, text):
            self.plugs.clear()
            try:
                process = get_process_instance(text)
            except:
                return
            traits = process.user_traits().keys()
            self.plugs.addItems(traits)

        def iterative_plugs(self):
            return [item.text() for item in self.plugs.selectedItems()]

    def add_iterative_process(self):
        '''
        Insert an iterative process node in the pipeline. Asks for the process
        module/name, the node name, and iterative plugs before inserting.
        '''
        proc_name_gui = PipelineDevelopperView.IterativeProcessInput()
        proc_name_gui.resize(800, proc_name_gui.sizeHint().height())

        res = proc_name_gui.exec_()
        if res:
            proc_module = unicode(proc_name_gui.proc_line.text())
            node_name = str(proc_name_gui.name_line.text())
            pipeline = self.scene.pipeline
            try:
                process = get_process_instance(
                  unicode(proc_name_gui.proc_line.text()))
            except Exception as e:
                print(e)
                return
            iterative_plugs = proc_name_gui.iterative_plugs()
            do_not_export = process.user_traits().keys()
            pipeline.add_iterative_process(node_name, process, iterative_plugs,
                                           do_not_export=do_not_export)

            node = pipeline.nodes[node_name]
            gnode = self.scene.add_node(node_name, node)
            gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    def add_switch(self):
        '''
        Insert a switch node in the pipeline. Asks for the switch
        inputs/outputs, and the node name before inserting.
        '''

        class SwitchInput(QtGui.QDialog):
            def __init__(self):
                super(SwitchInput, self).__init__()
                self.setWindowTitle('switch parameters/name:')
                layout = QtGui.QGridLayout(self)
                layout.addWidget(QtGui.QLabel('inputs:'), 0, 0)
                self.inputs_line = QtGui.QLineEdit()
                layout.addWidget(self.inputs_line, 0, 1)
                layout.addWidget(QtGui.QLabel('outputs:'), 1, 0)
                self.outputs_line = QtGui.QLineEdit()
                layout.addWidget(self.outputs_line, 1, 1)
                layout.addWidget(QtGui.QLabel('node name'), 2, 0)
                self.name_line = QtGui.QLineEdit()
                layout.addWidget(self.name_line, 2, 1)
                ok = QtGui.QPushButton('OK')
                layout.addWidget(ok, 3, 0)
                cancel = QtGui.QPushButton('Cancel')
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

    def add_optional_output_switch(self):
        '''
        Insert an optional output switch node in the pipeline. Asks for the
        switch inputs/outputs, and the node name before inserting.
        '''

        class SwitchInput(QtGui.QDialog):
            def __init__(self):
                super(SwitchInput, self).__init__()
                self.setWindowTitle('switch parameters/name:')
                layout = QtGui.QGridLayout(self)
                layout.addWidget(QtGui.QLabel('input:'), 0, 0)
                self.inputs_line = QtGui.QLineEdit()
                layout.addWidget(self.inputs_line, 0, 1)
                layout.addWidget(QtGui.QLabel('output:'), 1, 0)
                self.outputs_line = QtGui.QLineEdit()
                layout.addWidget(self.outputs_line, 1, 1)
                layout.addWidget(QtGui.QLabel('node name'), 2, 0)
                self.name_line = QtGui.QLineEdit()
                layout.addWidget(self.name_line, 2, 1)
                ok = QtGui.QPushButton('OK')
                layout.addWidget(ok, 3, 0)
                cancel = QtGui.QPushButton('Cancel')
                layout.addWidget(cancel, 3, 1)
                ok.clicked.connect(self.accept)
                cancel.clicked.connect(self.reject)

        switch_name_gui = SwitchInput()
        switch_name_gui.resize(600, switch_name_gui.sizeHint().height())

        res = switch_name_gui.exec_()
        if res:
            pipeline = self.scene.pipeline
            node_name = str(switch_name_gui.name_line.text()).strip()
            input = str(switch_name_gui.inputs_line.text()).strip()
            output = str(switch_name_gui.outputs_line.text()).strip()
            if output == '' and node_name != '':
                output = node_name
            elif output != '' and node_name == '':
                node_name = output
            pipeline.add_optional_output_switch(node_name, input, output)
            # add_optional_output_switch does *not* trigger an update
            self._reset_pipeline()
            gnode = self.scene.gnodes[node_name]
            gnode.setPos(self.mapToScene(self.mapFromGlobal(self.click_pos)))

    def _plug_clicked(self, name):
        if self.is_logical_view() or not self.edition_enabled():
            # in logival view, links are not editable since they do not reflect
            # the details of reality
            return
        node_name, plug_name = str(name).split(':')
        plug_name = str(plug_name)
        gnode = self.scene.gnodes[node_name]
        plug = gnode.out_plugs.get(plug_name)
        if not plug:
            return # probably an input plug
        plug_pos = plug.mapToScene(plug.mapFromParent(plug.get_plug_point()))
        self._grabpos = self.mapFromScene(plug_pos)
        self._temp_link = Link(
            plug_pos,
            self.mapToScene(self.mapFromGlobal(QtGui.QCursor.pos())),
            True, False)
        self.scene.addItem(self._temp_link)

        self._grab_link = True
        self._grabbed_plug = (node_name, plug_name)

    def _move_grab_link(self, event):
        pos = self.mapToScene(event.pos())
        self._temp_link.update(self.mapToScene(self._grabpos), pos)

    def _release_grab_link(self, event):
        max_square_dist = 100.
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
            for source_dest, link in six.iteritems(self.scene.glinks):
                if link is item:
                    plug = source_dest[1]
                    break
            if plug is not None:
                # check the plug is not too far from the drop point
                gnode = self.scene.gnodes[plug[0]]
                gplug = gnode.in_plugs[plug[1]]
                plug_pos = gplug.mapToScene(
                    gplug.mapFromParent(gplug.get_plug_point()))
                pdiff = plug_pos - pos
                dist2 = pdiff.x() * pdiff.x() + pdiff.y() * pdiff.y()
                if dist2 > max_square_dist:
                    plug = None
        elif isinstance(item, Plug):
            plug = str(item.name).split(':')
        if plug is not None:
            if self._grabbed_plug[0] not in ('', 'inputs'):
                src = '%s.%s' % self._grabbed_plug
            else:
                src = self._grabbed_plug[1]
            if plug[0] not in ('', 'outputs'):
                dst = '%s.%s' % tuple(plug)
            else:
                dst = plug[1]
            self.scene.pipeline.add_link('%s->%s' % (src, dst))
            self.scene.update_pipeline()
        self._grabbed_plug = None

    def _link_clicked(self, src_node, src_plug, dst_node, dst_plug):
        src_node = str(src_node)
        src_plug = str(src_plug)
        dst_node = str(dst_node)
        dst_plug = str(dst_plug)
        if self.is_logical_view() or not self.edition_enabled():
            # in logical view, links are not real links
            return
        if src_node in ('', 'inputs'):
            src = src_plug
            snode = self.scene.pipeline.pipeline_node
        else:
            src = '%s.%s' % (src_node, src_plug)
            snode = self.scene.pipeline.nodes[src_node]
        if dst_node in ('', 'outputs'):
            dst = dst_plug
            dnode = self.scene.pipeline.pipeline_node
        else:
            dst = '%s.%s' % (dst_node, dst_plug)
            dnode = self.scene.pipeline.nodes[dst_node]
        name = '%s->%s' % (src, dst)
        self._current_link = name #(src_node, src_plug, dst_node, dst_plug)

        menu = QtGui.QMenu('Link: %s' % name)
        title = menu.addAction('Link: %s' % name)
        title.setEnabled(False)
        menu.addSeparator()

        weak = False
        splug = snode.plugs[src_plug]
        for link in splug.links_to:
            if link[0] == dst_node and link[1] == dst_plug:
                weak = link[4]
                break
        weak_action = menu.addAction('Weak link')
        weak_action.setCheckable(True)
        weak_action.setChecked(bool(weak))
        weak_action.toggled.connect(self._change_weak_link)

        menu.addSeparator()
        del_link = menu.addAction('Delete link')
        del_link.triggered.connect(self._del_link)

        menu.exec_(QtGui.QCursor.pos())
        del self._current_link

    def _change_weak_link(self, weak):
        #src_node, src_plug, dst_node, dst_plug = self._current_link
        link_def = self._current_link
        self.scene.pipeline.remove_link(link_def)
        self.scene.pipeline.add_link(link_def, weak_link=weak)
        self.scene.update_pipeline()

    def _del_link(self):
        # src_node, src_plug, dst_node, dst_plug = self._current_link
        link_def = self._current_link
        self.scene.pipeline.remove_link(link_def)
        self.scene.update_pipeline()

    def _plug_right_clicked(self, name):
        if self.is_logical_view() or not self.edition_enabled():
            # in logival view, links are not editable since they do not reflect
            # the details of reality
            return
        node_name, plug_name = str(name).split(':')
        plug_name = str(plug_name)
        if node_name in ('inputs', 'outputs'):
            plug = self.scene.pipeline.pipeline_node.plugs[plug_name]
        else:
            plug = self.scene.pipeline.nodes[node_name].plugs[plug_name]
        output = plug.output
        self._temp_plug = plug
        self._temp_plug_name = (node_name, plug_name)

        menu = QtGui.QMenu('Plug: %s' % name)
        title = menu.addAction('Plug: %s' % name)
        title.setEnabled(False)
        menu.addSeparator()

        if node_name not in ('inputs', 'outputs'):
            # not a main node: allow export
            if output:
                links = plug.links_to
            else:
                links = plug.links_from
            existing = False
            for link in links:
                if link[0] == '':
                    existing = True
                    break
            export_action = menu.addAction('export plug')
            export_action.triggered.connect(self._export_plug)
            if existing:
                export_action.setEnabled(False)

        else:
            del_plug = menu.addAction('Remove plug')
            del_plug.triggered.connect(self._remove_plug)
            edit_plug = menu.addAction('Rename / edit plug')
            edit_plug.triggered.connect(self._edit_plug)

        menu.exec_(QtGui.QCursor.pos())
        del self._temp_plug
        del self._temp_plug_name

    class _PlugEdit(QtGui.QDialog):
        def __init__(self, show_weak=True, parent=None):
            super(PipelineDevelopperView._PlugEdit, self).__init__(parent)
            layout = QtGui.QVBoxLayout(self)
            hlay1 = QtGui.QHBoxLayout()
            layout.addLayout(hlay1)
            hlay1.addWidget(QtGui.QLabel('Plug name:'))
            self.name_line = QtGui.QLineEdit()
            hlay1.addWidget(self.name_line)
            hlay2 = QtGui.QHBoxLayout()
            layout.addLayout(hlay2)
            self.optional = QtGui.QCheckBox('Optional')
            hlay2.addWidget(self.optional)
            if show_weak:
                self.weak = QtGui.QCheckBox('Weak link')
                hlay2.addWidget(self.weak)
            hlay3 = QtGui.QHBoxLayout()
            layout.addLayout(hlay3)
            ok = QtGui.QPushButton('OK')
            hlay3.addWidget(ok)
            cancel = QtGui.QPushButton('Cancel')
            hlay3.addWidget(cancel)
            ok.clicked.connect(self.accept)
            cancel.clicked.connect(self.reject)

    def _export_plug(self):
        dial = self._PlugEdit()
        dial.name_line.setText(self._temp_plug_name[1])
        dial.optional.setChecked(self._temp_plug.optional)

        res = dial.exec_()
        if res:
            self.scene.pipeline.export_parameter(
                self._temp_plug_name[0], self._temp_plug_name[1],
                pipeline_parameter=str(dial.name_line.text()),
                is_optional=dial.optional.isChecked(),
                weak_link=dial.weak.isChecked())
            self.scene.update_pipeline()

    def _remove_plug(self):
        if self._temp_plug_name[0] in ('inputs', 'outputs'):
            #print 'remove plug:', self._temp_plug_name[1]
            self.scene.pipeline.remove_trait(self._temp_plug_name[1])
            self.scene.update_pipeline()

    def _edit_plug(self):
        dial = self._PlugEdit(show_weak=False)
        dial.name_line.setText(self._temp_plug_name[1])
        dial.name_line.setEnabled(False) ## FIXME
        dial.optional.setChecked(self._temp_plug.optional)
        res = dial.exec_()
        if res:
            plug = self._temp_plug
            plug.optional = dial.optional.isChecked()

            #print 'TODO.'
            self.scene.update_pipeline()

    def _prune_plugs(self):
        pipeline = self.scene.pipeline
        pnode = pipeline.pipeline_node
        to_del = []
        for plug_name, plug in six.iteritems(pnode.plugs):
            if plug.output and len(plug.links_from) == 0:
                to_del.append(plug_name)
            elif not plug.output and len(plug.links_to) == 0:
                to_del.append(plug_name)
        for plug_name in to_del:
            pipeline.remove_trait(plug_name)
        self.scene.update_pipeline()

    def confirm_erase_pipeline(self):
        if len(self.scene.pipeline.nodes) <= 1:
            return True
        confirm = Qt.QMessageBox.warning(
            self,
            'New pipeline',
            'The current pipeline will be lost. Continue ?',
            Qt.QMessageBox.Ok | Qt.QMessageBox.Cancel,
            Qt.QMessageBox.Cancel)
        if confirm != Qt.QMessageBox.Ok:
            return False
        return True

    def new_pipeline(self):
        if not self.confirm_erase_pipeline():
            return
        w = Qt.QDialog(self)
        w.setWindowModality(Qt.Qt.WindowModal)
        w.setWindowTitle('Pipeline name')
        l = Qt.QVBoxLayout()
        w.setLayout(l)
        le = Qt.QLineEdit()
        l.addWidget(le)
        l2 = Qt.QHBoxLayout()
        l.addLayout(l2)
        ok = Qt.QPushButton('OK')
        l2.addWidget(ok)
        cancel = Qt.QPushButton('Cancel')
        l2.addWidget(cancel)
        ok.clicked.connect(w.accept)
        cancel.clicked.connect(w.reject)
        le.returnPressed.connect(w.accept)

        res = w.exec_()
        if res:
            class_kwargs = {
                '__module__': '__main__',
                'do_autoexport_nodes_parameters': False,
                'node_position': {}
            }
            pipeline_class = type(le.text(), (Pipeline,), class_kwargs)
            pipeline = pipeline_class()
            self.set_pipeline(pipeline)
            self._pipeline_filename = ''

    def load_pipeline(self):
        class LoadProcessUi(Qt.QDialog):
            def __init__(self, parent=None, old_filename=''):
                super(LoadProcessUi, self).__init__(parent)
                self.old_filename = old_filename
                lay = Qt.QVBoxLayout()
                self.setLayout(lay)
                l2 = Qt.QHBoxLayout()
                lay.addLayout(l2)
                l2.addWidget(Qt.QLabel('Pipeline:'))
                self.proc_edit = PipelineDevelopperView.ProcessNameEdit()
                l2.addWidget(self.proc_edit)
                self.loadbt = Qt.QPushButton('...')
                l2.addWidget(self.loadbt)
                l3 = Qt.QHBoxLayout()
                lay.addLayout(l3)
                ok = Qt.QPushButton('OK')
                l3.addWidget(ok)
                cancel = Qt.QPushButton('Cancel')
                l3.addWidget(cancel)
                ok.clicked.connect(self.accept)
                cancel.clicked.connect(self.reject)
                self.loadbt.clicked.connect(self.get_filename)
                self.proc_edit.returnPressed.connect(self.accept)

            def get_filename(self):
                filename = qt_backend.getOpenFileName(
                    None, 'Load the pipeline', self.old_filename,
                    'Compatible files (*.xml *.py);; All (*)')
                if filename:
                    self.proc_edit.setText(filename)

        if not self.confirm_erase_pipeline():
            return

        old_filename = getattr(self, '_pipeline_filename', '')
        dialog = LoadProcessUi(self, old_filename=old_filename)
        dialog.setWindowTitle('Load pipeline')
        dialog.setWindowModality(Qt.Qt.WindowModal)
        res = dialog.exec_()

        if res:
            filename = dialog.proc_edit.text()
            if filename:
                pipeline = get_process_instance(filename)
                if pipeline is not None:
                    self.set_pipeline(pipeline)
                    self._pipeline_filename = filename

    def save_pipeline(self):
        '''
        Ask for a filename using the file dialog, and save the pipeline as a
        XML or python file.
        '''
        pipeline = self.scene.pipeline
        old_filename = getattr(self, '_pipeline_filename', '')
        filename = qt_backend.getSaveFileName(
            None, 'Save the pipeline', old_filename,
            'Compatible files (*.xml *.py);; All (*)')
        if filename:
            posdict = dict([(key, (value.x(), value.y())) \
                            for key, value in six.iteritems(self.scene.pos)])
            old_pos = pipeline.node_position
            pipeline.node_position = posdict
            pipeline_tools.save_pipeline(pipeline, filename)
            self._pipeline_filename = unicode(filename)
            pipeline.node_position = old_pos

