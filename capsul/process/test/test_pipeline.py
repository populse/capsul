from collections import OrderedDict

from capsul.api import Pipeline


class test_pipeline(Pipeline):
    def pipeline_definition(self):
        # nodes
        self.add_process(
            "threshold_gt_1",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_gt_1"].threshold = 1.0
        self.add_process(
            "threshold_gt_10",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_gt_10"].threshold = 10.0
        self.add_process(
            "threshold_gt_100",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_gt_100"].threshold = 100.0
        self.add_process(
            "threshold_lt_1",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_lt_1"].method = "lt"
        self.nodes["threshold_lt_1"].threshold = 1.0
        self.add_process(
            "threshold_lt_10",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_lt_10"].method = "lt"
        self.nodes["threshold_lt_10"].threshold = 10.0
        self.add_process(
            "threshold_lt_100",
            "capsul.process.test.test_load_from_description.threshold",
            make_optional=["method", "threshold"],
        )
        self.nodes["threshold_lt_100"].method = "lt"
        self.nodes["threshold_lt_100"].threshold = 100.0
        self.add_process(
            "mask_1", "capsul.process.test.test_load_from_description.mask"
        )
        self.add_process(
            "mask_10", "capsul.process.test.test_load_from_description.mask"
        )
        self.add_process(
            "mask_100", "capsul.process.test.test_load_from_description.mask"
        )

        # links
        self.export_parameter("threshold_lt_1", "input_image")
        self.add_link("input_image->threshold_gt_10.input_image")
        self.add_link("input_image->mask_10.input_image")
        self.add_link("input_image->threshold_gt_1.input_image")
        self.add_link("input_image->threshold_lt_100.input_image")
        self.add_link("input_image->threshold_lt_10.input_image")
        self.add_link("input_image->mask_1.input_image")
        self.add_link("input_image->threshold_gt_100.input_image")
        self.add_link("input_image->mask_100.input_image")
        self.add_link("threshold_gt_1.output_image->mask_1.mask")
        self.add_link("threshold_gt_10.output_image->mask_10.mask")
        self.add_link("threshold_gt_100.output_image->mask_100.mask")
        self.add_link("threshold_lt_1.output_image->mask_1.mask")
        self.add_link("threshold_lt_10.output_image->mask_10.mask")
        self.add_link("threshold_lt_100.output_image->mask_100.mask")
        self.export_parameter("mask_1", "output_image", "output_1")
        self.export_parameter("mask_10", "output_image", "output_10")
        self.export_parameter("mask_100", "output_image", "output_100")

        # processes selection
        self.add_processes_selection(
            "select_method",
            OrderedDict(
                [
                    (
                        "greater than",
                        ["threshold_gt_1", "threshold_gt_10", "threshold_gt_100"],
                    ),
                    (
                        "lower than",
                        ["threshold_lt_1", "threshold_lt_10", "threshold_lt_100"],
                    ),
                ]
            ),
        )

        # nodes positions
        self.node_position = {
            "threshold_gt_100": (386.0, 403.0),
            "inputs": (50.0, 50.0),
            "mask_1": (815.0, 153.0),
            "threshold_gt_10": (374.0, 242.0),
            "threshold_lt_100": (556.0, 314.0),
            "threshold_gt_1": (371.0, 88.0),
            "mask_10": (820.0, 293.0),
            "mask_100": (826.0, 451.0),
            "threshold_lt_1": (570.0, 6.0),
            "threshold_lt_10": (568.0, 145.0),
            "outputs": (1000.0, 100.0),
        }

        self.do_autoexport_nodes_parameters = False
