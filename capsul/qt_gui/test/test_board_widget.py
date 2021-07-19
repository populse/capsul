# -*- coding: utf-8 -*-
# System import
from __future__ import absolute_import
import unittest
import sys

# Trait import
from traits.api import File

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline

# Soma import
try:
    from soma.qt_gui.qt_backend import QtGui, QtCore
except ImportError:
    raise ImportError('Skipping tests because no Qt GUI module can be imported')

# Capsul import involving GUI    
from capsul.qt_gui.board_widget import BoardWidget

class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("output", File(optional=False, output=True))

    def _run_process(self):
        pass


class DummyViewer(Process):
    """ Dummy Test Viewer
    """
    def __init__(self):
        super(DummyViewer, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

    def _run_process(self):
        pass


class MySubPipeline(Pipeline):
    """ Simple Pipeline to test Viewer Nodes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("subprocess",
                        "capsul.qt_gui.test.test_board_widget.DummyProcess")
        self.add_process("viewer1",
                        "capsul.qt_gui.test.test_board_widget.DummyViewer")
        self.add_process("viewer2",
                        "capsul.qt_gui.test.test_board_widget.DummyViewer")

        # Links
        self.add_link("subprocess.output->viewer1.input")
        self.add_link("subprocess.output->viewer2.input")

        # Change node type
        self.nodes["viewer1"].node_type = "view_node"
        self.nodes["viewer2"].node_type = "view_node"

        # Export outputs
        self.export_parameter("subprocess", "output")


class MyPipeline(Pipeline):
    """ Simple Pipeline to test Viewer Nodes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("process",
                        "capsul.qt_gui.test.test_board_widget.MySubPipeline")
        self.add_process("viewer1",
                        "capsul.qt_gui.test.test_board_widget.DummyViewer")
        self.add_process("viewer2",
                        "capsul.qt_gui.test.test_board_widget.DummyViewer")

        # Links
        self.add_link("process.output->viewer1.input")
        self.add_link("process.output->viewer2.input")

        # Change node type
        self.nodes["viewer1"].node_type = "view_node"
        self.nodes["viewer2"].node_type = "view_node"

        # Export outputs
        self.export_parameter("process", "output")


if __name__ == "__main__":

    # Create a qt applicaction
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication(sys.argv)

    # Create the pipeline
    pipeline = MyPipeline()

    # Create to board widget
    widget = BoardWidget(pipeline, name="test")
    widget.show()

    # Start the qt loop
    app.exec_()
