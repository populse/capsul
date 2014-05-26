from soma.qt_gui.qt_backend import QtGui, QtCore
from soma.pipeline.study import Study
import glob
import json
import os
import collections
from soma.gui.file_selection import FileAttributeSelection
try:
    from traits.api import HasTraits,File
except ImportError:
    from enthought.traits.api import HasTraits,File

class ProcessDatabaseWidget(QtGui.QDialog):
    def __init__(self,process):
        super(ProcessDatabaseWidget, self).__init__()
        self.process = process
        self.vbox = QtGui.QVBoxLayout()
        self.table = QtGui.QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.vbox.addWidget(self.table)
        self.Study = Study.get_instance()
        self.setLayout(self.vbox)
        self.sub = collections.OrderedDict()
        self.list_subjects = []
        self.dico_btn_launch_json = {}
        self.first_subject = 0
        self.process_name = process.name
        self.add_header()
        self.add_subjects_on_table()


    def add_header(self):
        col = self.table.columnCount()
        self.table.setColumnCount(col + 1)
        self.table.setHorizontalHeaderItem(col,
            QtGui.QTableWidgetItem('JSONFILE'))
        col = self.table.columnCount()
        self.table.setColumnCount(col + 1)
        self.table.setHorizontalHeaderItem(col,
            QtGui.QTableWidgetItem('Subject'))
        for name, trait in self.process.user_traits().iteritems():
            if trait.is_trait_type(File) is True:
                if trait.output is True:
                #and trait.hidden is not True:
                    col = self.table.columnCount()
                    self.table.setColumnCount(col + 1)
                    self.table.setHorizontalHeaderItem(col,
                        QtGui.QTableWidgetItem(name))


    def add_subjects_on_table(self):
        self.get_subjects()
        for key in self.sub:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)

            #self.table.setColumnCount( 0 )
            #col = self.table.columnCount()
            #print 'col',col

            #if row==0:
                #self.table.setHorizontalHeaderItem(0,QtGui.QTableWidgetItem('JSONFILE'))
                #self.first_subject=0
            #else:
                #self.first_subject=1
            btn_launch_json = QtGui.QPushButton('launch json')
            btn_launch_json.clicked.connect(self.on_launch_json)
            self.dico_btn_launch_json[btn_launch_json] \
                = self.sub[key]['jsonfile']
            self.table.setCellWidget(row, 0, btn_launch_json)
            self.table.setItem(row, 1, QtGui.QTableWidgetItem(key))
            self.list_subjects.append(key)
            col=2
            for key2 in self.sub[key]['output']:
                if os.path.exists(self.sub[key]['output'][key2]) is True:
                    self.table.setItem(row, col, QtGui.QTableWidgetItem())
                    self.table.item(row, col).setBackground(
                        QtGui.QColor(50,205,50))
                else:
                    self.table.setItem(row, col, QtGui.QTableWidgetItem())
                    self.table.item(row, col).setBackground(
                        QtGui.QColor(238,64,0))
                col=col+1

        self.check_subjets_not_used()


    def check_subjets_not_used(self):
        file_selection = FileAttributeSelection()
        selector_class = file_selection.find_selector(self.Study.input_fom,
            'unused', ['unused'])
        if selector_class:
            a = selector_class(directory=self.Study.input_directory)
        else:
            return
        #print a.attributes['subject']
        for ele in a.attributes:
            if ele['subject'] not in self.list_subjects:
                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                col = self.table.columnCount()
                self.table.setItem(row, 0, QtGui.QTableWidgetItem('NOT'))
                self.table.setItem(row, 1,
                    QtGui.QTableWidgetItem(ele['subject']))
                for num_col in range(2, self.table.columnCount()):
                    self.table.setItem(row, num_col, QtGui.QTableWidgetItem())
                    self.table.item(row, num_col).setBackground(
                        QtGui.QColor(190,190,190))


    def on_launch_json(self):
        sender = self.sender()
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(self.dico_btn_launch_json[sender]))


    def get_directories(self):
        #get output directory
        for path in os.listdir(self.Study.output_directory):
            if not os.path.isfile(os.path.join(
                    self.Study.output_directory,path)):
                yield os.path.join(self.Study.output_directory,path)


    def get_json_files(self):
        for directory in self.get_directories():
            for json_file in glob.glob(directory+os.sep+'*.json'):
                if self.process_name in os.path.basename(json_file):
                    yield json_file


    def get_subjects(self):
        for json_file in self.get_json_files():
            self.load(json_file)


    def load(self,json_file):
        try:
            with open(json_file, 'r') as json_data:
                data = json.load(
                    json_data,object_pairs_hook=collections.OrderedDict)
                #print data['run']['attributes']['subject']
                self.sub[data['run']['attributes']['subject']] \
                    = collections.OrderedDict()
                self.sub[data['run']['attributes']['subject']]['output'] \
                    = data['run']['output']
                self.sub[data['run']['attributes']['subject']]['jsonfile'] \
                    = json_file

        #No file to load
        except IOError:
            pass
