#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import unittest
import os
from traits.api import Str, Float
from capsul.process import Process
from capsul.pipeline import Pipeline, PipelineNode


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input_image", Str(optional=False))
        self.add_trait("other_input", Float(optional=True))

        # outputs
        self.add_trait("output_image", Str(optional=False, output=True))
        self.add_trait("other_output", Float(optional=False, output=True))

    def _run_process(self):
        self.output_image = self.input_image
        self.other_output = self.other_input


class SwitchPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node",
            "capsul.pipeline.test.test_switch_pipeline.DummyProcess")
        self.add_process("way1",
            "capsul.pipeline.test.test_switch_pipeline.DummyProcess")
        self.add_process("way21",
            "capsul.pipeline.test.test_switch_pipeline.DummyProcess")
        self.add_process("way22",
             "capsul.pipeline.test.test_switch_pipeline.DummyProcess")

        # Create Switch
        self.add_switch("switch", ["one", "two", "none"],
                        ["switch_image", "switch_output", ])

        # Link input
        self.export_parameter("node", "input_image")
        self.export_parameter("node", "other_input")

        # Links
        self.add_link("node.output_image->switch.none_switch_switch_image")
        self.add_link("node.other_output->switch.none_switch_switch_output")
        self.add_link("node.output_image->way1.input_image")
        self.add_link("node.other_output->way1.other_input")
        self.add_link("node.output_image->way21.input_image")
        self.add_link("node.other_output->way21.other_input")

        self.add_link("way21.output_image->way22.input_image")
        self.add_link("way21.other_output->way22.other_input")

        self.add_link("way1.output_image->switch.one_switch_switch_image")
        self.add_link("way1.other_output->switch.one_switch_switch_output")

        self.add_link("way22.output_image->switch.two_switch_switch_image")
        self.add_link("way22.other_output->switch.two_switch_switch_output")

        # Outputs
        self.export_parameter("node", "other_output",
                              pipeline_parameter="hard_output",
                              is_optional=True)
        self.export_parameter("way21", "other_output",
                              pipeline_parameter="weak_output_1",
                              weak_link=True,
                              is_optional=True)
        self.export_parameter("way22", "other_output",
                              pipeline_parameter="weak_output_2",
                              weak_link=True,
                              is_optional=True)
        self.export_parameter("switch", "switch_image",
                              pipeline_parameter="result_image")
        self.export_parameter("switch", "switch_output",
                              pipeline_parameter="result_output")


class TestSwitchPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = SwitchPipeline()

    def test_way1(self):
        self.pipeline.switch = "one"
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "node->way1")

    def test_way2(self):
        self.pipeline.switch = "two"
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "node->way21->way22")

    def test_way3(self):
        self.pipeline.switch = "none"
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "node")

    def test_weak_on(self):
        self.pipeline.switch = "two"

        def is_valid():
            self.assertTrue(src_weak_plug.activated)
            self.assertTrue(dest_weak_plug.activated)
            is_weak = False
            for nn, pn, n, p, wl in src_weak_plug.links_to:
                if isinstance(n, PipelineNode):
                    is_weak = is_weak or wl
            self.assertTrue(is_weak)

        src_node = self.pipeline.nodes["way21"]
        src_weak_plug = src_node.plugs["other_output"]
        dest_node = self.pipeline.nodes[""]
        dest_weak_plug = dest_node.plugs["weak_output_1"]
        is_valid()

        src_node = self.pipeline.nodes["way22"]
        src_weak_plug = src_node.plugs["other_output"]
        dest_node = self.pipeline.nodes[""]
        dest_weak_plug = dest_node.plugs["weak_output_2"]
        is_valid()

    def test_weak_off(self):
        self.pipeline.switch = "one"

        def is_valid():
            self.assertFalse(src_weak_plug.activated)
            self.assertFalse(dest_weak_plug.activated)
            is_weak = False
            for nn, pn, n, p, wl in src_weak_plug.links_to:
                if isinstance(n, PipelineNode):
                    is_weak = is_weak or wl
            self.assertTrue(is_weak)

        src_node = self.pipeline.nodes["way21"]
        src_weak_plug = src_node.plugs["other_output"]
        dest_node = self.pipeline.nodes[""]
        dest_weak_plug = dest_node.plugs["weak_output_1"]
        is_valid()

        src_node = self.pipeline.nodes["way22"]
        src_weak_plug = src_node.plugs["other_output"]
        dest_node = self.pipeline.nodes[""]
        dest_weak_plug = dest_node.plugs["weak_output_2"]
        is_valid()

    def test_hard(self):
        self.pipeline.switch = "one"
        src_node = self.pipeline.nodes["node"]
        src_weak_plug = src_node.plugs["other_output"]
        self.assertTrue(src_weak_plug.activated)
        dest_node = self.pipeline.nodes[""]
        dest_weak_plug = dest_node.plugs["hard_output"]
        self.assertTrue(dest_weak_plug.activated)
        is_weak = False
        for nn, pn, n, p, wl in src_weak_plug.links_to:
            if isinstance(n, PipelineNode):
                is_weak = is_weak or wl
        self.assertFalse(is_weak)

    def test_parameter_propagation(self):
        self.pipeline.switch = "one"
        key = "test"
        self.pipeline.input_image = key
        # Test first level
        self.assertEqual(self.pipeline.nodes["node"].process.input_image,
                         key)
        # Test second level
        self.pipeline.nodes["node"].process()
        self.assertEqual(self.pipeline.nodes["way1"].process.input_image,
                         key)
        self.pipeline.switch = "two"
        self.assertEqual(self.pipeline.nodes["way21"].process.input_image,
                         key)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSwitchPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print "RETURNCODE: ", test()

    import sys
    from PySide import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)
    pipeline = SwitchPipeline()
    pipeline.switch = "one"
    view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True,
                                   allow_open_controller=True)
    view1.show()
    app.exec_()
    del view1

