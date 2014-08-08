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
from functools import partial

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.utils.functiontools import SomaPartial


class BoolCreateWidget(object):

    @staticmethod
    def is_valid_trait(trait):
        return True

    @staticmethod
    def create_widget(parent, name, trait, value):
        attribute_widget = QtGui.QCheckBox(parent)
        label = trait.label
        if not label:
            label = name
        if label is not None:
            label_widget = QtGui.QLabel(label, parent)
        else:
            label_widget = None
        return (attribute_widget, label_widget)

    @staticmethod
    def update_controller(controller_widget, name, attribute_widget):
        setattr(controller_widget.controller, name,
                bool(attribute_widget.isChecked()))

    @staticmethod
    def update_controller_widget(controller_widget, name, attribute_widget, label_widget):
        attribute_widget.setChecked(
            getattr(controller_widget.controller, name, False))

    @classmethod
    def connect_controller(cls, controller_widget, name, attribute_widget, label_widget):
        widget_hook = partial(
            cls.update_controller, controller_widget, name, attribute_widget)
        attribute_widget.connect(attribute_widget, QtCore.SIGNAL('clicked()'),
                                 widget_hook)
        controller_hook = SomaPartial(
            cls.update_controller_widget, controller_widget, name, attribute_widget, label_widget)
        controller_widget.controller.on_trait_change(
            controller_hook, name=name)
        attribute_widget._controller_connections = (
            widget_hook, controller_hook)

    @staticmethod
    def disconnect_controller(controller_widget, name, attribute_widget, label_widget):
        widget_hook, controller_hook = attribute_widget._controller_connections
        controller_widget.controller.on_trait_change(
            controller_hook, name=name, remove=True)
        attribute_widget.disconnect(attribute_widget, QtCore.SIGNAL('clicked()'),
                                    widget_hook)
        del attribute_widget._controller_connections
