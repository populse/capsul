
from __future__ import print_function

import json
import six
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.controller import Controller
from soma.qt_gui.controller_widget \
    import ControllerWidget, ScrollControllerWidget
from traits.api import File, HasTraits, Any, Directory, Undefined
from soma.functiontools import SomaPartial


class AttributedProcessWidget(QtGui.QWidget):
    """Process interface with FOM handling, and execution running"""
    def __init__(self, attributed_process, enable_attr_from_filename=False,
                 enable_load_buttons=False):
        """
        Parameters
        ----------
        attributed_process: Process instance
            process with attributes to be displayed
        enable_attr_from_filename: bool (optional)
            if enabled, it will be possible to specify an input filename to
            build FOM attributes from
        """
        super(AttributedProcessWidget, self).__init__()
        self.setLayout(QtGui.QVBoxLayout())
        self.attributed_process = attributed_process

        process = attributed_process
        completion_engine = getattr(process, 'completion_engine', None)

        if enable_attr_from_filename and completion_engine is not None:
            c = Controller()
            c.add_trait('attributes_from_input_filename', File(optional=True))
            cw = ControllerWidget(c, live=True)
            self.layout().addWidget(cw)
            self.input_filename_controller = c
            c.on_trait_change(self.on_input_filename_changed,
                              'attributes_from_input_filename')
            cw.setSizePolicy(QtGui.QSizePolicy.Expanding,
                             QtGui.QSizePolicy.Fixed)

            #if self.attributed_process.study_config.input_fom \
                    #!= self.attributed_process.study_config.output_fom:
                #c.add_trait('attributes_from_output_filename', File())
                #c.on_trait_change(self.on_input_filename_changed,
                                  #'attributes_from_output_filename')

        # groupbox area to show attributs
        attrib_widget = QtGui.QGroupBox('Attributes:')
        attrib_widget.setAlignment(QtCore.Qt.AlignLeft)
        attrib_widget.setLayout(QtGui.QVBoxLayout())
        self.attrib_widget = attrib_widget
        self.layout().addWidget(attrib_widget)
        attrib_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                    QtGui.QSizePolicy.Preferred)

        hlay = QtGui.QHBoxLayout()
        self.layout().addLayout(hlay)
        # CheckBox to foms rules or not
        self.checkbox_fom = QtGui.QCheckBox('Follow FOM rules')
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
        self.layout().addWidget(param_widget)
        param_widget.setLayout(QtGui.QVBoxLayout())
        param_widget.setSizePolicy(QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)

        # Create controller widget for process and object_attribute
        self.controller_widget = ScrollControllerWidget(process, live=True,
            parent=param_widget)

        if completion_engine is not None:
            self.controller_widget2 = ScrollControllerWidget(
                completion_engine.get_attribute_values(process),
                live=True, parent=attrib_widget)
            completion_engine.get_attribute_values(process).on_trait_change(
                SomaPartial(completion_engine.attributes_changed, process),
                'anytrait')
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

    def __del__(self):
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is not None:
            completion_engine.get_attribute_values(
                self.attributed_process).on_trait_change(
                    SomaPartial(completion_engine.attributes_changed,
                                self.attributed_process),
                    'anytrait', remove=True)

    def on_input_filename_changed(self, text):
        '''
        Input file path to guess FOM attributes changed: update FOM attributes
        '''
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is not None:
            print('set attributes from path:', text)
            try:
                completion_engine.path_attributes(self.attributed_process,
                                                 unicode(text))
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
            self, 'Select a .json FOM attributes file', '',
            'JSON files (*.json)')
        if filename is None:
            return
        print('load', filename)
        attributes = json.load(open(filename))
        print("loaded:", attributes)
        completion_engine.get_attribute_values(
            self.attributed_process).import_from_dict(attributes)

    def on_btn_save_json(self):
        """Save attributes in a json file"""
        completion_engine = getattr(self.attributed_process,
                                   'completion_engine', None)
        if completion_engine is None:
            print('No attributes in this process.')
            return
        # ask for a file name
        filename = qt_backend.getSaveFileName(
            self, 'Select a .json FOM attributes file', '',
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
            'Going back to FOM rules will reset all path files. Are you sure?',
            QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)

        if ret == QtGui.QMessageBox.Ok:
            #reset attributs and trait of process
            process = self.attributed_process
            completion_engine = getattr(self.attributed_process,
                                       'completion_engine', None)
            if completion_engine is None:
                return
            completion_engine.get_attribute_values(
                process).on_trait_change(
                    SomaPartial(completion_engine.attributes_changed,
                                self.attributed_process), 'anytrait')
            try:
                # WARNING: is it necessary to reset all this ?
                # create_completion() will do the job anyway ?
                #for name, trait in six.iteritems(process.user_traits()):
                    #if trait.is_trait_type(File) \
                            #or trait.is_trait_type(Directory):
                        #setattr(process,name, Undefined)
                completion_engine.complete_parameters(process)

                print(completion_engine.get_attribute_values(
                      process).export_to_dict())
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
        Use FOM checkbox callabck
        '''
        if state == QtCore.Qt.Checked:
            self.set_use_fom()
        else:
            self.attrib_widget.hide()
            completion_engine = getattr(self.attributed_process,
                                      'completion_engine', None)
            if completion_engine is not None:
                completion_engine.get_attribute_values(
                    self.attributed_process).on_trait_change(
                        SomaPartial(completion_engine.attributes_changed,
                                    self.attributed_process),
                        'anytrait', remove=True)
                self.btn_show_completion.setChecked(True)

    def show_completion(self, visible=None):
        '''
        Show or hide completion (File, Directory, or Any parameters)

        Parameters
        ----------
        visible: bool (optional)
            show/hide. If None, switch the current visibility state.
        '''

        for control_name, control in \
                six.iteritems(
                    self.controller_widget.controller_widget._controls):
            trait, control_class, control_instance, control_label = control
            if not isinstance(trait.trait_type, File) \
                    and not isinstance(trait.trait_type, Any) \
                    and not isinstance(trait.trait_type, Directory):
                continue
            if visible is None:
                visible = not control_instance.isVisible()
            control_instance.setVisible(visible)
            if isinstance(control_label, tuple):
                for cl in control_label:
                    cl.setVisible(visible)
            else:
                control_label.setVisible(visible)

    def on_show_completion(self):
        '''
        Toggle the visibility of paths parameters
        '''
        self.show_completion(None)


