


# System import
import logging
import sys

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.functiontools import partial

# Capsul import 
#from capsul.qtgui.controller_widget import ControllerWidget


class ControllerControlWidget(object):

    """Class for instance trait"""
    @staticmethod
    def is_valid_trait(trait):
        return True

    @classmethod
    def create_widget(cls, parent, name, trait, sub_controller):
        label = getattr(trait, 'label', None)
        if not label:
            label = name
        if label is not None:
            control_label = QtGui.QLabel(label, parent)
        else:
            control_label = None

        btn_expand = QtGui.QPushButton(parent)
        #btn_expand.setIcon( QtGui.QIcon( IconFactory()._imageExpand ) )

        scroll_area = QtGui.QScrollArea(parent=parent)
        scroll_area.setWidgetResizable(True)
        # scroll_area.setSizePolicy( QtGui.QSizePolicy( QtGui.QSizePolicy.Expanding,
        # QtGui.QSizePolicy.Expanding ) )
        sub_controller_widget = ControllerWidget(sub_controller,
                                                 parent=scroll_area)
        scroll_area.setWidget(sub_controller_widget)
        # sub_controller_widget.setSizePolicy( QtGui.QSizePolicy( QtGui.QSizePolicy.Expanding,
        # QtGui.QSizePolicy.MinimumExpanding ) )
        scroll_area.setFrameShape(QtGui.QFrame.StyledPanel)
        expand_hook = partial(cls.expand_collapse, scroll_area)
        btn_expand.connect(btn_expand, QtCore.SIGNAL('clicked()'),
                           expand_hook)
        control_instance = scroll_area
        control_instance.btn_expand = btn_expand
        control_instance.control_label = control_label
        control_instance.expand_hook = expand_hook
        scroll_area.hide()
        control_instance.controller_widget = sub_controller_widget
        return (control_instance, (control_label, btn_expand))

    @staticmethod
    def update_controller(controller_widget, name, control_instance):
        control_instance.controller_widget.update_controller()

    @staticmethod
    def update_controller_widget(controller_widget, name, control_instance, control_label):
        control_instance.controller_widget.update_controller_widget()

    @staticmethod
    def connect_controller(controller_widget, name, control_instance, control_label):
        control_instance.controller_widget.connect_controller()

    @staticmethod
    def disconnect_controller(controller_widget, name, control_instance, control_label):
        control_instance.controller_widget.disconnect_controller()

    @staticmethod
    def expand_collapse(control_instance):
        if control_instance.isVisible():
            control_instance.hide()
            #control_instance.btn_expand.setIcon( QtGui.QIcon( IconFactory()._imageExpand ) )
        else:
            control_instance.show()
            #control_instance.btn_expand.setIcon( QtGui.QIcon( IconFactory()._imageCollapse ) )
