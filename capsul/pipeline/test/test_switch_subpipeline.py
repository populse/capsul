# -*- coding: utf-8 -*-
import unittest
import os
import json
from capsul.api import Process, executable
from capsul.api import Pipeline
import sys


class DummyProcess(Process):
    """Dummy Test Process"""

    def __init__(self, definition=None):
        super(DummyProcess, self).__init__(
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess"
        )

        # inputs
        self.add_field("input_image", str, optional=False)
        self.add_field("other_input", str, optional=True)

        # outputs
        self.add_field("output_image", str, optional=False, output=True)
        self.add_field("other_output", str, optional=False, output=True)

    def execute(self):
        self.output_image = self.input_image
        self.other_output = self.other_input


class DummyProcess1_1(Process):
    """Dummy Test Process with 1 input and one output"""

    def __init__(self, definition=None):
        super(DummyProcess1_1, self).__init__(
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )

        # inputs
        self.add_field("input", str, optional=False)

        # outputs
        self.add_field("output", str, optional=False, output=True)

    def execute(self):
        self.output = self.input


class DummyProcess2_1(Process):
    """Dummy Test Process with 2 inputs and one output"""

    def __init__(self, definition=None):
        super(DummyProcess2_1, self).__init__(
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess2_1"
        )

        # inputs
        self.add_field("input1", str, optional=False)
        self.add_field("input2", str, optional=False)

        # outputs
        self.add_field("output", str, optional=False, output=True)

    def execute(self):
        self.output = "_".join((self.input1, self.input2))


class DummyProcess4_1(Process):
    """Dummy Test Process with 4 inputs and one output"""

    def __init__(self, definition=None):
        super(DummyProcess4_1, self).__init__(
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess4_1"
        )

        # inputs
        self.add_field("input1", str, optional=False)
        self.add_field("input2", str, optional=False)
        self.add_field("input3", str, optional=False)
        self.add_field("input4", str, optional=False)

        # outputs
        self.add_field("output", str, optional=False, output=True)

    def execute(self):
        self.output = "_".join((self.input1, self.input2, self.input3, self.input4))


class SwitchPipeline(Pipeline):
    """Simple Pipeline to test the Switch Node"""

    def pipeline_definition(self):

        # Create processes
        self.add_process(
            "way1", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess"
        )
        self.add_process(
            "way2", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess"
        )

        # Create Switch
        self.create_switch(
            "switch",
            {
                "one": {"switch_image": "way1.output_image"},
                "two": {"switch_image": "way2.output_image"},
            },
        )

        # Link input
        self.export_parameter("way1", "input_image")
        self.export_parameter("way1", "other_input")

        self.add_link("input_image->way2.input_image")
        self.add_link("other_input->way2.other_input")

        # Outputs
        self.export_parameter(
            "way1",
            "other_output",
            pipeline_parameter="weak_output_1",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "way2",
            "other_output",
            pipeline_parameter="weak_output_2",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "switch", "switch_image", pipeline_parameter="result_image"
        )

        self.node_position = {
            "inputs": (40.0, 240.0),
            "outputs": (605.0, 289.0),
            "switch": (381.0, 255.0),
            "way1": (211.0, 179.0),
            "way2": (208.0, 338.0),
        }


class MultipleConnectionsPipeline(Pipeline):
    """Simple Pipeline to test one input connected to several processes"""

    def pipeline_definition(self):

        # Create processes
        self.add_process(
            "process1", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )
        self.export_parameter("process1", "input", "input1")
        self.add_process(
            "process2", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )
        self.add_link("input1->process2.input")
        self.add_process(
            "process3", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )
        self.add_link("input1->process3.input")
        self.add_process(
            "process4", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess4_1"
        )
        self.add_link("process1.output->process4.input1")
        self.add_link("process2.output->process4.input2")
        self.add_link("process3.output->process4.input3")
        self.export_parameter("process4", "input4", "input2")

        self.node_position = {
            "inputs": (28.9, 340.8),
            "outputs": (574.4, 236.0),
            "process1": (229.2, 82.8),
            "process2": (236.6, 206.7),
            "process3": (214.2, 327.6),
            "process4": (397.8, 314.2),
        }


