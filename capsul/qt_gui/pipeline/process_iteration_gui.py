from soma.qt_gui.qt_backend import QtGui, QtCore,QtSql
from soma.application import Application
#from morphologistSimp import SimpMorpho
from soma.gui.file_selection import FileAttributeSelection
from soma.controller import trait_ids
from capsul.process import get_process_instance
from capsul.process.process_with_fom import ProcessWithFom
from capsul.study_config.study_config2 import StudyConfig
from soma.gui.widget_controller_creation import ControllerWidget
from functools import partial
import os
from soma.qt4gui.api import TimeredQLineEdit
try:
    from traits.api import File
except ImportError:
    from enthought.traits.api import File


class ProcessIterationGui(QtGui.QWizardPage):
    """Interface for process execution on many subjects"""
    def __init__(self, study_config):
        super(ProcessIterationGui, self).__init__()
        self.list_simple_process = {}
        self.list_process = {}
        self.list_attributs = {}
        self.dico_btn_delete = {}
        self.dico_header = {}
        self.list_subjects_selected = []
        self.study_config = study_config
        #Need object_attribute to create headser
        #self.object_attribute=object_attribute
        self.first_subject_add = 0
        self.list_filename = []
        self.vbox = QtGui.QVBoxLayout()

        # To add subjects
        self.add_subjects = QtGui.QPushButton('Add Subjects')
        self.add_subjects.clicked.connect(self.on_add_subjects)
        self.vbox.addWidget(self.add_subjects)
        self.setLayout(self.vbox)

    #To enebale the button next of QWizardPage or not
    #def isComplete(self):
        #print 'si complet'
        #if self.list_subjects_selected is None:
            #return False
        #else:
            #return True


    def on_add_header(self):
        # The view for the QSqlTableModel
        self.table = QtGui.QTableWidget(1, 1)
        self.vbox.addWidget(self.table)
        num_col = 0
        for key in sorted(self.pwd.attributes):
            self.table.insertColumn(num_col)
            self.table.setHorizontalHeaderItem(num_col,
                QtGui.QTableWidgetItem(key))
            self.dico_header[key]=num_col
            num_col = num_col + 1
        self.table.setHorizontalHeaderItem(num_col,
            QtGui.QTableWidgetItem('delete'))


    def on_add_subjects(self):
        """ Add a subject in the database and create Attributes and process
        objects for each
        """
        file_selection = FileAttributeSelection()
        selection = file_selection.select(self.study_config.input_fom,
            'unused',
            [ 'unused' ], self.study_config.input_directory)
        if selection is None:
            return
        for i in range(0, len(selection)):
            self.new_sub = selection[i]
            if self.new_sub['subject'] in self.list_subjects_selected:
                print 'subjects already in the base'
                pass
            else:
                self.list_subjects_selected.append(self.new_sub['subject'])
                #import morphologistSimp
                self.pwd = ProcessWithFom(self.get_process(),
                    self.study_config)
                self.pwd.attributes = self.new_sub


                #If first subject add, add header of QTable
                if self.first_subject_add == 0:
                    self.on_add_header()
                    self.first_subject_add = 1

                # Just list to have values of attributes and check if
                # something is wrong
                liste=[]
                for key in sorted(self.pwd.attributes):
                    liste.append(self.pwd.attributes[key])
                # If only filename probably error in the filename (TODO:
                # better to raise ValueError in the fom if subject not good)
                if len(liste)==0:
                    print "no attributes - something wrong?"
                    self.list_subjects_selected.pop()
                    return

                #if len(self.list_subjects_selected) > 1:
                self.table.insertRow(len(self.list_subjects_selected)-1)

                for a in range(0, len(liste)):
                    self.table.setItem(len(self.list_subjects_selected)-1, a,
                        QtGui.QTableWidgetItem(liste[a]))
                btn_delete = QtGui.QPushButton('Delete')
                self.dico_btn_delete[btn_delete] \
                    = len(self.list_subjects_selected)-1
                btn_delete.clicked.connect(self.on_del_subjects)
                self.table.setCellWidget(len(self.list_subjects_selected)-1,
                    len(liste), btn_delete)


    def on_del_subjects(self):
        sender = self.sender()
        the_item = self.table.item(self.dico_btn_delete[sender],
            self.dico_header['subject'])
        the_i = the_item.text()
        self.table.removeRow(self.dico_btn_delete[sender])
        #print 'wha,',self.table.item(self.dico_btn_delete[sender],0)

        self.list_subjects_selected.remove(the_i)
        del self.dico_btn_delete[sender]

        #Remove list subejct
        self.update_dico_btn_delete()


    def update_dico_btn_delete(self):
        for row in range(0, len(self.list_subjects_selected)):
            it = self.table.cellWidget(row,self.table.columnCount()-1)
            if it in self.dico_btn_delete:
                self.dico_btn_delete[it] = row


    def get_process(self):
        """This will be automatic"""
        return get_process_instance(str(self.study_config.process))



