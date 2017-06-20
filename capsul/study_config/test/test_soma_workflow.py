##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function
import os
import sys
import unittest
import socket
import shutil
import tempfile
if sys.version_info[0] >= 3:
    import io as StringIO
else:
    import StringIO
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


class TestSomaWorkflow(unittest.TestCase):

    def setUp(self):
        default_config = SortedDictionary(
            ("use_soma_workflow", True)
        )
        # use a custom temporary soma-workflow dir to avoid concurrent
        # access problems
        tmpdb = tempfile.mkstemp('', prefix='soma_workflow')
        os.close(tmpdb[0])
        os.unlink(tmpdb[1])
        self.soma_workflow_temp_dir = tmpdb[1]
        os.mkdir(self.soma_workflow_temp_dir)
        swf_conf = '[%s]\nSOMA_WORKFLOW_DIR = %s\n' \
            % (socket.gethostname(), tmpdb[1])
        swconfig.Configuration.search_config_path \
            = staticmethod(lambda : StringIO.StringIO(swf_conf))
        self.study_config = StudyConfig(init_config=default_config)
        self.atomic_pipeline = MyAtomicPipeline()
        self.composite_pipeline = MyCompositePipeline()

    def tearDown(self):
        shutil.rmtree(self.soma_workflow_temp_dir)

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
        self.assertEqual(dependencies.count(("node1", "node2")), 1)
        self.assertEqual(dependencies.count(("node1", "node3")), 2)
        self.assertEqual(dependencies.count(("node2", "node4")), 1)
        self.assertEqual(dependencies.count(("node3", "node4")), 2)
        self.assertEqual(dependencies.count(("node1", "node2_input")), 1)
        self.assertEqual(dependencies.count(("node2_output", "node4")), 1)
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
        from soma.qt_gui import qt_backend
        qt_backend.set_qt_backend('PyQt4')
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        #app = QtGui.QApplication(sys.argv)
        #pipeline = MyCompositePipeline()
        #view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True)
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
        view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True)
        view1.show()
        view2 = PipelineUserView(pipeline)
        view2.show()
        if not has_qapp:
            app.exec_()
            del view1
