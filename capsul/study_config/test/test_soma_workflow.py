# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import unittest
import socket
import shutil
import tempfile
from traits.api import File
from capsul.api import StudyConfig
from capsul.api import Process
from capsul.api import Pipeline
from soma.sorted_dictionary import SortedDictionary
from capsul.pipeline.pipeline_workflow import workflow_from_pipeline
from soma_workflow import configuration as swconfig


class EchoProcess(Process):
    """ Dummy Echo Process
    """
    def _run_process(self):
        description = "{0}: ".format(self.id)
        for parameter in self.user_traits():
            description += "{0} = {1} ".format(parameter,
                                              repr(getattr(self, parameter)))
        print(description)


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
        cmdline = super(Process_1, self).get_commandline()
        return cmdline


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
        cmdline = super(Process_2, self).get_commandline()
        return cmdline


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
        cmdline = super(Process_3, self).get_commandline()
        return cmdline


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


def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    temp_home_dir = None
    old_home = os.environ.get('HOME')
    try:
        temp_home_dir = tempfile.mkdtemp('', prefix='soma_workflow')
        os.environ['HOME'] = temp_home_dir
        swconfig.change_soma_workflow_directory(temp_home_dir)
    except BaseException:  # clean up in case of interruption
        if old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = old_home
        if temp_home_dir:
            shutil.rmtree(temp_home_dir)
        raise


def tearDownModule():
    if old_home is None:
        del os.environ['HOME']
    else:
        os.environ['HOME'] = old_home
    shutil.rmtree(temp_home_dir)


class TestSomaWorkflow(unittest.TestCase):

    def setUp(self):
        default_config = SortedDictionary(
            ("use_soma_workflow", True),
        )
        self.study_config = StudyConfig(init_config=default_config)
        self.atomic_pipeline = MyAtomicPipeline()
        self.composite_pipeline = MyCompositePipeline()

    def tearDown(self):
        swm = self.study_config.modules['SomaWorkflowConfig']
        swc = swm.get_workflow_controller()
        if swc is not None:
            # stop workflow controller and wait for thread termination
            swc.stop_engine()

    def test_atomic_dependencies(self):
        workflow = workflow_from_pipeline(self.atomic_pipeline)
        dependencies = [(x.name, y.name) for x, y in workflow.dependencies]
        self.assertTrue(len(dependencies) == 4)
        self.assertTrue(("node1", "node2") in dependencies)
        self.assertTrue(("node1", "node3") in dependencies)
        self.assertTrue(("node2", "node4") in dependencies)
        self.assertTrue(("node3", "node4") in dependencies)
        self.assertEqual(workflow.groups, [])

    def test_atomic_execution(self):
        self.atomic_pipeline.workflow_ordered_nodes()
        self.assertIn(self.atomic_pipeline.workflow_repr,
                      ('node1->node3->node2->node4',
                       'node1->node2->node3->node4'))
        self.study_config.run(self.atomic_pipeline)

    def test_composite_dependencies(self):
        workflow = workflow_from_pipeline(self.composite_pipeline)
        dependencies = [(x.name, y.name) for x, y in workflow.dependencies]
        self.assertTrue(len(dependencies) == 8)
        self.assertEqual(dependencies.count(("node1", "node2")), 1)
        self.assertEqual(dependencies.count(("node1", "node3")), 2)
        self.assertEqual(dependencies.count(("node2", "node4")), 1)
        self.assertEqual(dependencies.count(("node3", "node4")), 2)
        self.assertEqual(dependencies.count(("node1", "node1")), 1)
        self.assertEqual(dependencies.count(("node4", "node4")), 1)
        self.assertTrue(len(workflow.groups) == 1)

    def test_composite_execution(self):
        self.composite_pipeline.workflow_ordered_nodes()
        self.assertTrue(
            self.composite_pipeline.workflow_repr in
            ("node1->node3->node2->node4", "node1->node2->node3->node4"))
        self.study_config.run(self.composite_pipeline)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSomaWorkflow)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

    if len(sys.argv) > 1 and '-v' in sys.argv[1:] \
            or '--verbose' in sys.argv[1:]:
        import sys
        #from soma.qt_gui import qt_backend
        #qt_backend.set_qt_backend('PyQt4')
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        #app = QtGui.QApplication(sys.argv)
        #pipeline = MyCompositePipeline()
        #view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True)
        #view1.show()
        #app.exec_()
        #del view1

        from capsul.qt_gui.widgets import PipelineUserView
        if QtGui.QApplication.instance() is not None:
            has_qapp = True
            app = QtGui.QApplication.instance()
        else:
            has_qapp = False
            app = QtGui.QApplication(sys.argv)
        pipeline = MyCompositePipeline()
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True)
        view1.show()
        view2 = PipelineUserView(pipeline)
        view2.show()
        if not has_qapp:
            app.exec_()
            del view1
