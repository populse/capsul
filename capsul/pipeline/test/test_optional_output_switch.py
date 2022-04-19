# -*- coding: utf-8 -*-

import unittest
from soma.controller import File, undefined
from capsul.api import Process
from capsul.api import Pipeline
from capsul.api import executable
from capsul.pipeline.pipeline_nodes import OptionalOutputSwitch
import tempfile
import os


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self, definition=None):
        super(DummyProcess, self).__init__(
            'capsul.pipeline.test.test_optional_output_switch')

        # inputs
        self.add_field("input_image", File, optional=False)

        # outputs
        self.add_field("output_image", File, optional=True, write=True)

    def execute(self, context=None):
        pass


class MyPipelineWithOptOut(Pipeline):

    """ Simple Pipeline to test the OptionalOutputSwitch Node
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node1",
            "capsul.pipeline.test.test_optional_output_switch.DummyProcess")
        self.add_process("node2",
            "capsul.pipeline.test.test_optional_output_switch.DummyProcess")
        self.add_optional_output_switch("intermediate_out", "one")

        # Links
        self.add_link("node1.output_image->node2.input_image")
        self.add_link("node1.output_image->"
                      "intermediate_out.one_switch_intermediate_out")

        # exports
        self.export_parameter("node1", "input_image", "input_image1")
        self.export_parameter("node2", "output_image", "output_image2")

        self.node_position = {
            'inputs': (-157.0, 67.8998),
            'intermediate_out': (265.72604, 205.80563),
            'node1': (46.40114, 102.8998),
            'node2': (298.72604, 22.0),
            'outputs': (540.34484, 109.8998)}

class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = executable(MyPipelineWithOptOut)

    def test_way1(self):
        workflow_repr = self.pipeline.workflow_ordered_nodes()
        workflow_repr = '->'.join(x.name.rsplit('.', 1)[-1]
                                  for x in workflow_repr)
        self.assertEqual(workflow_repr, "node1->node2")

    @unittest.skip('reimplementation expected for capsul v3')
    def test_way2(self):
        workflow_repr = self.pipeline.workflow_ordered_nodes()
        workflow_repr = '->'.join(x.name.rsplit('.', 1)[-1]
                                  for x in workflow_repr)
        self.assertEqual(workflow_repr, "node1->node2")
        self.assertEqual(self.pipeline.nodes["intermediate_out"].switch,
                         "_none")
        self.pipeline.intermediate_out = '/tmp/a_file.txt'
        self.assertEqual(self.pipeline.nodes["intermediate_out"].switch, "one")
        self.assertEqual(self.pipeline.nodes["node1"].output_image,
                         self.pipeline.intermediate_out)
        self.pipeline.intermediate_out = undefined
        self.assertEqual(self.pipeline.nodes["intermediate_out"].switch,
                         "_none")
        self.assertEqual(
            getattr(self.pipeline.nodes["node1"], 'output_image', undefined),
            undefined)

    @unittest.skip('reimplementation expected for capsul v3')
    def test_xml(self):
        from capsul.pipeline import xml
        temp = tempfile.mkstemp(suffix='.xml')
        try:
            os.close(temp[0])
            xml.save_xml_pipeline(self.pipeline, temp[1])
            pipeline = get_process_instance(temp[1])
            self.assertEqual(len(pipeline.nodes), len(self.pipeline.nodes))
            pipeline.workflow_ordered_nodes()
            self.assertEqual(isinstance(pipeline.nodes['intermediate_out'],
                                        OptionalOutputSwitch), True)
            self.assertEqual(pipeline.workflow_repr, "node1->node2")
        finally:
            os.unlink(temp[1])

def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    import sys
    verbose = '-v' in sys.argv or '--verbose' in sys.argv

    if verbose:
        from soma.qt_gui.qt_backend import Qt
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = Qt.QApplication.instance()
        if not app:
            app = Qt.QApplication(sys.argv)
        pipeline = executable(MyPipelineWithOptOut)
        pipeline.intermediate_out = '/tmp/a_file.txt'
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1