class ProcessParametersTable(QtGui.QWizardPage):
    def __init__(self, process, process_with_fom):
        super(ProcessParametersTable, self).__init__()
        self.list_subjects_selected = []
        #self.list_subjects_selected_prec=None
        self.process = process
        self.process_with_fom = process_with_fom
        self.dict_parameters = {}
        self.dict_default_value = {}
        self.vbox = QtGui.QVBoxLayout()
        self.table = QtGui.QTableWidget(1, 1)
        self.table.setHorizontalHeaderItem(0,
            QtGui.QTableWidgetItem('Subjects'))
        #self.table.contextMenuEvent.connect(self.mousePressEvent)
        #self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.table.customContextMenuRequested.connect(self.mousePressEvent)
        #self.connect(self.table,QtCore.SIGNAL('mousePressEvent'),self.mousePressEvent)
        self.vbox.addWidget(self.table)
        self.setLayout(self.vbox)

        header_horizontal = 1
        for trait in self.process.user_traits():
            if self.process.trait(trait).is_trait_type(File) is False:
                #for trait_id in trait_ids(self.process.trait(trait)):
                    self.table.insertColumn(header_horizontal)
                    self.dict_parameters[trait] \
                        = [trait_ids(self.process.trait(trait))[0],
                            self.process.trait(trait).handler.values,
                            self.process.trait(trait).default ]
                    #print self.dict_parameters[trait]
                    self.dict_default_value[trait] \
                        = self.process.trait(trait).default
                    self.table.setHorizontalHeaderItem(
                        header_horizontal,QtGui.QTableWidgetItem(trait))
                    header_horizontal = header_horizontal+1


    #def mousePressEvent(self, event):
        #row = self.table.rowAt(event.y())
        #col = self.table.rowAt(event.x())
        #self.popMenu = QtGui.QMenu( self )
        #toolbar = QtGui.QToolBar()
        #self.actionDefaultValue = toolbar.addAction("Default value", self.on_back_default_value)
        #self.popMenu.addAction( self.actionDefaultValue )
        #self.popMenu.exec_( self.table.mapToGlobal(event) )


    def combo_parameter_changed(self, trait, text):
        conv_value = type(trait.default)(text)
        setattr(self.process, trait, conv_value)


    def checkbox_parameter_changed(self,trait,state):
        if state == 0:
            setattr(self.process, trait, False)
        else:
            setattr(self.process, trait, True)


    def on_back_default_value(self):
        print 'on back default value'
        #print '1 - d value',self.dict_default_value[trait]
        #print '2 - d value',self.process.trait(trait).default


    def del_element_on_table(self,element):
        items = self.table.findItems(element, QtCore.Qt.MatchExactly)
        #it's sure that the len of items is 1!
        print items
        if items:
            self.table.removeRow(items[0].row())


    def add_element_on_table(self,list_add_element):
        for ele in list_add_element:
            nb_row = self.table.rowCount()
            self.table.insertRow(nb_row)
            self.table.setItem(nb_row, 0, QtGui.QTableWidgetItem(ele))
            nb_param = 1
            for trait in self.process.user_traits():
                if self.process.trait(trait).is_trait_type(File) is False:
                    self.table.setCellWidget(nb_row,nb_param,
                        self.trait_parameter_to_widget(
                            trait, self.dict_parameters[trait][0],
                            self.dict_parameters[trait][1],
                            self.dict_parameters[trait][2]))
                    nb_param = nb_param+1


    def go(self):
        nb_sub = 0
        for sub in self.list_subjects_selected:
            if nb_sub == 0:
                pass
            else:
                self.table.insertRow(nb_sub)
            self.table.setItem(nb_sub, 0, QtGui.QTableWidgetItem(sub))
            nb_param = 1
            for trait in self.process.user_traits():
                if self.process.trait(trait).is_trait_type(File) is False:
                    self.table.setCellWidget(nb_sub,nb_param,
                        self.trait_parameter_to_widget(
                            trait, self.dict_parameters[trait][0],
                            self.dict_parameters[trait][1],
                            self.dict_parameters[trait][2]))
                    nb_param = nb_param+1
            nb_sub = nb_sub+1


    def trait_parameter_to_widget(
            self, trait, type_trait, all_value, default_value):
        if type_trait == 'Enum':
            wid = QtGui.QComboBox()
            for val in all_value:
                wid.addItem(str(val))
                #wid.currentIndexChanged.connect(self.parameter_changed)
            self.connect(wid,QtCore.SIGNAL(
                "currentIndexChanged(const QString &)"),
                partial(self.combo_parameter_changed, trait))
            #return wid
        elif type_trait == 'Bool':
            wid = QtGui.QCheckBox()
            wid.setChecked(default_value)
            self.connect(wid,QtCore.SIGNAL("stateChanged(int)"),
                partial(self.checkbox_parameter_changed, trait))
            #wid.stateChanged.connect(self.parameter_changed)
        else:
            wid = None
        return wid


