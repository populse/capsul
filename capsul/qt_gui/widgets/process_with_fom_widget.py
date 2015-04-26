import json
from soma.qt_gui.qt_backend import QtGui, QtCore
from capsul.qt_gui.controller_widget import ControllerWidget
from soma.qt_gui.widgets.file_selection_widget import FileSelectionWidget
from traits.api import File, HasTraits, Any, Directory, Undefined


class ProcessWithFomWidget(QtGui.QWidget):
    """Process interface with FOM handling, and execution running"""
    def __init__(self, process_with_fom):
        """
        Parameters
        ----------
        process_with_fom: ProcessWithFom instance
            process with FOM to be displayed
        """
        super(ProcessWithFomWidget, self).__init__()
        self.setLayout( QtGui.QVBoxLayout() )
        self.process_with_fom = process_with_fom

        # To show output directory and select file
        self.lineedit_input = FileSelectionWidget(
            'File','Input file to guess attributes', 165)
        self.connect(self.lineedit_input,
            QtCore.SIGNAL("editChanged(const QString & )"), self.on_lineedit)
        self.lineedit_input.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))

        self.layout().addWidget(self.lineedit_input)
        if self.process_with_fom.study_config.input_fom \
                != self.process_with_fom.study_config.output_fom:
            self.lineedit_output = FileSelectionWidget(
                'File','Output file to guess attributes', 165)
            self.lineedit_output.setSizePolicy(QtGui.QSizePolicy(
                QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))
            self.layout().addWidget(self.lineedit_output)
            self.connect(self.lineedit_output,
                QtCore.SIGNAL("editChanged(const QString & )"),
                self.on_lineedit)

        # Scroll area to show attributs
        self.scroll_area2 = QtGui.QScrollArea( parent=self )
        self.scroll_area2.setWidgetResizable( True )
        self.scroll_area2.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred))
        self.layout().addWidget( self.scroll_area2 )

        # CheckBox to foms rules or not
        self.checkbox_fom = QtGui.QCheckBox('Follow FOM rules')
        self.checkbox_fom.setChecked(True)
        self.checkbox_fom.stateChanged.connect(self.on_checkbox_change)
        self.layout().addWidget(self.checkbox_fom)

        # Button Show/Hide completion
        self.btn_show_completion=QtGui.QPushButton('Show/Hide completion')
        self.layout().addWidget(self.btn_show_completion)
        self.btn_show_completion.clicked.connect(self.on_show_completion)

        # Scroll area to show completion
        self.scroll_area = QtGui.QScrollArea( parent=self )
        self.scroll_area.setWidgetResizable( True )
        self.scroll_area.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))
        self.layout().addWidget( self.scroll_area )

        # Create controller widget for process and object_attribute
        process = process_with_fom.process
        self.controller_widget = ControllerWidget( process, live=True,
            parent=self.scroll_area )
        self.controller_widget2=ControllerWidget( self.process_with_fom,
            live=True, parent=self.scroll_area2 )
        self.process_with_fom.on_trait_change(
            self.process_with_fom.attributes_changed, 'anytrait')

        # Set controller of attributs and controller of process for each
        # corresponding area
        self.scroll_area2.setWidget(self.controller_widget2)
        self.scroll_area.setWidget(self.controller_widget)
        #self.scroll_area.hide()

        io_lay = QtGui.QHBoxLayout()
        self.layout().addLayout(io_lay)
        self.btn_load_json = QtGui.QPushButton('Load Json')
        io_lay.addWidget(self.btn_load_json)
        self.btn_load_json.clicked.connect(self.on_btn_load_json)
        self.btn_save_json = QtGui.QPushButton('Save Json')
        io_lay.addWidget(self.btn_save_json)
        self.btn_save_json.clicked.connect(self.on_btn_save_json)

        self.btn_run=QtGui.QPushButton('Run', parent=self)
        self.btn_run.clicked.connect(self.on_run)
        self.layout().addWidget(self.btn_run)
        self.show_completion(False) # hide file parts

    def __del__(self):
        self.process_with_fom.on_trait_change(
            self.process_with_fom.attributes_changed, 'anytrait',
            remove=True)

    def on_lineedit(self, text):
        '''
        Input file path to guess FOM attributes changed: update FOM attributes
        '''
        print 'set attributes from path:', text
        self.process_with_fom.find_attributes(unicode(text))


    def on_btn_load_json(self):
        """Load attributes from a json file"""
        # ask for a file name
        filename = QtGui.QFileDialog.getOpenFileName(
            self, 'Select a .json FOM attributes file', '', '*.json')
        if filename is None:
            return
        print 'load', filename
        attributes = json.load(open(filename))
        print "loaded:", attributes
        for att, value in attributes.iteritems():
            if att in self.process_with_fom.attributes:
                setattr(self.process_with_fom, att, value)

    def on_btn_save_json(self):
        """Save attributes in a json file"""
        # ask for a file name
        filename = QtGui.QFileDialog.getSaveFileName(
            self, 'Select a .json FOM attributes file', '', '*.json')
        if filename is None:
            return
        json.dump(self.process_with_fom.attributes, open(filename, 'w'))

    def set_use_fom(self):
        '''
        Setup the FOM doing its job
        '''
        ret = QtGui.QMessageBox.critical(self, "Critical",
            'Going back to FOM rules will reset all path files. Are you sure?',
            QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)

        if ret == QtGui.QMessageBox.Ok:
            #reset attributs and trait of process
            process = self.process_with_fom.process
            self.process_with_fom.on_trait_change(
                self.process_with_fom.attributes_changed, 'anytrait')
            # WARNING: is it necessary to reset all this ?
            # create_completion() will do the job anyway ?
            for name, trait in process.user_traits().iteritems():
                if trait.is_trait_type(File) \
                        or trait.is_trait_type(Directory):
                    setattr(process,name, Undefined)
            self.process_with_fom.create_completion()

            print self.process_with_fom.attributes
            if self.lineedit_input.lineedit.text() != '':
                self.process_with_fom.find_attributes(
                    self.lineedit_input.lineedit.text())
            self.scroll_area2.show()

        else:
            self.checkbox_fom.setChecked(False)


    def on_checkbox_change(self, state):
        '''
        Use FOM checkbox callabck
        '''
        if state == QtCore.Qt.Checked:
            self.set_use_fom()
        else:
            self.scroll_area2.hide()
            self.process_with_fom.on_trait_change(
                self.process_with_fom.attributes_changed, 'anytrait',
                remove=True)

    def show_completion(self, visible=None):
        '''
        Show or hide completion (File, Directory, or Any parameters)

        Parameters
        ----------
        visible: bool (optional)
            show/hide. If None, switch the current visibility state.
        '''

        for control_name, control in \
                self.controller_widget._controls.iteritems():
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

    #Run excecution of the process
    def on_run(self):
        '''
        Run the process or pipeline
        '''
        print 'IN THE RUN FUNCTION'
        #To execute the process
        self.process()
        #How pass atributes
        # FIXME
        #self.study_config.save_run(self.process_with_fom.attributes,self.process)


