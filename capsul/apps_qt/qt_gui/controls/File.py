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


class FileCreateWidget(object):

    @staticmethod
    def is_valid_trait(trait):
        return True

    @classmethod
    def create_widget(cls, parent, name, trait, value):
        text_widget, label_widget = StrCreateWidget.create_widget(
            parent, name, trait, value)
        attribute_widget = QtGui.QWidget(parent)
        horizontal_layout = QtGui.QHBoxLayout(attribute_widget)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.addWidget(text_widget)
        attribute_widget.text_widget = text_widget

        btn_browse = QtGui.QPushButton(attribute_widget)
        # if trait.output is True:
        #    btn_browse.setIcon( QtGui.QIcon( IconFactory()._imageBrowseOutput) )
        # if trait.output is False:
        #    btn_browse.setIcon( QtGui.QIcon( IconFactory()._imageBrowseInput) )
        # if trait(name).is_trait_type( Directory):
        #  btn_browse.setIcon( QtGui.QIcon( IconFactory()._imageBrowseDir) )
        horizontal_layout.addWidget(btn_browse)
        btn_browse.setFixedSize(20, 20)
        attribute_widget.btn_browse = btn_browse
        attribute_widget._browse_hook = partial(
            cls.file_dialog, parent, name, attribute_widget)
        attribute_widget.btn_browse.clicked.connect(
            attribute_widget._browse_hook)

        viewers = getattr(parent.controller, 'viewers', None)
        if viewers and name in viewers:
            btn_viewer = QtGui.QPushButton(attribute_widget)
            horizontal_layout.addWidget(btn_viewer)
            btn_viewer.setFixedSize(20, 20)
            #btn_viewer.setIcon( QtGui.QIcon( IconFactory()._imageViewer ) )
            attribute_widget.btn_viewer = btn_viewer
            if hasattr(parent.controller, 'call_viewer'):
                viewer_hook = partial(
                    parent.controller.call_viewer, parent, name)
                attribute_widget._viewer_hook = viewer_hook
                attribute_widget.btn_viewer.clicked.connect(viewer_hook)
        return (attribute_widget, label_widget)

    @staticmethod
    def file_dialog(parent, name, attribute_widget):
        if hasattr( parent.controller.user_traits()[name], 'output' ) \
                and parent.controller.user_traits()[name].output:
            outputfile = True
        else:
            outputfile = False
        if sipconfig.Configuration().sip_version >= 0x040a00:
            #/nfs/neurospin/cati/cati_shared/MEMENTO/CONVERTED/001/0010020_LAFR/M000/MRI/3DT1/0010020_LAFR_M000_3DT1_S002.nii.gz
                #''
            if not outputfile:
                value = QtGui.QFileDialog.getOpenFileName(parent, 'Select a file', '/home/mb236582/datafom/subjects/subject02/t1mri/default_acquisition/subject02.nii', '',
                                                          options=QtGui.QFileDialog.DontUseNativeDialog)
            else:
                value = QtGui.QFileDialog.getSaveFileName(parent, 'Select a file', '/home/mb236582/datafom/subjects/subject02/t1mri/default_acquisition/subject02.nii', '',
                                                          options=QtGui.QFileDialog.DontUseNativeDialog)
        else:
            if outputfile:
                value = QtGui.QFileDialog.getOpenFileName(self._widget, 'Select a file', '', '',
                                                          0, QtGui.QFileDialog.DontUseNativeDialog)
            else:
                value = QtGui.QFileDialog.getSaveFileName(self._widget, 'Select a file', '', '',
                                                          0, QtGui.QFileDialog.DontUseNativeDialog)
        setattr(parent.controller, name, unicode(value))

    @staticmethod
    def update_viewer(controller_widget, name, attribute_widget):
        if hasattr(controller_widget.controller, 'viewers'):
            if name in controller_widget.controller.viewers:
                try:
                    open(getattr(controller_widget.controller, name))
                    attribute_widget.btn_viewer.setEnabled(True)
                except IOError:
                    attribute_widget.btn_viewer.setEnabled(False)

    @staticmethod
    def update_controller(controller_widget, name, attribute_widget):
        """GUI modified so update traits"""
        StrCreateWidget.update_controller(
            controller_widget, name, attribute_widget.text_widget)
        #StrCreateWidget.update_controller( controller_widget, name, attribute_widget)

    @staticmethod
    def update_controller_widget(controller_widget, name, attribute_widget, label_widget):
        """Traits modified so update GUI"""
        StrCreateWidget.update_controller_widget(
            controller_widget, name, attribute_widget.text_widget, label_widget)
        #StrCreateWidget.update_controller_widget( controller_widget, name, attribute_widget, label_widget )

        # To disable viewer if file doesn't exist
        # if controller_widget.controller.trait( name ).viewer is not None:
        if hasattr(controller_widget.controller, 'viewers'):
            if name in controller_widget.controller.viewers:
                try:
                    open(getattr(controller_widget.controller, name))
                    attribute_widget.btn_viewer.setEnabled(True)
                except IOError:
                    attribute_widget.btn_viewer.setEnabled(False)

    @classmethod
    def connect_controller(cls, controller_widget, name, attribute_widget, label_widget):
        #StrCreateWidget.connect_controller( controller_widget, name, attribute_widget.text_widget, label_widget )
        StrCreateWidget.connect_controller(
            controller_widget, name, attribute_widget.text_widget, label_widget)

        # Function call when traits change to update if viewer enabled or not
        controller_hook = SomaPartial(
            cls.update_viewer, controller_widget, name, attribute_widget)
        controller_widget.controller.on_trait_change(controller_hook, name)

        attribute_widget._controller_connections = controller_hook

    @staticmethod
    def disconnect_controller(controller_widget, name, attribute_widget, label_widget):
        controller_hook = attribute_widget._controller_connections
        controller_widget.controller.on_trait_change(
            controller_hook, name, remove=True)
        StrCreateWidget.disconnect_controller(
            controller_widget, name, attribute_widget.text_widget, label_widget)
        del attribute_widget._controller_connections

