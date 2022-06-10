import unittest
import sys
import shutil
import tempfile

# Controller import
from soma.controller import File

# Capsul import
from capsul.api import Capsul, Process, Pipeline


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=File)

        # outputs
        self.add_field("output", File, write=True)
        self.add_field("log_file", str, output=True)

    def execute(self, context):
        self.log_file = "in"


class DummyViewer(Process):
    """ Dummy Test Viewer
    """
    def __init__(self, definition):
        super().__init__(definition)

        self.add_field("input", File)
        self.add_field("log_file", str, output=True)

    def execute(self, context):
        self.log_file = "in"


class MySubPipeline(Pipeline):
    """ Simple Pipeline to test Viewer Nodes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("subprocess",
                         "capsul.pipeline.test.test_qc_nodes.DummyProcess",
                         do_not_export=['log_file'])
        self.add_process("subviewer",
                         "capsul.pipeline.test.test_qc_nodes.DummyViewer",
                         do_not_export=['log_file'])

        # Links
        self.add_link("subprocess.output->subviewer.input")

        # Export outputs
        self.export_parameter("subprocess", "output")


class MyPipeline(Pipeline):
    """ Simple Pipeline to test Viewer Nodes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("process",
                         "capsul.pipeline.test.test_qc_nodes.MySubPipeline")
        self.add_process("viewer",
                         "capsul.pipeline.test.test_qc_nodes.DummyViewer",
                         do_not_export=['log_file'])

        # Links
        self.add_link("process.output->viewer.input")

        # Export outputs
        self.export_parameter("process", "output")


class TestQCNodes(unittest.TestCase):
    """ Test pipeline node types.
    """

    def setUp(self):
        """ Initialize the TestQCNodes class
        """
        self.pipeline = Capsul.executable(MyPipeline)
        self.pipeline.input = 'dummy_input'
        self.pipeline.output = 'dummy_output'
        self.output_directory = tempfile.mkdtemp()
        self.capsul = Capsul()

    def tearDown(self):
        """ Remove temporary items.
        """
        Capsul.delete_singleton()
        shutil.rmtree(self.output_directory)

    @unittest.skip('reimplementation expected for capsul v3')
    def test_qc_active(self):
        """ Method to test if the run qc option works properly.
        """
        # Execute all the pipeline nodes
        with self.capsul.engine() as engine:
            engine.run(self.pipeline, timeout=5)

        # self.assertEqual(self.pipeline.nodes['process'].log_file, "in")
        self.assertEqual(self.pipeline.nodes['viewer'].log_file, "in")

    @unittest.skip('reimplementation expected for capsul v3')
    def test_qc_inactive(self):
        """ Method to test if the run qc option works properly.
        """
        # Execute all the pipeline nodes
        self.study_config.run(self.pipeline, execute_qc_nodes=False)

        # Get the list of all the nodes
        execution_list = self.pipeline.workflow_ordered_nodes()

        # Go through all the nodes
        for process_node in execution_list:

            # Get the process instance that may have been executed
            process_instance = process_node.process

            # Check that view nodes are not executed
            if process_node.node_type == "view_node":
                self.assertEqual(process_instance.log_file, None)
            else:
                self.assertEqual(process_instance.log_file, "in")


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQCNodes)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = Capsul.executable(MyPipeline)
    pipeline.input = 'dummy_input'
    pipeline.output = 'dummy_output'
    view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True)
    view1.show()
    app.exec_()
    del view1