class MainTestPipeline(Pipeline):
    def pipeline_definition(self):
        self.add_process(
            "switch_pipeline",
            "capsul.pipeline.test.test_switch_subpipeline.SwitchPipeline",
        )
        # Export may be omitted here but it is necessary to force parameters
        # order.
        self.export_parameter("switch_pipeline", "input_image")
        self.export_parameter("switch_pipeline", "switch", "which_way")
        self.add_process(
            "way1_1",
            "capsul.pipeline.test.test_switch_subpipeline.MultipleConnectionsPipeline",
        )
        self.add_process(
            "way1_2", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )
        self.add_process(
            "way2_1",
            "capsul.pipeline.test.test_switch_subpipeline.MultipleConnectionsPipeline",
        )
        self.add_process(
            "way2_2", "capsul.pipeline.test.test_switch_subpipeline.DummyProcess1_1"
        )
        self.add_link("switch_pipeline.weak_output_1->way1_1.input1")
        self.add_link("switch_pipeline.result_image->way1_1.input2")
        self.add_link("way1_1.output->way1_2.input")
        self.export_parameter("way1_2", "output")
        self.add_link("switch_pipeline.weak_output_2->way2_1.input1")
        self.add_link("switch_pipeline.result_image->way2_1.input2")
        self.add_link("way2_1.output->way2_2.input")
        self.add_link("way2_2.output->output")

        # self.node_position = {'inputs': (-33.8, 278.1),
        #'outputs': (661.0, 239.0),
        #'switch_pipeline': (173.0, 112.0),
        #'way1_1': (377.0, 113.0),
        #'way1_2': (510.0, 163.0),
        #'way2_1': (376.0, 246.0),
        #'way2_2': (507.0, 296.0)}
        self.node_position = {
            "inputs": (-605.0, -77.0),
            "outputs": (1022.0, 56.0),
            "switch_pipeline": (-439.0, 51.0),
            "way1_1": (335.0, -207.0),
            "way1_2": (851.0, -66.0),
            "way2_1": (381.0, 116.0),
            "way2_2": (852.0, 170.0),
        }


class TestSwitchPipeline(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.pipeline = executable(MainTestPipeline)
        # self.pipeline.name = ''  # saved state has an empty main node name

    def load_state(self, file_name):
        file_name = os.path.join(os.path.dirname(__file__), file_name + ".json")
        with open(file_name) as f:
            return json.load(f)

    def test_self_state(self):
        # verify that the state of a pipeline does not generate differences
        # when compared to itself
        state = self.pipeline.pipeline_state()
        self.assertEqual(self.pipeline.compare_to_state(state), [])

    def test_switch_value(self):
        state_one = self.load_state("test_switch_subpipeline_one")
        state_two = self.load_state("test_switch_subpipeline_two")
        self.pipeline.which_way = "two"
        self.assertEqual(self.pipeline.compare_to_state(state_two), [])
        self.pipeline.which_way = "one"
        self.assertEqual(self.pipeline.compare_to_state(state_one), [])


if __name__ == "__main__":
    if "-v" in sys.argv[1:]:

        def write_state():
            state_file_name = "/tmp/state.json"
            with open(state_file_name, "w") as f:
                json.dump(pipeline.pipeline_state(), f)
            print("Wrote", state_file_name)

        import sys
        from soma.qt_gui import qt_backend

        qt_backend.set_qt_backend(compatible_qt5=True)
        from soma.qt_gui.qt_backend import Qt
        from capsul.qt_gui.widgets import PipelineDeveloperView

        # from capsul.qt_gui.widgets import PipelineUserView

        app = Qt.QApplication(sys.argv)
        # pipeline = capsul.executable(MainTestPipeline)
        pipeline = executable(MainTestPipeline)
        pipeline.selection_changed.add(write_state)
        view1 = PipelineDeveloperView(
            pipeline, show_sub_pipelines=True, allow_open_controller=True
        )
        view1.add_embedded_subpipeline("switch_pipeline", scale=0.7)
        view1.add_embedded_subpipeline("way1_1", scale=0.4)
        view1.add_embedded_subpipeline("way2_1", scale=0.4)
        view1.show()
        # pipeline._debug_activations = '/tmp/activations.log'
        # view2 = PipelineUserView(pipeline)
        # view2.show()
        app.exec_()
        del view1
        # del view2
