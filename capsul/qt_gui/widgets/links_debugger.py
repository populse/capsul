##########################################################################
# CAPSUL - Copyright (C) CEA, 2015
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import tempfile
import re

# Soma import
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui, QtCore

# capsul import
from capsul.pipeline import pipeline


class CapsulLinkDebuggerView(QtGui.QWidget):
    """ A Widget to display the links propagation when values are set in a
    pipeline
    """
    CAUSE = 1
    PLUG = 2
    PROPAGATE = 3
    VALUE = 4

    def __init__(self, pipeline, ui_file=None, record_file=None, parent=None):
        super(CapsulLinkDebuggerView, self).__init__(parent)

        # load the user interface window
        if ui_file is None:
            ui_file = os.path.join(
                os.path.dirname(__file__), "links_debugger.ui")

        self.ui = qt_backend.loadUi(ui_file)
        table_header = self.ui.links_table.horizontalHeader()
        table_header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        table_header_v = self.ui.links_table.verticalHeader()
        table_header_v.setResizeMode(QtGui.QHeaderView.ResizeToContents)

        if record_file is None:
            record_file_s = tempfile.mkstemp()
            record_file = record_file_s[1]
            os.close(record_file_s[0])
            print 'temporary record file:', record_file
            class AutoDeleteFile(object):
                def __init__(self, record_file):
                    self.record_file = record_file
                def __del__(self):
                    try:
                        os.unlink(self.record_file)
                    except:
                        pass
            self._autodelete_record_file = AutoDeleteFile(record_file)

        self.record_file = record_file
        self.pipeline = None
        self.set_pipeline(pipeline)
        self.update_links_view()
        self.ui.links_table.cellClicked.connect(self.activateCell)

    def __del__(self):
        self.release_pipeline()

    def show(self):
        """ Shows the widget and its child widgets.
        """
        self.ui.show()

    def set_pipeline(self, pipeline):
        if self.pipeline is not None:
            self.release_pipeline()
        self.pipeline = pipeline
        pipeline.uninstall_links_debug_handler()
        pipeline.install_links_debug_handler(
            log_file=open(self.record_file, 'w'), handler=None, prefix='')

    def release_pipeline(self):
        if self.pipeline is not None:
            self.pipeline.uninstall_links_debug_handler()
        self.pipeline = None

    def update_links_view(self):
        self.ui.links_table.clearContents()
        l = 0
        f = open(self.record_file)
        lines = f.readlines()
        self.ui.links_table.setRowCount(len(lines))
        linkre = re.compile('^value link: from: ([^ ,]+) *to: ([^ ]+) *, value: ([^ ]+).*$')
        links_orgs = {}
        for line in lines:
            match = linkre.match(line)
            if match:
                link_source = match.group(1)
                link_dest = match.group(2)
                plug_value = match.group(3)
                self.ui.links_table.setItem(
                    l, 0, QtGui.QTableWidgetItem('%d' % l))
                self.ui.links_table.setItem(
                    l, self.PLUG, QtGui.QTableWidgetItem(link_source))
                self.ui.links_table.setItem(
                    l, self.PROPAGATE, QtGui.QTableWidgetItem(link_dest))
                self.ui.links_table.setItem(
                    l, self.VALUE, QtGui.QTableWidgetItem(plug_value))
                links_orgs.setdefault(link_dest, []).append(l)
                l += 1
        self.links_orgs = links_orgs
        for l in xrange(len(lines)):
            item = self.ui.links_table.item(l, self.PLUG)
            if item is None:
                continue
            plug_name = unicode(item.text())
            if plug_name in links_orgs:
                org = links_orgs[plug_name][0]
                self.ui.links_table.setItem(
                    l, self.CAUSE,
                    QtGui.QTableWidgetItem(self.ui.links_table.item(org, 2)))

    def activateCell(self, row, column):
        if self.ui.links_table.item(row, column) is None:
            return
        if column == self.CAUSE:
            self.go_previous(row)
        elif column == self.PLUG:
            self.highlight_plug(row)
        elif column == self.PROPAGATE:
            self.go_next(row)
        elif column == self.VALUE:
            self.highlight_value(row)

    def go_previous(self, row):
        self.ui.links_table.clearSelection()
        plug = self.ui.links_table.item(row, self.PLUG)
        plug.setSelected(True)
        self.ui.links_table.item(row, self.CAUSE).setSelected(True)
        items = self.ui.links_table.findItems(
            plug.text(), QtCore.Qt.MatchExactly)
        for item in items:
            if item.column() == self.PROPAGATE:
                item.setSelected(True)

    def go_next(self, row):
        self.ui.links_table.clearSelection()
        next_item = self.ui.links_table.item(row, self.PROPAGATE)
        next_item.setSelected(True)
        items = self.ui.links_table.findItems(
            next_item.text(), QtCore.Qt.MatchExactly)
        for item in items:
            if item.column() == self.PLUG:
                item.setSelected(True)

    def highlight_plug(self, row):
        self.ui.links_table.clearSelection()
        plug = self.ui.links_table.item(row, self.PLUG)
        plug.setSelected(True)
        items = self.ui.links_table.findItems(
            plug.text(), QtCore.Qt.MatchExactly)
        for item in items:
            if item.column() in (self.CAUSE, self.PROPAGATE):
                item.setSelected(True)

    def highlight_value(self, row):
        self.ui.links_table.clearSelection()
        value_item = self.ui.links_table.item(row, self.VALUE)
        value_item.setSelected(True)
        items = self.ui.links_table.findItems(
            value_item.text(), QtCore.Qt.MatchExactly)
        for item in items:
            if item.column() == self.VALUE:
                item.setSelected(True)


