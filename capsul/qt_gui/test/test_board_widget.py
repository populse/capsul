##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import sys

# Trait import
from traits.api import File

# Capsul import
from capsul.process import Process
from capsul.pipeline import Pipeline
from capsul.qt_gui.board_widget import BoardWidget

# Soma import
from soma.qt_gui.qt_backend import QtGui, QtCore


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



