# -*- coding: utf-8 -*-
'''
Tool to debug and understand process / pipeline parameters links

Classes
=======
:class:`CapsulLinkDebuggerView`
-------------------------------
'''

from __future__ import print_function

# System import
from __future__ import absolute_import
import os
import tempfile
import re

# Soma import
from soma.qt_gui import qt_backend
from soma.qt_gui.qt_backend import QtGui, QtCore


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
        self.ui.help.hide()
        self.ui.help.setParent(None)
        self.help_geom = None
        table_header = self.ui.links_table.horizontalHeader()
        table_header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        table_header_v = self.ui.links_table.verticalHeader()
        table_header_v.setResizeMode(QtGui.QHeaderView.ResizeToContents)

        if record_file is None:
            record_file_s = tempfile.mkstemp()
            record_file = record_file_s[1]
            os.close(record_file_s[0])
            print('temporary record file:', record_file)
            class AutoDeleteFile(object):
                def __init__(self, record_file):
                    self.record_file = record_file
                def __del__(self):
                    try:
                        os.unlink(self.record_file)
                    except OSError:
                        pass
            self._autodelete_record_file = AutoDeleteFile(record_file)

        self.record_file = record_file
        self.pipeline = None
        self.set_pipeline(pipeline)
        self.update_links_view()
        self.ui.links_table.cellClicked.connect(self.activateCell)
        self.ui.actionPrevious.activated.connect(self.go_previous_line)
        self.ui.actionNext.activated.connect(self.go_next_line)
        self.ui.actionFollow.activated.connect(self.go_follow_link)
        self.ui.actionRefresh.activated.connect(self.update_links_view)
        self.ui.actionClear.activated.connect(self.clear_view)
        self.ui.actionHelp.activated.connect(self.help)


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
        record_stream = pipeline.install_links_debug_handler(
            log_file=open(self.record_file, 'w'), handler=None, prefix='')
        self.record_stream = record_stream

    def release_pipeline(self):
        if self.pipeline is not None:
            self.pipeline.uninstall_links_debug_handler()
        self.pipeline = None

    def update_links_view(self):
        self.ui.links_table.clearContents()
        self.ui.links_table.setRowCount(0)  # IMPORTANT otherwise perf drops
        table_header = self.ui.links_table.horizontalHeader()
        table_header.setResizeMode(QtGui.QHeaderView.Interactive)
        l = 0
        self.record_stream.flush()
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
                    l, 0, QtGui.QTableWidgetItem('%04d' % l))
                self.ui.links_table.setItem(
                    l, self.PLUG, QtGui.QTableWidgetItem(link_source))
                self.ui.links_table.setItem(
                    l, self.PROPAGATE, QtGui.QTableWidgetItem(link_dest))
                self.ui.links_table.setItem(
                    l, self.VALUE, QtGui.QTableWidgetItem(plug_value))
                links_orgs.setdefault(link_dest, []).append(l)
                if link_source in links_orgs:
                    org = links_orgs[link_source][0]
                    self.ui.links_table.setItem(
                        l, self.CAUSE,
                        QtGui.QTableWidgetItem(
                            self.ui.links_table.item(org, 2)))
                l += 1
        self.links_orgs = links_orgs
        table_header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        #table_header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        #table_header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        #table_header.setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        #table_header.setResizeMode(4, QtGui.QHeaderView.ResizeToContents)
        #table_header.setResizeMode(QtGui.QHeaderView.Interactive)
        QtGui.qApp.processEvents()
        #table_header.resizeSection(0, table_header.sectionSizeHint(0))
        #table_header.resizeSection(1, table_header.sectionSizeHint(1))
        #table_header.resizeSection(2, table_header.sectionSizeHint(2))
        #table_header.resizeSection(3, table_header.sectionSizeHint(3))
        #table_header.resizeSection(4, table_header.sectionSizeHint(4))
        table_header.setResizeMode(QtGui.QHeaderView.Interactive)

    def clear_view(self):
        self.ui.links_table.clearContents()
        self.ui.links_table.setRowCount(0)
        self.record_stream.seek(0)
        self.record_stream.truncate(0)
        self.record_stream.flush()

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
        if next_item:
            next_item.setSelected(True)
            items = self.ui.links_table.findItems(
                next_item.text(), QtCore.Qt.MatchExactly)
            for item in items:
                if item.column() == self.PLUG and item.row() >= row:
                    item.setSelected(True)

    def highlight_plug(self, row):
        self.ui.links_table.clearSelection()
        plug = self.ui.links_table.item(row, self.PLUG)
        if plug:
            plug.setSelected(True)
            items = self.ui.links_table.findItems(
                plug.text(), QtCore.Qt.MatchExactly)
            for item in items:
                if item.column() in (self.CAUSE, self.PROPAGATE):
                    item.setSelected(True)

    def highlight_value(self, row):
        self.ui.links_table.clearSelection()
        value_item = self.ui.links_table.item(row, self.VALUE)
        if value_item:
            value_item.setSelected(True)
            items = self.ui.links_table.findItems(
                value_item.text(), QtCore.Qt.MatchExactly)
            for item in items:
                if item.column() == self.VALUE:
                    item.setSelected(True)

    def go_next_line(self):
        row = self.ui.links_table.currentRow() + 1
        self.ui.links_table.setCurrentCell(row, self.PLUG)
        self.highlight_plug(row)

    def go_previous_line(self):
        row = self.ui.links_table.currentRow() - 1
        if row >= 0:
            self.ui.links_table.setCurrentCell(row, self.PLUG)
            self.highlight_plug(row)

    def go_follow_link(self):
        row = self.ui.links_table.currentRow()
        plug = self.ui.links_table.item(row, self.PROPAGATE)
        if plug:
            items = self.ui.links_table.findItems(
                plug.text(), QtCore.Qt.MatchExactly)
            for item in items:
                if item.column() == self.PLUG and item.row() > row:
                    self.ui.links_table.setCurrentCell(item.row(), self.PLUG)
                    break
        self.go_next(row)

    def help(self):
        if self.help_geom is None or self.ui.help.isVisible():
            self.help_geom = self.ui.help.geometry()
            set_geom = False
        else:
            set_geom = True
        self.ui.help.setVisible(not self.ui.help.isVisible())
        if set_geom:
            self.ui.help.setGeometry(self.help_geom)
