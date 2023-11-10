import unittest
from soma.controller import File, undefined
from capsul.api import Process
from capsul.api import Pipeline
from capsul.api import executable
import sys


class DummyProcess(Process):
    """Dummy Test Process"""

    def __init__(self, definition=None):
        super(DummyProcess, self).__init__(
            "capsul.pipeline.test.test_optional_output_switch"
        )

        # inputs
        self.add_field("input_image", File, optional=False)

        # outputs
        self.add_field("output_image", File, optional=True, write=True)

    def execute(self, context=None):
        pass


class MyPipelineWithOptOut(Pipeline):

    """Simple Pipeline to test the OptionalOutputSwitch Node"""

    def pipeline_definition(self):

        # Create processes
        self.add_process(
            "node1", "capsul.pipeline.test.test_optional_output_switch.DummyProcess"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_optional_output_switch.DummyProcess"
        )
        self.add_proxy("intermediate_out", self.nodes["node1"], "output_image")

        # Links
        self.add_link("node1.output_image->node2.input_image")

        # exports
        self.export_parameter("node1", "input_image", "input_image1")
        self.export_parameter("node2", "output_image", "output_image2")

        self.node_position = {
            "inputs": (-157.0, 67.8998),
            "intermediate_out": (265.72604, 205.80563),
            "node1": (46.40114, 102.8998),
            "node2": (298.72604, 22.0),
            "outputs": (540.34484, 109.8998),
        }


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = executable(MyPipelineWithOptOut)

    def test_way1(self):
        workflow_repr = self.pipeline.workflow_ordered_nodes()
        workflow_repr = "->".join(x.name.rsplit(".", 1)[-1] for x in workflow_repr)
        self.assertEqual(workflow_repr, "node1->node2")

    def test_way2(self):
        self.pipeline.intermediate_out = "/tmp/a_file.txt"
        self.assertEqual(self.pipeline.nodes["node1"].output_image, "/tmp/a_file.txt")
        self.assertEqual(
            self.pipeline.nodes["node1"].output_image, self.pipeline.intermediate_out
        )
        self.pipeline.intermediate_out = undefined
        self.assertEqual(
            getattr(self.pipeline.nodes["node1"], "output_image", undefined), undefined
        )


if __name__ == "__main__":
    from soma.qt_gui.qt_backend import Qt
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = Qt.QApplication.instance()
    if not app:
        app = Qt.QApplication(sys.argv)
    pipeline = executable(MyPipelineWithOptOut)
    pipeline.intermediate_out = "/tmp/a_file.txt"
    view1 = PipelineDeveloperView(
        pipeline, show_sub_pipelines=True, allow_open_controller=True
    )
    view1.show()
    app.exec_()
    del view1
