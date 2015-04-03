##########################################################################
# CAPSUL - Copyright (C) CEA, 2015
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from soma.qt_gui.qt_backend import QtCore, QtGui
try:
    import traits.api as traits
except ImportError:
    import enthought.traits.api as traits


class PipelineFileWarningWidget(QtGui.QSplitter):

    def __init__(self, missing_inputs, overwritten_outputs, parent=None):
        super(PipelineFileWarningWidget, self).__init__(
            QtCore.Qt.Vertical, parent)
        splitter = self
        widget1 = QtGui.QWidget(splitter)
        layout1 = QtGui.QVBoxLayout(widget1)
        widget2 = QtGui.QWidget(splitter)
        layout2 = QtGui.QVBoxLayout(widget2)
        label = QtGui.QLabel()
        layout1.addWidget(label)

        text = '<h1>Pipeline file parameters problems</h1>\n'

        if len(missing_inputs) == 0:
            text += '<h2>Inputs: OK</h2>\n' \
                '<p>All input file are present.</p>\n'
            label.setText(text)
        else:
            text += '<h2>Inputs: missing files</h2>\n'
            label.setText(text)

            table = QtGui.QTableWidget()
            layout1.addWidget(table)
            table.setColumnCount(3)
            sizes = [len(l) for node, l in missing_inputs.iteritems()]
            table.setRowCount(sum(sizes))
            table.setHorizontalHeaderLabels(
                ['node', 'parameter', 'filename'])
            row = 0
            for node_name, items in missing_inputs.iteritems():
                for param_name, file_name in items:
                    if not file_name or file_name is traits.Undefined:
                        file_name = '<temp. file>'
                    table.setItem(row, 0, QtGui.QTableWidgetItem(node_name))
                    table.setItem(row, 1,
                                  QtGui.QTableWidgetItem(param_name))
                    table.setItem(row, 2, QtGui.QTableWidgetItem(file_name))
                    row += 1
            table.setSortingEnabled(True)
            table.resizeColumnsToContents()

        label_out = QtGui.QLabel()
        layout2.addWidget(label_out)
        if len(overwritten_outputs) == 0:
            text = '<h2>Outputs: OK</h2>\n' \
                '<p>No output file will be overwritten.</p>\n'
            label_out.setText(text)
        else:
            text = '<h2>Outputs: overwritten files</h2>\n'
            label_out.setText(text)

            table = QtGui.QTableWidget()
            layout2.addWidget(table)
            table.setColumnCount(3)
            sizes = [len(l) for node, l in overwritten_outputs.iteritems()]
            table.setRowCount(sum(sizes))
            table.setHorizontalHeaderLabels(
                ['node', 'parameter', 'filename'])
            row = 0
            for node_name, items in overwritten_outputs.iteritems():
                for param_name, file_name in items:
                    if not file_name or file_name is traits.Undefined:
                        file_name = '<temp. file>'
                    table.setItem(row, 0, QtGui.QTableWidgetItem(node_name))
                    table.setItem(row, 1,
                                  QtGui.QTableWidgetItem(param_name))
                    table.setItem(row, 2, QtGui.QTableWidgetItem(file_name))
                    row += 1
            table.setSortingEnabled(True)
            table.resizeColumnsToContents()

