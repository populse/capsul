##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

import unittest
import os
import sys
from traits.api import File
from capsul.api import Process
from capsul.api import Pipeline, PipelineNode
from capsul.pipeline import pipeline_workflow
from capsul.study_config.study_config import StudyConfig


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self):
        super(DummyProcess, self).__init__()

        # inputs
        self.add_trait("input", File(optional=False))

        # outputs
        self.add_trait("output", File(output=True))

    def _run_process(self):
        self.output = self.input
        self.output = self.output

class DummyPipeline(Pipeline):

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess')
        self.add_process(
            "node2",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess')
        self.add_process(
            "node3",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess')
        self.add_process(
            "node4",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess')
        # Links
        self.add_link("node1.output->node2.input")
        self.add_link("node2.output->node3.input")
        self.add_link("node2.output->node4.input")
        # Outputs
        self.export_parameter("node2", "output",
                              pipeline_parameter="output1",
                              is_optional=True)
        self.export_parameter("node3", "output",
                              pipeline_parameter="output2",
                              is_optional=True)
        self.export_parameter("node4", "output",
                              pipeline_parameter="output3",
                              is_optional=True)

        self.add_pipeline_step('step1', ['node1'])
        self.add_pipeline_step('step2', ['node2'])
        self.add_pipeline_step('step3', ['node3'])

        self.node_position = {'inputs': (54.0, 298.0),
            'node1': (173.0, 168.0),
            'node2': (259.0, 320.0),
            'node3': (405.0, 142.0),
            'node4': (450.0, 450.0),
            'outputs': (518.0, 278.0)}


class TestPipelineWorkflow(unittest.TestCase):

    def setUp(self):
        self.pipeline = DummyPipeline()
        self.pipeline.input = '/tmp/file_in.nii'
        self.pipeline.output1 = '/tmp/file_out1.nii'
        self.pipeline.output2 = '/tmp/file_out2.nii'
        self.pipeline.output3 = '/tmp/file_out3.nii'
        study_config = StudyConfig() #modules=StudyConfig.default_modules \
                                   #+ ['FomConfig'])
        study_config.input_directory = '/tmp'
        study_config.somaworkflow_computing_resource = 'localhost'
        study_config.somaworkflow_computing_resources_config.localhost = {
            'transfer_paths': [study_config.input_directory],
        }
        self.study_config = study_config

    def test_full_wf(self):
        self.pipeline.enable_all_pipeline_steps()
        wf = pipeline_workflow.workflow_from_pipeline(
            self.pipeline, study_config=self.study_config)
        # 5 jobs including the output directories creation
        self.assertEqual(len(wf.jobs), 5)
        # 4 deps (1 additional, dirs->node1)
        self.assertEqual(len(wf.dependencies), 4)

    def test_partial_wf1(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step3 = False
        wf = pipeline_workflow.workflow_from_pipeline(
            self.pipeline, study_config=self.study_config,
            create_directories=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(len(wf.dependencies), 2)

    def test_partial_wf2(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step2 = False
        wf = pipeline_workflow.workflow_from_pipeline(
            self.pipeline, study_config=self.study_config,
            create_directories=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(len(wf.dependencies), 0)

    def test_partial_wf3_fail(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step1 = False
        try:
            wf = pipeline_workflow.workflow_from_pipeline(
                self.pipeline, study_config=self.study_config)
        except ValueError:
            pass # OK
        else:
            # no exception, this is a bug.
            raise ValueError('workflow should have failed due to a missing '
                'temporary file')


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineWorkflow)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    verbose = False
    if len(sys.argv) >= 2 and sys.argv[1] in ('-v', '--verbose'):
        verbose = True

    print("RETURNCODE: ", test())

    if verbose:
        import sys
        from soma.qt_gui import qt_backend
        qt_backend.set_qt_backend('PyQt4')
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = DummyPipeline()
        pipeline.input = '/tmp/file_in.nii'
        pipeline.output1 = '/tmp/file_out1.nii'
        pipeline.output2 = '/tmp/file_out2.nii'
        pipeline.output3 = '/tmp/file_out3.nii'
        view1 = PipelineDevelopperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()
        app.exec_()
        del view1

