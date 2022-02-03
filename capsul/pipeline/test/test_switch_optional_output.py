# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
from traits.api import File, Float
from capsul.api import Process
from capsul.api import Pipeline


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input_image", File(optional=False))

        # outputs
        self.add_trait("output_image", File(optional=True, output=True))

    def __call__(self):
        pass


class MyPipeline(Pipeline):
    """ Simple Pipeline to test the Switch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node1",
            "capsul.pipeline.test.test_switch_optional_output.DummyProcess")
        self.add_process("node2",
            "capsul.pipeline.test.test_switch_optional_output.DummyProcess")
        self.add_process("node3",
            "capsul.pipeline.test.test_switch_optional_output.DummyProcess")
        self.add_switch("switch1", ["one", "two"], ["out"])

        # Links
        self.add_link("node2.output_image->node3.input_image")
        self.add_link("node1.output_image->switch1.one_switch_out")
        self.add_link("node3.output_image->switch1.two_switch_out")

        # exports
        self.export_parameter("node1", "input_image", "input_image1")
        self.export_parameter("node2", "input_image", "input_image2")

        self.node_position = {
            'inputs': (-206.0, 242.0),
            'node1': (89.0, 114.0),
            'node2': (-25.0, 365.0),
            'node3': (166.0, 375.0),
            'outputs': (481.0, 335.0),
            'switch1': (340.0, 234.0)}


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = MyPipeline()

    def test_way1(self):
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "node1")

    def test_way2(self):
        self.pipeline.switch1 = 'two'
        self.pipeline.workflow_ordered_nodes()
        self.assertEqual(self.pipeline.workflow_repr, "node2->node3")


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    if 0:
        import sys
        from PyQt4 import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = MyPipeline()
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1
