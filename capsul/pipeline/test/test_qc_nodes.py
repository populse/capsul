##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import sys
import shutil
import tempfile

# Trait import
from traits.api import File

# Capsul import
from capsul.api import Process
from capsul.api import Pipeline
from capsul.study_config import StudyConfig


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("output", File(optional=False, output=True))

    def _run_process(self):
        self.log_file = "in"


class DummyViewer(Process):
    """ Dummy Test Viewer
    """
    def __init__(self):
        super(DummyViewer, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

    def _run_process(self):
        self.log_file = "in"


class MySubPipeline(Pipeline):
    """ Simple Pipeline to test Viewer Nodes
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("subprocess",
                         "capsul.pipeline.test.test_qc_nodes.DummyProcess")
        self.add_process("subviewer",
                         "capsul.pipeline.test.test_qc_nodes.DummyViewer")

        # Links
        self.add_link("subprocess.output->subviewer.input")

        # Change node type
        self.nodes["subviewer"].node_type = "view_node"

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
                         "capsul.pipeline.test.test_qc_nodes.DummyViewer")

        # Links
        self.add_link("process.output->viewer.input")

        # Change node type
        self.nodes["viewer"].node_type = "view_node"

        # Export outputs
        self.export_parameter("process", "output")


class TestQCNodes(unittest.TestCase):
    """ Test pipeline node types.
    """

    def setUp(self):
        """ Initialize the TestQCNodes class
        """
        self.pipeline = MyPipeline()
        self.output_directory = tempfile.mkdtemp()
        self.study_config = StudyConfig(output_directory=self.output_directory)

    def __del__(self):
        """ Remove temporary items.
        """
        shutil.rmtree(self.output_directory)

    def test_qc_active(self):
        """ Method to test if the run qc option works properly.
        """
        # Execute all the pipeline nodes
        self.study_config.run(self.pipeline, executer_qc_nodes=True)

        # Get the list of all the nodes that havec been executed
        execution_list = self.pipeline.workflow_ordered_nodes()

        # Go through all the executed nodes
        for process_node in execution_list:

            # Get the process instance that has been executed
            process_instance = process_node.process

            # Check that the node has been executed
            self.assertEqual(process_instance.log_file, "in")

    def test_qc_inactive(self):
        """ Method to test if the run qc option works properly.
        """
        # Execute all the pipeline nodes
        self.study_config.run(self.pipeline, executer_qc_nodes=False)

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
    print "RETURNCODE: ", test()

