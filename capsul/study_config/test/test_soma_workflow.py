#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function
import sys
import unittest
from traits.api import File
from capsul.study_config import StudyConfig
from capsul.process import Process
from capsul.pipeline import Pipeline
from soma.sorted_dictionary import SortedDictionary
from capsul.pipeline.pipeline_workflow import workflow_from_pipeline


class EchoProcess(Process):
    """ Dummy Echo Process
    """
    def _run_process(self):
        descripton = "{0}: ".format(self.id)
        for parameter in self.user_traits():
            descripton += "{0} = {1} ".format(parameter,
                                              repr(getattr(self, parameter)))
        print(descripton)


class Process_1(EchoProcess):
    """ Dummy Test Process
    """
    def __init__(self):
        super(Process_1, self).__init__()
        # Inputs
        self.add_trait("input_image", File(optional=True))
        # Outputs
        self.add_trait("output_image", File(optional=True, output=True))

    def get_commandline(self):
        return super(Process_1, self).get_commandline()


class Process_2(EchoProcess):
    """ Dummy Test Process
    """
    def __init__(self):
        super(Process_2, self).__init__()
        # Inputs
        self.add_trait("input_image", File(optional=True))
        # Outputs
        self.add_trait("output_image", File(optional=True, output=True))

    def get_commandline(self):
        return super(Process_2, self).get_commandline()


class Process_3(EchoProcess):
    """ Dummy Test Process
    """
    def __init__(self):
        super(Process_3, self).__init__()
        # Inputs
        self.add_trait("input_image", File(optional=True))
        # Outputs
        self.add_trait("output_image", File(optional=True, output=True))

    def get_commandline(self):
        return super(Process_3, self).get_commandline()


class Process_4(EchoProcess):
    """ Dummy Test Process
    """
    def __init__(self):
        super(Process_4, self).__init__()
        # Inputs
        self.add_trait("input_image", File(optional=True))
        self.add_trait("other_image", File(optional=True))
        # Outputs
        self.add_trait("output_image", File(optional=True, output=True))

    def get_commandline(self):
        return super(Process_4, self).get_commandline()


class MyAtomicPipeline(Pipeline):
    """ Simple Pipeline to test soma workflow
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node1",
            "capsul.study_config.test.test_soma_workflow.Process_1")
        self.add_process("node2",
            "capsul.study_config.test.test_soma_workflow.Process_2")
        self.add_process("node3",
            "capsul.study_config.test.test_soma_workflow.Process_3")
        self.add_process("node4",
            "capsul.study_config.test.test_soma_workflow.Process_4")

        # Links
        self.add_link("node1.output_image->node2.input_image")
        self.add_link("node1.output_image->node3.input_image")
        self.add_link("node2.output_image->node4.input_image")
        self.add_link("node3.output_image->node4.other_image")

        # Outputs
        self.export_parameter("node1", "input_image")
        self.export_parameter("node4", "output_image")


class MyCompositePipeline(Pipeline):
    """ Composite Pipeline to test soma workflow
    """
    def pipeline_definition(self):

        # Create processes
        self.add_process("node1",
            "capsul.study_config.test.test_soma_workflow.Process_1")
        self.add_process("node2",
            "capsul.study_config.test.test_soma_workflow.MyAtomicPipeline")
        self.add_process("node3",
            "capsul.study_config.test.test_soma_workflow.Process_3")
        self.add_process("node4",
            "capsul.study_config.test.test_soma_workflow.Process_4")

        # Links
        self.add_link("node1.output_image->node2.input_image")
        self.add_link("node1.output_image->node3.input_image")
        self.add_link("node2.output_image->node4.input_image")
        self.add_link("node3.output_image->node4.other_image")

        # Outputs
        self.export_parameter("node1", "input_image")
        self.export_parameter("node4", "output_image")


class TestSomaWorkflow(unittest.TestCase):

    def setUp(self):
        default_config = SortedDictionary(
            ("use_soma_workflow", True)
        )
        self.study_config = StudyConfig(default_config)
        self.atomic_pipeline = MyAtomicPipeline()
        self.composite_pipeline = MyCompositePipeline()

    def test_atomic_dependencies(self):
        workflow = workflow_from_pipeline(self.atomic_pipeline)
        dependencies = [(x.name, y.name) for x, y in workflow.dependencies]
        self.assertTrue(len(dependencies) == 4)
        self.assertTrue(("Process_1", "Process_2") in dependencies)
        self.assertTrue(("Process_1", "Process_3") in dependencies)
        self.assertTrue(("Process_2", "Process_4") in dependencies)
        self.assertTrue(("Process_3", "Process_4") in dependencies)
        self.assertEqual(workflow.groups, [])

    def test_atomic_execution(self):
        self.atomic_pipeline.workflow_ordered_nodes()
        if sys.version_info >= (2, 7):
            self.assertIn(self.atomic_pipeline.workflow_repr,
                          ('node1->node3->node2->node4',
                          'node1->node2->node3->node4'))
        else: # python 2.6 unittest does not have assertIn()
            self.assertTrue(self.atomic_pipeline.workflow_repr in \
                ('node1->node3->node2->node4',
                'node1->node2->node3->node4'))
        self.study_config.run(self.atomic_pipeline)

    def test_composite_dependencies(self):
        workflow = workflow_from_pipeline(self.composite_pipeline)
        dependencies = [(x.name, y.name) for x, y in workflow.dependencies]
        self.assertTrue(len(dependencies) == 16)
        self.assertEqual(dependencies.count(("Process_1", "Process_2")), 1)
        self.assertEqual(dependencies.count(("Process_1", "Process_3")), 2)
        self.assertEqual(dependencies.count(("Process_2", "Process_4")), 1)
        self.assertEqual(dependencies.count(("Process_3", "Process_4")), 2)
        self.assertEqual(dependencies.count(("Process_1", "node2_input")), 1)
        self.assertEqual(dependencies.count(("node2_output", "Process_4")), 1)
        self.assertTrue(len(workflow.groups) == 1)

    def test_composite_execution(self):
        self.composite_pipeline.workflow_ordered_nodes()
        self.assertEqual(self.composite_pipeline.workflow_repr,
                         "node1->node3->node2->node4")
        self.study_config.run(self.composite_pipeline)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSomaWorkflow)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    #print("RETURNCODE: ", test())

    import sys
    from PySide import QtGui
    from capsul.apps_qt.base.pipeline_widgets import PipelineDevelopperView

    #app = QtGui.QApplication(sys.argv)
    #pipeline = MyCompositePipeline()
    #view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True)
    #view1.show()
    #app.exec_()
    #del view1

    from capsul.apps_qt.base.pipeline_widgets import PipelineUserView
    app = QtGui.QApplication(sys.argv)
    pipeline = MyCompositePipeline()
    view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True)
    view1.show()
    view2 = PipelineUserView(pipeline)
    view2.show()
    app.exec_()
    del view1
