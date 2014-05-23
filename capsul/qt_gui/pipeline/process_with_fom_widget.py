from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.application import Application
from soma.gui.widget_controller_creation import ControllerWidget
import collections
from soma.gui.icon_factory import IconFactory
from soma.qt_gui.widgets.file_selection_widget import FileSelectionWidget
from soma.qt4gui.api import TimeredQLineEdit
from soma.pipeline.study import Study
try:
    from traits.api import File,HasTraits
except ImportError:
    from enthought.traits.api import File,HasTraits

class ProcessWithFomWidget(QtGui.QWidget):
    """Process interface with FOM handling, and execution running"""
    def __init__(self, process_with_fom, process):
        super(ProcessWithFomWidget, self).__init__()
        self.Study = Study.get_instance()
        self.setLayout( QtGui.QVBoxLayout() )
        # Get the object process (SimpMorpho)
        self.process_with_fom = process_with_fom
        self.process = process

        # To show output directory and select file
        self.lineedit_input = FileSelectionWidget(
            'File','File for attributes input', 165)
        self.connect(self.lineedit_input,
            QtCore.SIGNAL("editChanged(const QString & )"), self.on_lineedit)
        self.lineedit_input.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))

        self.layout().addWidget(self.lineedit_input)
        if self.Study.input_fom != self.Study.output_fom:
            self.lineedit_output = FileSelectionWidget(
                'File','File for attributes output', 165)
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
        self.controller_widget = ControllerWidget( self.process, live=True,
            parent=self.scroll_area )
        self.controller_widget2=ControllerWidget( self.process_with_fom,
            live=True, parent=self.scroll_area2 )
        self.process_with_fom.on_trait_change(
            self.process_with_fom.attributes_changed, 'anytrait')

        # Set controller of attributs and controller of process for each
        # corresponding area
        self.scroll_area2.setWidget(self.controller_widget2)
        self.scroll_area.setWidget(self.controller_widget)
        self.scroll_area.hide()

        self.btn_save_json=QtGui.QPushButton('Save Json')
        self.layout().addWidget(self.btn_save_json)
        self.btn_save_json.clicked.connect(self.on_btn_save_json)

        self.btn_run=QtGui.QPushButton('RUN', parent=self)
        self.btn_run.clicked.connect(self.on_run)
        self.layout().addWidget(self.btn_run)


    def on_lineedit(self,text):
        print 'text',text
        self.process_with_fom.find_attributes(text)


    def on_btn_save_json(self):
        """Save results in a json file"""
        print 'on btn save json'
        #if the user wants to save with a diffent name
        #QtGui.QFileDialog.getSaveFileName(self, 'Select a .json study','', '*.json')
        #if not self.Study.runs.keys():
            #name_run='run1'
        #else:
            #number=len(self.Study.runs.keys())+1
            #name_run='run'+str(number)
        #self.Study.runs[name_run]=collections.OrderedDict()
        #self.Study.runs[name_run]['process_name']='morphologistSimp.SimplifiedMorphologist'
        #self.Study.inc_nb_run_process('morphologistSimp.SimplifiedMorphologist' )
        #self.Study.runs[name_run]['fom_name']=self.object_attribute.fom_name
        #self.Study.runs[name_run]['attributs']={}
        #self.Study.runs[name_run]['attributs']={}
        #for key in self.object_attribute.dictionnary_attributes:
            #self.Study.runs[name_run]['attributs'][key]=self.object_attribute.dictionnary_attributes[key]
        #self.Study.runs[name_run]['output']={}
        #for name, trait in self.process.user_traits().iteritems():
            #if trait.output is True:
                #self.Study.runs[name_run]['output'][name]=getattr(self.process,name)
        #self.Study.save()


    def message_box_critical(self):
        ret = QtGui.QMessageBox.critical(self, "Critical",
            'Going back to FOM rules will reset all path files. Are you sure?',
            QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)

        if ret == QtGui.QMessageBox.Ok:
            #reset attributs and trait of process
            self.process_with_fom.on_trait_change(
                self.process_with_fom.attributes_changed, 'anytrait')
            for name,trait in self.process.user_traits().iteritems():
                if trait.is_trait_type(File):
                    setattr(self.process,name, '')
            self.process_with_fom.create_completion()

            print self.process_with_fom.attributes
            if self.lineedit_input.lineedit.text() != '':
                self.process_with_fom.find_attributes(
                    self.lineedit_input.lineedit.text())
            self.scroll_area2.show()

        else:
            self.checkbox_fom.setChecked(False)


    def on_checkbox_change(self,state):
       if state == QtCore.Qt.Checked:
           self.message_box_critical()
       else:
           self.scroll_area2.hide()
           self.process_with_fom.on_trait_change(
              self.process_with_fom.attributes_changed, 'anytrait',
              remove=True)


    def on_show_completion(self):
        if self.scroll_area.isHidden() is True:
            self.scroll_area.show()
        else:
            self.scroll_area.hide()


    #Run excecution of the process
    def on_run(self):
        print 'IN THE RUN FUNCTION'
        #To execute the process
        self.process()
        #How pass atributes
        self.Study.save_run(self.process_with_fom.attributes,self.process)


