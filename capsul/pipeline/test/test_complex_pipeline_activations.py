import os
import shutil
import sys
import tempfile
import unittest

from soma.controller import File, field

from capsul.api import Pipeline, Process, executable


class Identity(Process):
    input_image: File = field(optional=False, output=False)
    output_image: File = field(optional=False, output=True)


class ComplexPipeline(Pipeline):
    """Pipeline to test complex constructions behaviours"""

    def pipeline_definition(self):
        # Create processes
        self.add_process("first_pipeline", "capsul.process.test.test_pipeline")
        self.add_process(
            "pipeline_1",
            "capsul.process.test.test_pipeline",
            make_optional=["output_1", "output_10", "output_100"],
        )

        # self.export_parameter('pipeline_1', 'output_1')

        self.add_process(
            "pipeline_10",
            "capsul.process.test.test_pipeline",
            make_optional=["output_1", "output_10", "output_100"],
        )
        self.add_process(
            "pipeline_100",
            "capsul.process.test.test_pipeline",
            make_optional=["output_1", "output_10", "output_100"],
        )
        self.create_switch(
            "select_threshold",
            {
                "threshold_1": {
                    "output_a": "pipeline_1.output_1",
                    "output_b": "pipeline_10.output_1",
                    "output_c": "pipeline_100.output_1",
                },
                "threshold_10": {
                    "output_a": "pipeline_1.output_10",
                    "output_b": "pipeline_10.output_10",
                    "output_c": "pipeline_100.output_10",
                },
                "threshold_100": {
                    "output_a": "pipeline_1.output_100",
                    "output_b": "pipeline_10.output_100",
                    "output_c": "pipeline_100.output_100",
                },
            },
        )
        self.add_process(
            "identity_a",
            "capsul.pipeline.test.test_complex_pipeline_activations.Identity",
        )
        self.add_process(
            "identity_b",
            "capsul.pipeline.test.test_complex_pipeline_activations.Identity",
        )
        self.add_process(
            "identity_c",
            "capsul.pipeline.test.test_complex_pipeline_activations.Identity",
        )

        self.export_parameter("first_pipeline", "select_method")
        self.add_link("select_method->pipeline_1.select_method")
        self.add_link("select_method->pipeline_10.select_method")
        self.add_link("select_method->pipeline_100.select_method")

        self.add_link("first_pipeline.output_1->pipeline_1.input_image")
        self.add_link("first_pipeline.output_10->pipeline_10.input_image")
        self.add_link("first_pipeline.output_100->pipeline_100.input_image")

        self.add_link("select_threshold.output_a->identity_a.input_image")
        self.add_link("select_threshold.output_b->identity_b.input_image")
        self.add_link("select_threshold.output_c->identity_c.input_image")

        self.export_parameter("identity_a", "output_image", "output_a")
        self.export_parameter("identity_b", "output_image", "output_b")
        self.export_parameter("identity_c", "output_image", "output_c")
        self.node_position = {
            "first_pipeline": (118.0, 486.0),
            "identity_a": (870.0, 644.0),
            "identity_b": (867.0, 742.0),
            "identity_c": (866.0, 846.0),
            "inputs": (-107.0, 491.0),
            "outputs": (1111.0, 723.0),
            "pipeline_1": (329.0, 334.0),
            "pipeline_10": (331.0, 533.0),
            "pipeline_100": (334.0, 738.0),
            "select_threshold": (559.0, 453.0),
        }


class TestComplexPipeline(unittest.TestCase):
    expected_status = [
        (
            {},
            {
                "": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "select_threshold": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_a": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_b": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_c": {
                    "_activated": True,
                    "_enabled": True,
                },
            },
        ),
        (
            {"select_method": "lower than"},
            {
                "": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.mask_10": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "select_threshold": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_a": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_b": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_c": {
                    "_activated": True,
                    "_enabled": True,
                },
            },
        ),
        (
            {"select_threshold": "threshold_10"},
            {
                "": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_lt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "select_threshold": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_a": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_b": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_c": {
                    "_activated": True,
                    "_enabled": True,
                },
            },
        ),
        (
            {"select_threshold": "threshold_10", "select_method": "lower than"},
            {
                "": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_lt_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "first_pipeline.mask_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "first_pipeline.mask_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_1.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_1.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_1.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_10.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_10.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_10.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.threshold_lt_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.threshold_gt_1": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_gt_10": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.threshold_gt_100": {
                    "_activated": False,
                    "_enabled": False,
                },
                "pipeline_100.mask_1": {
                    "_activated": False,
                    "_enabled": True,
                },
                "pipeline_100.mask_10": {
                    "_activated": True,
                    "_enabled": True,
                },
                "pipeline_100.mask_100": {
                    "_activated": False,
                    "_enabled": True,
                },
                "select_threshold": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_a": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_b": {
                    "_activated": True,
                    "_enabled": True,
                },
                "identity_c": {
                    "_activated": True,
                    "_enabled": True,
                },
            },
        ),
    ]

    def test_complex_activations(self):
        for kwargs, activations_to_check in self.expected_status:
            pipeline = executable(ComplexPipeline, **kwargs)

        for full_node_name, node_activations in activations_to_check.items():
            split = full_node_name.split(".")
            node_pipeline = pipeline
            for i in split[:-1]:
                node_pipeline = node_pipeline.nodes[i]
            node_name = split[-1]
            try:
                node = node_pipeline.nodes[node_name]
            except KeyError as e:
                raise KeyError(
                    f"Pipeline {node_pipeline.pipeline} has no node named {node_name}"
                ) from e
            try:
                what = "activation of node {}".format(
                    full_node_name or "main pipeline node"
                )
                expected = node_activations.get("_activated")
                if expected is not None:
                    got = node.activated
                    self.assertEqual(expected, got)
                what = "enabled for node {}".format(
                    full_node_name or "main pipeline node"
                )
                expected = node_activations.get("_enabled")
                if expected is not None:
                    got = node.enabled
                    self.assertEqual(expected, got)
            except AssertionError as e:
                raise AssertionError(
                    f"Wrong activation within ComplexPipeline with parameters {kwargs}: {what} is supposed to be {expected} but is {got}"
                ) from e


if __name__ == "__main__":
    if "-v" in sys.argv[1:]:
        from pprint import pprint

        pipeline = executable(ComplexPipeline)

        from soma.qt_gui.qt_backend import Qt

        from capsul.qt_gui.widgets import PipelineDeveloperView
        from capsul.qt_gui.widgets.activation_inspector import ActivationInspectorApp

        app = Qt.QApplication(sys.argv)

        sys.argv = [sys.argv[0]]
        aapp = ActivationInspectorApp(ComplexPipeline)

        view = PipelineDeveloperView(
            pipeline, allow_open_controller=True, show_sub_pipelines=True
        )
        view.show()

        app.exec_()
        del view
