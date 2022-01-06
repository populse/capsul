# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
import os
import os.path as osp
import sys
from traits.api import File, List
from capsul.api import Process
from capsul.api import Pipeline, PipelineNode
from capsul.pipeline import pipeline_workflow
from capsul.study_config.study_config import StudyConfig
import tempfile
import shutil


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
        with open(self.output, 'w') as f:
            print('node', self.name, ', input:', self.input, file=f)
            with open(self.input) as g:
                for l in g:
                    print('    %s' % l[:-1], file=f)
        #self.output = self.input


class DummyProcessSPM(DummyProcess):
    """ Dummy Test Process with config requirement
    """
    def requirements(self):
        return {'spm': 'standalone == True'}


class DummyListProcess(Process):
    def __init__(self):
        super(DummyListProcess, self).__init__()

        # inputs
        self.add_trait("inputs", List(File(optional=False)))

        # outputs
        self.add_trait("output", File(output=True))

    def _run_process(self):
        with open(self.output, 'w') as f:
            print('node', self, ', inputs:', self.inputs, file=f)
            for inp in self.inputs:
                print('input:', inp, file=f)
                with open(inp) as g:
                    in_lines = g.readlines()
                    print('\n'.join(['    %s' % l for l in in_lines]), file=f)


class DummyPipeline(Pipeline):

    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess')
        self.add_process(
            "node2",
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcessSPM')
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


class DummyPipelineIter(Pipeline):

    def pipeline_definition(self):
        self.add_iterative_process(
            'dummy_iter', DummyPipeline,
            iterative_plugs=['input', 'output1', 'output2', 'output3'])
        self.add_process(
            'after1',
            'capsul.pipeline.test.test_pipeline_workflow.DummyListProcess')
        self.add_process(
            'after2',
            'capsul.pipeline.test.test_pipeline_workflow.DummyListProcess')
        self.add_process(
            'after3',
            'capsul.pipeline.test.test_pipeline_workflow.DummyListProcess')
        # links
        self.add_link('dummy_iter.output1->after1.inputs')
        self.add_link('dummy_iter.output2->after2.inputs')
        self.add_link('dummy_iter.output3->after3.inputs')
        # Outputs
        self.export_parameter("after1", "output",
                              pipeline_parameter="output1",
                              is_optional=True)
        self.export_parameter("after2", "output",
                              pipeline_parameter="output2",
                              is_optional=True)
        self.export_parameter("after3", "output",
                              pipeline_parameter="output3",
                              is_optional=True)


class DummyPipelineIterSimple(Pipeline):

    def pipeline_definition(self):
        self.add_iterative_process(
            'dummy_iter',
            'capsul.pipeline.test.test_pipeline_workflow.DummyProcess',
            iterative_plugs=['input', 'output'])
        self.add_process(
            'after',
            'capsul.pipeline.test.test_pipeline_workflow.DummyListProcess')
        # links
        self.add_link('dummy_iter.output->after.inputs')
        self.export_parameter('dummy_iter', 'output', 'intermediate')


class TestPipelineWorkflow(unittest.TestCase):

    def setUp(self):
        study_config = StudyConfig() #modules=StudyConfig.default_modules \
                                   #+ ['FomConfig'])
        self.pipeline = DummyPipeline()
        self.pipeline.set_study_config(study_config)
        self.tmpdir = tempfile.mkdtemp()
        self.pipeline.input = osp.join(self.tmpdir, 'file_in.nii')
        self.pipeline.output1 = osp.join(self.tmpdir, '/tmp/file_out1.nii')
        self.pipeline.output2 = osp.join(self.tmpdir, '/tmp/file_out2.nii')
        self.pipeline.output3 = osp.join(self.tmpdir, '/tmp/file_out3.nii')
        study_config.input_directory = self.tmpdir
        study_config.somaworkflow_computing_resource = 'localhost'
        study_config.somaworkflow_computing_resources_config.localhost = {
            'transfer_paths': [study_config.input_directory],
        }
        self.study_config = study_config
        engine = self.study_config.engine
        engine.load_module('spm')
        #with engine.settings as session:
            #ids = [c.config_id for c in session.configs('spm', 'global')]
            #for id in ids:
                #session.remove_config('spm', 'global', {'config_id': id})
            #session.new_config('spm', 'global',
                               #{'version': '12', 'standalone': True})
        study_config.spm_standalone = True
        study_config.spm_version = '12'
        study_config.somaworkflow_keep_succeeded_workflows = False
        self.exec_ids = []

    def tearDown(self):
        for exec_id in self.exec_ids:
            self.study_config.engine.dispose(exec_id)
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_requirements(self):
        engine = self.study_config.engine
        with engine.settings as session:
            session.remove_config('spm', 'global', 'spm12-standalone')
        self.pipeline.enable_all_pipeline_steps()
        with self.assertRaises(ValueError):
            wf = pipeline_workflow.workflow_from_pipeline(
                self.pipeline, study_config=self.study_config)


    def test_full_wf(self):
        engine = self.study_config.engine
        self.pipeline.enable_all_pipeline_steps()
        wf = pipeline_workflow.workflow_from_pipeline(
            self.pipeline, study_config=self.study_config)
        # 5 jobs including the output directories creation
        self.assertEqual(len(wf.jobs), 5)
        # 4 deps (1 additional, dirs->node1)
        self.assertEqual(len(wf.dependencies), 4)

        # DEBUG
        #import soma_workflow.client as swc
        #swc.Helper.serialize('/tmp/workflow1.wf', wf)

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

    def test_wf_run(self):
        print()
        engine = self.study_config.engine
        pipeline = self.pipeline
        pipeline.enable_all_pipeline_steps()
        with open(pipeline.input, 'w') as f:
            print('MAIN INPUT', file=f)

        exec_id = engine.start(pipeline)
        self.exec_ids.append(exec_id)
        print('execution started')
        status = engine.wait(exec_id, pipeline=pipeline)
        print('finished:', status)
        self.assertTrue(osp.exists(pipeline.output1))
        self.assertTrue(osp.exists(pipeline.output2))
        self.assertTrue(osp.exists(pipeline.output3))
        lens = [4, 5, 5]
        for o in range(3):
            #print('** output%d: **' % (o+1))
            with open(getattr(pipeline, 'output%d' % (o+1))) as f:
                text = f.read()
                #print(text)
                self.assertEqual(len(text.split('\n')), lens[o])

    def test_iter_workflow_without_temp(self):
        engine = self.study_config.engine
        pipeline = engine.get_process_instance(DummyPipelineIterSimple)
        self.assertTrue(pipeline is not None)
        niter = 2
        pipeline.input = [osp.join(self.tmpdir, 'file_in%d' % i)
                          for i in range(niter)]
        pipeline.output = osp.join(self.tmpdir, 'file_out')
        pipeline.intermediate = [osp.join(self.tmpdir, 'file_out1'),
                                 osp.join(self.tmpdir, 'file_out2')]

        wf = pipeline_workflow.workflow_from_pipeline(
            pipeline, study_config=self.study_config,
            create_directories=False)
        njobs = niter + 1 + 2  # 1 after + map / reduce
        self.assertEqual(len(wf.jobs), njobs)
        #for job in wf.jobs:
            #print(job.name)
            #print(job.command)
            #print('ref inputs:', job.referenced_input_files)
            #print('ref outputs:', job.referenced_output_files)
            #print()

        #import soma_workflow.client as swc
        #swc.Helper.serialize('/tmp/workflow2.wf', wf)

        for i, filein in enumerate(pipeline.input):
            with open(filein, 'w') as f:
                print('MAIN INPUT %d' % i, file=f)

        exec_id = engine.start(pipeline, workflow=wf)
        self.exec_ids.append(exec_id)
        print('execution started')
        status = engine.wait(exec_id, pipeline=pipeline)
        print('finished:', status)

        self.assertEqual(status, 'workflow_done')
        self.assertTrue(osp.exists(pipeline.output))
        olen = 12
        #print('** output: **')
        with open(pipeline.output) as f:
            text = f.read()
            #print(text)
            self.assertEqual(len(text.split('\n')), olen)

    def test_iter_workflow(self):
        engine = self.study_config.engine
        pipeline = engine.get_process_instance(DummyPipelineIter)
        self.assertTrue(pipeline is not None)
        niter = 2
        pipeline.input = [osp.join(self.tmpdir, 'file_in%d' % i)
                          for i in range(niter)]
        pipeline.output1 = osp.join(self.tmpdir, 'file_out1')
        pipeline.output2 = osp.join(self.tmpdir, 'file_out2')
        pipeline.output3 = osp.join(self.tmpdir, 'file_out3')

        wf = pipeline_workflow.workflow_from_pipeline(
            pipeline, study_config=self.study_config,
            create_directories=False)
        njobs = 4*niter + 3 + 2  # 3 after + map / reduce
        self.assertEqual(len(wf.jobs), njobs)
        #for job in wf.jobs:
            #print(job.name)
            #print(job.command)
            #print('ref inputs:', job.referenced_input_files)
            #print('ref outputs:', job.referenced_output_files)
            #print()

        #import soma_workflow.client as swc
        #swc.Helper.serialize('/tmp/workflow.wf', wf)

        for i, filein in enumerate(pipeline.input):
            with open(filein, 'w') as f:
                print('MAIN INPUT %d' % i, file=f)

        exec_id = engine.start(pipeline, workflow=wf)
        self.exec_ids.append(exec_id)

        print('execution started')
        status = engine.wait(exec_id, pipeline=pipeline)
        print('finished:', status)

        self.assertEqual(status, 'workflow_done')
        self.assertTrue(osp.exists(pipeline.output1))
        self.assertTrue(osp.exists(pipeline.output2))
        self.assertTrue(osp.exists(pipeline.output3))
        lens = [16, 20, 20]
        for o in range(3):
            #print('** output%d: **' % (o+1))
            with open(getattr(pipeline, 'output%d' % (o+1))) as f:
                text = f.read()
                #print(text)
                self.assertEqual(len(text.split('\n')), lens[o])


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
        # qt_backend.set_qt_backend('PyQt4')
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        pipeline = DummyPipeline()
        pipeline.input = '/tmp/file_in.nii'
        pipeline.output1 = '/tmp/file_out1.nii'
        pipeline.output2 = '/tmp/file_out2.nii'
        pipeline.output3 = '/tmp/file_out3.nii'
        view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view1.show()

        pipeline2 = DummyPipelineIterSimple()
        pipeline2.input = ['/tmp/file_in1.nii', '/tmp/file_in2.nii']
        pipeline2.output = '/tmp/file_out.nii'
        pipeline2.intermediate = ['/tmp/file_out1',
                                  '/tmp/file_out2']
        view2 = PipelineDeveloperView(pipeline2, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view2.show()

        pipeline3 = DummyPipelineIter()
        pipeline3.input = ['/tmp/file_in1.nii', '/tmp/file_in2.nii']
        pipeline3.output1 = '/tmp/file_out1.nii'
        pipeline3.output2 = '/tmp/file_out2.nii'
        pipeline3.output3 = '/tmp/file_out3.nii'
        view3 = PipelineDeveloperView(pipeline3, show_sub_pipelines=True,
                                       allow_open_controller=True)
        view3.show()

        app.exec_()
        del view1
