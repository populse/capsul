import unittest
from capsul.api import Process, executable
from capsul.api import Pipeline


class DummyProcess(Process):
    """Dummy Test Process"""

    def __init__(self, definition=None):
        super(DummyProcess, self).__init__(
            "capsul.pipeline.test.test_double_switch.DummyProcess"
        )

        # inputs
        self.add_field("input_image", str, optional=False)

        # outputs
        self.add_field("output_image", str, optional=False, output=True)

    def execute(self, context=None):
        self.output_image = self.input_image


class DoubleSwitchPipeline1(Pipeline):
    """Simple Pipeline to test the Switch-Switch connection"""

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1", "capsul.pipeline.test.test_double_switch.DummyProcess"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_double_switch.DummyProcess"
        )
        self.add_process(
            "node3", "capsul.pipeline.test.test_double_switch.DummyProcess"
        )
        self.add_process(
            "node4", "capsul.pipeline.test.test_double_switch.DummyProcess"
        )

        self.create_switch(
            "switch1",
            options={
                "one": {
                    "switch_image1": "node1.output_image",
                    "switch_image2": "node3.output_image",
                },
                "two": {
                    "switch_image1": "node2.output_image",
                    "switch_image2": "node4.output_image",
                },
            },
            make_optional=("switch_image1",),
        )

        self.create_switch(
            "switch2",
            options={
                "one": {"switch_image": "node1.output_image"},
                "two": {"switch_image": "switch1.switch_image1"},
            },
        )

        # Link input
        self.export_parameter("node1", "input_image", "input_image1")
        self.export_parameter("node2", "input_image", "input_image2")
        self.export_parameter("node3", "input_image", "input_image3")
        self.export_parameter("node4", "input_image", "input_image4")

        # Outputs
        self.export_parameter(
            "switch1", "switch_image2", pipeline_parameter="temp_image"
        )
        self.export_parameter(
            "switch2", "switch_image", pipeline_parameter="result_image"
        )

        self.node_position = {
            "inputs": (-240.0, 144.0),
            "node1": (7.0, 128.0),
            "node2": (-6.0, 337.0),
            "node3": (3.0, 214.0),
            "node4": (-13.0, 433.0),
            "outputs": (598.0, 350.0),
            "switch1": (213.0, 227.0),
            "switch2": (478.0, 166.0),
        }


class TestDoubleSwitchPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = executable(DoubleSwitchPipeline1)

    def test_double_switch_way2(self):
        self.pipeline.switch1 = "one"
        self.pipeline.switch2 = "two"
        self.assertEqual(self.pipeline.nodes["switch1"].activated, True)

    def test_double_switch_way1(self):
        self.pipeline.switch1 = "one"
        self.pipeline.switch2 = "one"
        self.assertEqual(self.pipeline.nodes["switch1"].activated, True)


if __name__ == "__main__":
    import sys
    from soma.qt_gui import qt_backend

    qt_backend.set_qt_backend(compatible_qt5=True)
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = executable(DoubleSwitchPipeline1)
    pipeline.switch1 = "one"
    pipeline.switch2 = "one"
    view1 = PipelineDeveloperView(
        pipeline, show_sub_pipelines=True, allow_open_controller=True
    )
    view1.show()

    app.exec_()
    del view1
