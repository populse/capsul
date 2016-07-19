
from __future__ import print_function

import json
import six
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.controller import Controller
from soma.qt_gui.controller_widget \
    import ControllerWidget, ScrollControllerWidget
from traits.api import File, HasTraits, Any, Directory, Undefined


class AttributedProcessWidget(QtGui.QWidget):
    """Process interface with attributes completion handling"""
    def __init__(self, attributed_process, enable_attr_from_filename=False,
                 enable_load_buttons=False):
        """
        Parameters
        ----------
        attributed_process: Process instance
            process with attributes to be displayed
        enable_attr_from_filename: bool (optional)
            if enabled, it will be possible to specify an input filename to
            build attributes from
        """
        super(AttributedProcessWidget, self).__init__()
        self.setLayout(QtGui.QVBoxLayout())
        self.attributed_process = attributed_process
        self._show_completion = False

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

        if enable_attr_from_filename and completion_engine is not None:
            c = Controller()
            c.add_trait('attributes_from_input_filename', File(optional=True))
            cw = ControllerWidget(c, live=True)
            spl_up.layout().addWidget(cw)
            self.input_filename_controller = c
            c.on_trait_change(self.on_input_filename_changed,
                              'attributes_from_input_filename', dispatch='ui')
            cw.setSizePolicy(QtGui.QSizePolicy.Expanding,
                             QtGui.QSizePolicy.Fixed)

        # groupbox area to show attributs
        attrib_widget = QtGui.QGroupBox('Attributes:')
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

        # groupbox area to show completion
        param_widget = QtGui.QGroupBox('Parameters:')
        param_widget.setAlignment(QtCore.Qt.AlignLeft)
        spl_down.layout().addWidget(param_widget)
        param_widget.setLayout(QtGui.QVBoxLayout())
        param_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)

        # Create controller widget for process and object_attribute
        self.controller_widget = ScrollControllerWidget(process, live=True,
            parent=param_widget)

        if completion_engine is not None:
            self.controller_widget2 = ScrollControllerWidget(
                completion_engine.get_attribute_values(),
                live=True, parent=attrib_widget)
            completion_engine.get_attribute_values().on_trait_change(
                completion_engine.attributes_changed, 'anytrait')
        else:
            self.controller_widget2 = ScrollControllerWidget(Controller())

        # Set controller of attributs and controller of process for each
        # corresponding area
        param_widget.layout().addWidget(self.controller_widget)
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

        if completion_engine is None:
            attrib_widget.hide()
            self.checkbox_fom.hide()
            self.btn_show_completion.hide()
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
                completion_engine.path_attributes(unicode(text))
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
            #reset attributs and trait of process
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

                if self.input_filename_controller.attributes_from_input_filename \
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
        Use completion checkbox callabck
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
        for control_name, control_groups in \
                six.iteritems(
                    self.controller_widget.controller_widget._controls):
            for group, control in six.iteritems(control_groups):
                trait, control_class, control_instance, control_label = control
                if not isinstance(trait.trait_type, File) \
                        and not isinstance(trait.trait_type, Any) \
                        and not isinstance(trait.trait_type, Directory):
                    continue
                control_instance.setVisible(visible)
                if isinstance(control_label, tuple):
                    for cl in control_label:
                        cl.setVisible(visible)
                else:
                    control_label.setVisible(visible)
        for group, group_widget in six.iteritems(
                self.controller_widget.controller_widget._groups):
            if [x for x in group_widget.hideable_widget.children()
                if isinstance(x, QtGui.QWidget) and not x.isHidden()]:
                group_widget.show()
            else:
                group_widget.hide()

    def on_show_completion(self, visible):
        '''
        Toggle the visibility of paths parameters
        '''
        self.show_completion(None)

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

