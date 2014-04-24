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

        # outputs
        self.add_trait("output_image", Str(optional=False, output=True))
        self.add_trait("other_output", Float(optional=False, output=True))

    def _run_process(self):
        self.output_image = self.input_image


class SwitchPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("way1",
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess")
        self.add_process("way2",
            "capsul.pipeline.test.test_switch_subpipeline.DummyProcess")

        # Create Switch
        self.add_switch("switch", ["one", "two"],
                        ["switch_image", ])

        # Link input
        self.export_parameter("way1", "input_image")

        # Links
        self.add_link("way1.output_image->switch.one_switch_switch_image")

        self.add_link("input_image->way2.input_image")

        self.add_link("way2.output_image->switch.two_switch_switch_image")

        # Outputs
        self.export_parameter("way1", "other_output",
                              pipeline_parameter="weak_output_1",
                              weak_link=True)
        self.export_parameter("way2", "other_output",
                              pipeline_parameter="weak_output_2",
                              weak_link=True)
        self.export_parameter("switch", "switch_image",
                              pipeline_parameter="result_image")


class Pipeline2(Pipeline):
    """
    """
    def pipeline_definition(self):
        self.add_process("sub_pipeline", "capsul.pipeline.test.test_switch_subpipeline.SwitchPipeline")

        self.export_parameter("sub_pipeline", "switch")
        self.export_parameter("sub_pipeline", "input_image")
        self.export_parameter("sub_pipeline", "weak_output_1")
        self.export_parameter("sub_pipeline", "weak_output_2")


class TestSwitchSubPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = Pipeline2()

    def test_weak_plug_1_activated(self):
        # node way1 is active, its "other_output" should be active and
        # linked to the pipeline weak_output_1
        self.assertTrue(
            self.pipeline.nodes['sub_pipeline'].process.nodes['way1'] \
                .plugs['other_output'].activated)

    def test_weak_1_on(self):
        # node way1 is active:
        # assignation of weak_output_1 should be propagated to node way1
        self.pipeline.weak_output_1 = 12.
        self.assertTrue(
            self.pipeline.nodes['sub_pipeline'].process.nodes['way1'] \
                .process.other_output == self.pipeline.weak_output_1)

    def test_weak_2_on(self):
        # here we are more or less in the same case as in test_weak_1_on for
        # node way2: way2 is activated (via the switch), so its outputs should
        # be linked to the main pipeline outputs
        self.pipeline.switch = "two"
        self.pipeline.weak_output_2 = 12.
        self.assertTrue(
            self.pipeline.nodes['sub_pipeline'].process.nodes['way2'] \
                .process.other_output == self.pipeline.weak_output_2)

    def test_weak_2bis_on(self):
        # node way2 is inactive: should assignation of weak_output_2 be
        # propagated to way2.other_output ? This is questionable, but when
        # reactivating the node (via the switch), then the value should
        # ideally be propagated - but in which direction ?
        self.pipeline.weak_output_2 = 12.
        self.pipeline.switch = "two"
        self.assertTrue(
            self.pipeline.nodes['sub_pipeline'].process.nodes['way2'] \
                .process.other_output == self.pipeline.weak_output_2)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSwitchSubPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print "RETURNCODE: ", test()

    import sys
    from PySide import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView

    app = QtGui.QApplication(sys.argv)
    pipeline = Pipeline2()
    pipeline.switch = "one"
    view1 = PipelineDevelopperView(pipeline, force_plot=True)
    view1.show()
    app.exec_()
    del view1

