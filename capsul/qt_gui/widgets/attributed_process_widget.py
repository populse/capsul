# -*- coding: utf-8 -*-
'''
Process or pipeline parameters view with attributes handling.

Classes
=======
:class:`AttributedProcessWidget`
--------------------------------
'''

from __future__ import print_function

from __future__ import absolute_import
import json
import six
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.controller import Controller
from soma.qt_gui.controller_widget \
    import ControllerWidget, ScrollControllerWidget
from traits.api import File, HasTraits, Any, Directory, Undefined, List


class AttributedProcessWidget(QtGui.QWidget):
    """Process interface with attributes completion handling"""
    def __init__(self, attributed_process, enable_attr_from_filename=False,
                 enable_load_buttons=False, override_control_types=None,
                 separate_outputs=True, user_data=None, userlevel=0,
                 scroll=True):
        """
        Parameters
        ----------
        attributed_process: Process instance
            process with attributes to be displayed
        enable_attr_from_filename: bool (optional)
            if enabled, it will be possible to specify an input filename to
            build attributes from
        override_control_types: dict (optional)
            if given, this is a "factory" dict assigning new controller editor
            types to some traits types in the parameters controller.
        separate_outputs: bool
            if True, inputs and outputs (traits with output=True set) will
            be separated into two boxes.
        user_data: any type (optional)
            optional user data that can be accessed by individual control
            editors
        userlevel: int
            the current user level: some traits may be marked with a non-zero userlevel, and will only be visible if the ControllerWidget userlevel is more than (or equal) the trait level.
        scroll: bool
            if True, the widget includes scrollbars in the parameters and
            attributes sections when needed, otherwise it will be a fixed size
            widget.
        """
        super(AttributedProcessWidget, self).__init__()
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.attributed_process = attributed_process
        self._show_completion = False
        self.user_data = user_data
        self.separate_outputs = separate_outputs
        self._userlevel = userlevel

        process = attributed_process
        completion_engine = getattr(process, 'completion_engine', None)

        if completion_engine is not None:
            splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
            self.layout().addWidget(splitter)
            spl_up = QtGui.QWidget()
            spl_up.setLayout(QtGui.QVBoxLayout())
            splitter.addWidget(spl_up)
            spl_down = QtGui.QWidget()
            spl_down.setLayout(QtGui.QVBoxLayout())
            splitter.addWidget(spl_down)
        else:
            spl_up = self
            spl_down = self

        filename_widget = None
        if enable_attr_from_filename and completion_engine is not None:
            c = Controller()
            c.add_trait('attributes_from_input_filename', File(optional=True))
            filename_widget = ControllerWidget(c, live=True,
                                               user_data=user_data)
            spl_up.layout().addWidget(filename_widget)
            self.input_filename_controller = c
            c.on_trait_change(self.on_input_filename_changed,
                              'attributes_from_input_filename', dispatch='ui')
            filename_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                          QtGui.QSizePolicy.Fixed)

        # groupbox area to show attributes
        attrib_widget = QtGui.QGroupBox('Attributes:')
        attrib_widget.setFlat(True)
        attrib_widget.setAlignment(QtCore.Qt.AlignLeft)
        attrib_widget.setLayout(QtGui.QVBoxLayout())
        self.attrib_widget = attrib_widget
        spl_up.layout().addWidget(attrib_widget)
        attrib_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                    QtGui.QSizePolicy.Preferred)

        hlay = QtGui.QHBoxLayout()
        spl_up.layout().addLayout(hlay)
        # CheckBox to completion rules or not
        self.checkbox_fom = QtGui.QCheckBox('Follow completion rules')
        self.checkbox_fom.setChecked(True)
        self.checkbox_fom.stateChanged.connect(self.on_use_fom_change)
        hlay.addWidget(self.checkbox_fom)

        # Button Show/Hide completion
        self.btn_show_completion = QtGui.QCheckBox('Show completion')
        self.btn_show_completion.setSizePolicy(QtGui.QSizePolicy.Fixed,
                                               QtGui.QSizePolicy.Fixed)
        hlay.addWidget(self.btn_show_completion)
        self.btn_show_completion.stateChanged.connect(self.on_show_completion)

        params = QtGui.QWidget()
        playout = QtGui.QVBoxLayout()
        params.setLayout(playout)
        if scroll:
            scroll_a = QtGui.QScrollArea()
            scroll_a.setWidgetResizable(True)
            scroll_a.setWidget(params)
            spl_up.layout().addWidget(scroll_a)
            scroll_a.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                   QtGui.QSizePolicy.Preferred)
            params.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                 QtGui.QSizePolicy.Preferred)
            CWidgetClass = ScrollControllerWidget
        else:
            spl_up.layout().addWidget(params)
            CWidgetClass = ControllerWidget

        # groupbox area to show completion
        if separate_outputs:
            param_widget = QtGui.QGroupBox('Inputs:')
        else:
            param_widget = QtGui.QGroupBox('Parameters:')
        param_widget.setFlat(True)
        param_widget.setAlignment(QtCore.Qt.AlignLeft)
        playout.addWidget(param_widget)
        param_widget.setLayout(QtGui.QVBoxLayout())
        param_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        if separate_outputs:
            out_widget = QtGui.QGroupBox('Outputs:')
            out_widget.setFlat(True)
            out_widget.setAlignment(QtCore.Qt.AlignLeft)
            playout.addWidget(out_widget)
            out_widget.setLayout(QtGui.QVBoxLayout())
            out_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                     QtGui.QSizePolicy.Expanding)

        # use concise shape for lists GUI
        from  soma.qt_gui.controls import OffscreenListControlWidget
        control_types_a = {'List': OffscreenListControlWidget}
        control_types_p = {'List': OffscreenListControlWidget}
        if override_control_types:
            control_types_p.update(override_control_types)
        #ControllerWidget._defined_controls['List'] = OffscreenListControlWidget

        # Create controller widget for process and object_attribute
        sel = None
        if separate_outputs:
            sel = 'inputs'
        self.controller_widget = ControllerWidget(process, live=True,
            parent=param_widget, override_control_types=control_types_p,
            user_data=user_data, userlevel=userlevel, select_controls=sel)
        if separate_outputs:
            self.outputs_cwidget = ControllerWidget(process, live=True,
            parent=out_widget, override_control_types=control_types_p,
            user_data=user_data, userlevel=userlevel,
            select_controls='outputs')

        show_ce = (completion_engine is not None
                   and len(
                      completion_engine.get_attribute_values().user_traits())
                          != 0)

        if completion_engine is not None:
            self.controller_widget2 = CWidgetClass(
                completion_engine.get_attribute_values(),
                live=True, parent=attrib_widget,
                override_control_types=control_types_a, user_data=user_data,
                userlevel=userlevel)
            completion_engine.get_attribute_values().on_trait_change(
                completion_engine.attributes_changed, 'anytrait')
        else:
            self.controller_widget2 = CWidgetClass(
                Controller(), override_control_types=control_types_a,
                user_data=user_data, userlevel=userlevel)

        # Set controller of attributes and controller of process for each
        # corresponding area
        param_widget.layout().addWidget(self.controller_widget)
        if separate_outputs:
            out_widget.layout().addWidget(self.outputs_cwidget)
        attrib_widget.layout().addWidget(self.controller_widget2)

        if enable_load_buttons and completion_engine is not None:
            io_lay = QtGui.QHBoxLayout()
            self.layout().addLayout(io_lay)
            self.btn_load_json = QtGui.QPushButton('Load attributes')
            io_lay.addWidget(self.btn_load_json)
            self.btn_load_json.clicked.connect(self.on_btn_load_json)
            self.btn_save_json = QtGui.QPushButton('Save attributes')
            io_lay.addWidget(self.btn_save_json)
            self.btn_save_json.clicked.connect(self.on_btn_save_json)

        if not show_ce:
            if filename_widget:
                filename_widget.hide()
            attrib_widget.hide()
            self.checkbox_fom.hide()
            self.btn_show_completion.hide()
            if hasattr(self, 'btn_load_json'):
                self.btn_load_json.hide()
                self.btn_save_json.hide()
            self.show_completion(True) # hide file parts
        else:
            self.show_completion(False) # hide file parts

        if completion_engine is not None:
            completion_engine.on_trait_change(
                self._completion_progress_changed, 'completion_progress',
                dispatch='ui')

    def __del__(self):
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is not None:
            completion_engine.get_attribute_values().on_trait_change(
                completion_engine.attributes_changed, 'anytrait', remove=True)
            completion_engine.on_trait_change(
                self._completion_progress_changed, 'completion_progress',
                remove=True)

    @property
    def userlevel(self):
        return getattr(self, '_userlevel', 0)

    @userlevel.setter
    def userlevel(self, value):
        self._userlevel = value
        cw = getattr(self, 'controller_widget', None)
        if cw:
            cw.userlevel = value
        cw = getattr(self, 'outputs_cwidget', None)
        if cw:
            cw.userlevel = value
        cw = getattr(self, 'controller_widget2', None)
        if cw:
            cw.userlevel = value
        # re-hide file params if needed
        self.show_completion(self._show_completion)

    def on_input_filename_changed(self, text):
        '''
        Input file path to guess completion attributes changed: update
        attributes
        '''
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is not None:
            print('set attributes from path:', text)
            try:
                completion_engine.path_attributes(six.text_type(text))
            except ValueError as e:
                print(e)
                import traceback
                traceback.print_stack()


    def on_btn_load_json(self):
        """Load attributes from a json file"""
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is None:
            print('No completion engine with attributes in this process.')
            return
        # ask for a file name
        filename = qt_backend.getOpenFileName(
            self, 'Select a .json attributes file', '',
            'JSON files (*.json)')
        if filename is None:
            return
        print('load', filename)
        attributes = json.load(open(filename))
        print("loaded:", attributes)
        completion_engine.get_attribute_values().import_from_dict(attributes)

    def on_btn_save_json(self):
        """Save attributes in a json file"""
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is None:
            print('No attributes in this process.')
            return
        # ask for a file name
        filename = qt_backend.getSaveFileName(
            self, 'Select a .json attributes file', '',
            'JSON files (*.json)')
        if filename is None:
            return
        json.dump(completion_engine.get_attribute_values().export_to_dict(),
                  open(filename, 'w'))

    def set_use_fom(self):
        '''
        Setup the FOM doing its job
        '''
        ret = QtGui.QMessageBox.critical(self, "Critical",
            'Going back to completion rules will reset all path files. '
            'Are you sure?',
            QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)

        if ret == QtGui.QMessageBox.Ok:
            #reset attributes and trait of process
            process = self.attributed_process
            completion_engine = getattr(self.attributed_process,
                                       'completion_engine', None)
            if completion_engine is None:
                return
            completion_engine.get_attribute_values().on_trait_change(
                completion_engine.attributes_changed, 'anytrait')
            try:
                # WARNING: is it necessary to reset all this ?
                # create_completion() will do the job anyway ?
                #for name, trait in six.iteritems(process.user_traits()):
                    #if trait.is_trait_type(File) \
                            #or trait.is_trait_type(Directory):
                        #setattr(process,name, Undefined)
                completion_engine.complete_parameters()

                if hasattr(self, 'input_filename_controller') \
                        and self.input_filename_controller. \
                            attributes_from_input_filename \
                        != '':
                    completion_engine.path_attributes(
                        self.input_filename_controller.attributes_from_input_filename)
            except Exception as e:
                print(e)
                import traceback
                traceback.print_stack()
            self.attrib_widget.show()

        else:
            # reset it in a timer callback, otherwise the checkbox state is not
            # correctly recorded, and next time its state change will not
            # trigger the on_use_fom_change slot.
            QtCore.QTimer.singleShot(0, self._reset_fom_checkbox)


    def _reset_fom_checkbox(self):
        self.checkbox_fom.setChecked(False)

    def on_use_fom_change(self, state):
        '''
        Use completion checkbox callback
        '''
        if state == QtCore.Qt.Checked:
            self.set_use_fom()
        else:
            self.attrib_widget.hide()
            completion_engine = getattr(self.attributed_process,
                                        'completion_engine', None)
            if completion_engine is not None:
                completion_engine.get_attribute_values().on_trait_change(
                    completion_engine.attributes_changed, 'anytrait',
                    remove=True)
                self.btn_show_completion.setChecked(True)

    def show_completion(self, visible=None):
        '''
        Show or hide completion (File, Directory, or Any parameters)

        Parameters
        ----------
        visible: bool (optional)
            show/hide. If None, switch the current visibility state.
        '''

        if visible is None:
            visible = not self._show_completion
        self._show_completion = visible
        cwidgets = [self.controller_widget]
        if self.separate_outputs:
            cwidgets.append(self.outputs_cwidget)
        for controller_widget in cwidgets:
            for control_name, control_groups in \
                    six.iteritems(
                        controller_widget._controls):
                for group, control in six.iteritems(control_groups):
                    trait, control_class, control_instance, control_label \
                        = control
                    if not isinstance(trait.trait_type,
                                      (File, Any, Directory)) \
                            and (not isinstance(trait.trait_type, List)
                                or not isinstance(
                                    trait.inner_traits[0].trait_type,
                                    (File, Directory, Any))):
                        continue
                    if trait.forbid_completion:
                        # when completion is disable, parameters are always
                        # visible
                        is_visible = True
                    else:
                        hidden = trait.hidden \
                              or (trait.userlevel is not None
                                  and trait.userlevel > self.userlevel)
                        is_visible = visible and not hidden
                    control_instance.setVisible(is_visible)
                    if isinstance(control_label, tuple):
                        for cl in control_label:
                            cl.setVisible(is_visible)
                    else:
                        control_label.setVisible(is_visible)
            for group, group_widget in six.iteritems(
                    controller_widget._groups):
                if [x for x in group_widget.hideable_widget.children()
                    if isinstance(x, QtGui.QWidget) and not x.isHidden()]:
                    group_widget.show()
                else:
                    group_widget.hide()

    def on_show_completion(self, visible):
        '''
        Toggle the visibility of paths parameters
        '''
        self.show_completion(visible)

    def _completion_progress_changed(self, obj, name, old, new):
        completion_engine = getattr(self.attributed_process,
                                    'completion_engine', None)
        if completion_engine is not None:
            if not hasattr(self, 'progressdialog'):
                self.progressdialog = QtGui.QWidget()
                self.layout().insertWidget(1, self.progressdialog)
                layout = QtGui.QHBoxLayout()
                self.progressdialog.setLayout(layout)
                layout.addWidget(QtGui.QLabel('Completion progress:'))
                self.progressbar = QtGui.QProgressBar()
                layout.addWidget(self.progressbar)
                self.progressbar.setRange(0, 100)
            value = int(round(100 * completion_engine.completion_progress
                        / completion_engine.completion_progress_total))
            self.progressbar.setValue(value)
            if value != 100:
                self.progressdialog.show()
                QtGui.qApp.processEvents()
            else:
                self.progressdialog.hide()
