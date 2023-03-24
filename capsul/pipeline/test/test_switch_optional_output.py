# -*- coding: utf-8 -*-
import unittest
from soma.controller import File
from capsul.api import Capsul, Process, Pipeline, CapsulWorkflow


class DummyProcess(Process):
    """Dummy Test Process"""

    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input_image", File)

        # outputs
        self.add_field("output_image", File, optional=True, output=True)


class MyPipeline(Pipeline):
    """Simple Pipeline to test the Switch Node"""

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1", "capsul.pipeline.test.test_switch_optional_output.DummyProcess"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_switch_optional_output.DummyProcess"
        )
        self.add_process(
            "node3", "capsul.pipeline.test.test_switch_optional_output.DummyProcess"
        )
        self.add_switch("switch1", ["one", "two"], ["out"])

        # Links
        self.add_link("node2.output_image->node3.input_image")
        self.add_link("node1.output_image->switch1.one_switch_out")
        self.add_link("node3.output_image->switch1.two_switch_out")

        # exports
        self.export_parameter("node1", "input_image", "input_image1")
        self.export_parameter("node2", "input_image", "input_image2")

        self.node_position = {
            "inputs": (-206.0, 242.0),
            "node1": (89.0, 114.0),
            "node2": (-25.0, 365.0),
            "node3": (166.0, 375.0),
            "outputs": (481.0, 335.0),
            "switch1": (340.0, 234.0),
        }


class TestPipeline(unittest.TestCase):
    def test_switch_optional_output_way1(self):
        pipeline = Capsul.executable(MyPipeline)
        workflow = CapsulWorkflow(pipeline)
        self.assertEqual(len(workflow.jobs), 1)

    def test_switch_optional_output_way2(self):
        pipeline = Capsul.executable(MyPipeline)
        pipeline.switch1 = "two"
        workflow = CapsulWorkflow(pipeline)
        self.assertEqual(len(workflow.jobs), 2)


if __name__ == "__main__":
    if 0:
        import sys
        from PyQt4 import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        view1 = PipelineDeveloperView(
            pipeline, show_sub_pipelines=True, allow_open_controller=True
        )
        view1.show()
        app.exec_()
        del view1
