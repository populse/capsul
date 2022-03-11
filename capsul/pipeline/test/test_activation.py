# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
import unittest
from soma.controller import File
from capsul.api import Process
from capsul.api import Pipeline
import sys


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__(
            'capsul.pipeline.test.test_activation.DummyProcess')

        # inputs
        self.add_field("input_image", File, optional=False)
        self.add_field("other_input", float, optional=True)

        # outputs
        self.add_field("output_image", File, optional=False, output=True)
        self.add_field("other_output", float, optional=True, output=True)

    def execute(self, context):
        pass


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("way11",
            "capsul.pipeline.test.test_activation.DummyProcess")
        self.add_process("way12",
            "capsul.pipeline.test.test_activation.DummyProcess")
        self.add_process("way21",
            "capsul.pipeline.test.test_activation.DummyProcess")
        self.add_process("way22",
            "capsul.pipeline.test.test_activation.DummyProcess",
            do_not_export=['output_image' ],
            make_optional=['output_image'])

        # Inputs
        self.export_parameter("way11", "input_image")

        # Links
        self.add_link("input_image->way21.input_image")
        self.add_link("way11.output_image->way12.input_image")
        self.add_link("way21.output_image->way22.input_image")

        # Outputs
        self.export_parameter("way12", "output_image", is_optional=True)
        self.export_parameter("way22", "other_output")


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = MyPipeline()

    @unittest.skip('reimplementation expected for capsul v3')
    def test_partial_desactivation(self):
        self.pipeline.nodes_activation.way11 = False
        self.run_unactivation_tests_1()
        self.pipeline.nodes_activation.way11 = True

        self.pipeline.nodes_activation.way12 = False
        self.run_unactivation_tests_1()
        self.pipeline.nodes_activation.way12 = True

        self.pipeline.nodes_activation.way21 = False
        self.run_unactivation_tests_2()
        self.pipeline.nodes_activation.way21 = True

        self.pipeline.nodes_activation.way22 = False
        self.run_unactivation_tests_2()
        self.pipeline.nodes_activation.way22 = True

    @unittest.skip('reimplementation expected for capsul v3')
    def test_full_desactivation(self):
        self.pipeline.nodes_activation.way11 = False
        self.pipeline.nodes_activation.way21 = False

        self.assertFalse(self.pipeline.nodes["way11"].enabled)
        self.assertFalse(self.pipeline.nodes["way21"].enabled)
        self.assertFalse(self.pipeline.nodes["way11"].activated)
        self.assertFalse(self.pipeline.nodes["way12"].activated)
        self.assertFalse(self.pipeline.nodes["way21"].activated)
        self.assertFalse(self.pipeline.nodes["way22"].activated)
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "")

    @unittest.skip('reimplementation expected for capsul v3')
    def run_unactivation_tests_1(self):
        self.assertFalse(self.pipeline.nodes["way11"].activated)
        self.assertFalse(self.pipeline.nodes["way12"].activated)
        self.assertTrue(self.pipeline.nodes["way21"].activated)
        self.assertTrue(self.pipeline.nodes["way22"].activated)
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "way21->way22")

    @unittest.skip('reimplementation expected for capsul v3')
    def run_unactivation_tests_2(self):
        self.assertTrue(self.pipeline.nodes["way11"].activated)
        self.assertTrue(self.pipeline.nodes["way12"].activated)
        self.assertFalse(self.pipeline.nodes["way21"].activated)
        self.assertFalse(self.pipeline.nodes["way22"].activated)
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "way11->way12")


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:]:
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        setattr(pipeline.nodes_activation, "way11", False)
        view1 = PipelineDeveloperView(pipeline)
        view1.show()
        app.exec_()
        del view1
