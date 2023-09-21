# -*- coding: utf-8 -*-

import unittest
import os.path as osp
from soma.controller import File
from capsul.api import Capsul, Process, Pipeline
from capsul.execution_context import CapsulWorkflow
import tempfile
import shutil


class DummyProcess(Process):
    """ Dummy Test Process
    """
    def __init__(self, definition):
        super(DummyProcess, self).__init__(definition)

        # inputs
        self.add_field("input", File, optional=False)

        # outputs
        self.add_field("output", File, write=True)

    def execute(self, context=None):
        with open(self.output, 'w') as f:
            print('node', self.name, ', input:', self.input, file=f)
            with open(self.input) as g:
                for l in g:
                    print('    %s' % l[:-1], file=f)
        #self.output = self.input


class DummyProcessSPM(DummyProcess):
    """ Dummy Test Process with config requirement
    """
    # requirements = {'spm': {'standalone': True}}


class DummyListProcess(Process):
    def __init__(self, definition):
        super(DummyListProcess, self).__init__(definition)

        # inputs
        self.add_field("inputs", list[File], optional=False)

        # outputs
        self.add_field("output", File, output=True)

    def execute(self, context=None):
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
        self.capsul = Capsul(database_path='')
        self.pipeline = self.capsul.executable(DummyPipeline)
        self.tmpdir = tempfile.mkdtemp()
        self.capsul.config.databases['builtin']['path'] \
            = osp.join(self.tmpdir, 'capsul_engine_database.rdb')
        self.pipeline.input = osp.join(self.tmpdir, 'file_in.nii')
        self.pipeline.output1 = osp.join(self.tmpdir, '/tmp/file_out1.nii')
        self.pipeline.output2 = osp.join(self.tmpdir, '/tmp/file_out2.nii')
        self.pipeline.output3 = osp.join(self.tmpdir, '/tmp/file_out3.nii')

    def tearDown(self):
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_full_wf(self):
        self.pipeline.enable_all_pipeline_steps()
        wf = CapsulWorkflow(self.pipeline, create_output_dirs=False)
        # 4 jobs
        self.assertEqual(len(wf.jobs), 4)
        # 3 deps
        self.assertEqual(sum(len(job['wait_for']) for job in wf.jobs.values()),
                         3)
        wf = CapsulWorkflow(self.pipeline, create_output_dirs=True)
        # 5 jobs with the directories creation
        self.assertEqual(len(wf.jobs), 5)
        # 4 deps
        self.assertEqual(sum(len(job['wait_for']) for job in wf.jobs.values()),
                         4)

    def test_partial_wf1(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step3 = False
        wf = CapsulWorkflow(self.pipeline, create_output_dirs=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(sum(len(job['wait_for'])
                             for job in wf.jobs.values()), 2)

    def test_partial_wf2(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step2 = False
        wf = CapsulWorkflow(self.pipeline, create_output_dirs=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(sum(len(job['wait_for'])
                             for job in wf.jobs.values()), 0)

    def test_partial_wf3_fail(self):
        self.pipeline.enable_all_pipeline_steps()
        self.pipeline.pipeline_steps.step1 = False
        wf = CapsulWorkflow(self.pipeline, create_output_dirs=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(sum(len(job['wait_for'])
                             for job in wf.jobs.values()), 2)

    def test_wf_run(self):
        pipeline = self.pipeline
        pipeline.enable_all_pipeline_steps()

        with open(pipeline.input, 'w') as f:
            print('MAIN INPUT', file=f)
        with self.capsul.engine() as engine:
            engine.run(pipeline)

        self.assertTrue(osp.exists(pipeline.output1))
        self.assertTrue(osp.exists(pipeline.output2))
        self.assertTrue(osp.exists(pipeline.output3))
        lens = [4, 5, 5]
        for o in range(3):
            with open(getattr(pipeline, 'output%d' % (o+1))) as f:
                text = f.read()
                self.assertEqual(len(text.split('\n')), lens[o])

    def test_iter_without_temp(self):
        pipeline = Capsul.executable(DummyPipelineIterSimple)
        self.assertTrue(pipeline is not None)
        niter = 2
        pipeline.input = [osp.join(self.tmpdir, 'file_in%d' % i)
                          for i in range(niter)]
        pipeline.output = osp.join(self.tmpdir, 'file_out')
        pipeline.intermediate = [osp.join(self.tmpdir, 'file_out1'),
                                 osp.join(self.tmpdir, 'file_out2')]

        wf = CapsulWorkflow(pipeline, create_output_dirs=False)
        njobs = niter + 1  # 1 after
        self.assertEqual(len(wf.jobs), njobs)

        for i, filein in enumerate(pipeline.input):
            with open(filein, 'w') as f:
                print('MAIN INPUT %d' % i, file=f)
        with self.capsul.engine() as engine:
            status = engine.run(pipeline)

        self.assertEqual(status, 'ended')
        self.assertTrue(osp.exists(pipeline.output))
        olen = 12
        with open(pipeline.output) as f:
            text = f.read()
            self.assertEqual(len(text.split('\n')), olen)

    def test_iter_workflow(self):
        pipeline = Capsul.executable(DummyPipelineIter)

        self.assertTrue(pipeline is not None)
        niter = 2
        pipeline.input = [osp.join(self.tmpdir, 'file_in%d' % i)
                          for i in range(niter)]
        pipeline.output1 = osp.join(self.tmpdir, 'file_out1')
        pipeline.output2 = osp.join(self.tmpdir, 'file_out2')
        pipeline.output3 = osp.join(self.tmpdir, 'file_out3')

        wf = CapsulWorkflow(pipeline, create_output_dirs=False)
        njobs = 4*niter + 3  # 3 after
        self.assertEqual(len(wf.jobs), njobs)

        for i, filein in enumerate(pipeline.input):
            with open(filein, 'w') as f:
                print('MAIN INPUT %d' % i, file=f)

        with self.capsul.engine() as engine:
            status = engine.run(pipeline)

        self.assertEqual(status, 'ended')
        self.assertTrue(osp.exists(pipeline.output1))
        self.assertTrue(osp.exists(pipeline.output2))
        self.assertTrue(osp.exists(pipeline.output3))
        lens = [16, 20, 20]
        for o in range(3):
            with open(getattr(pipeline, 'output%d' % (o+1))) as f:
                text = f.read()
                self.assertEqual(len(text.split('\n')), lens[o])


if __name__ == "__main__":
    import sys
    from soma.qt_gui import qt_backend
    from soma.qt_gui.qt_backend import QtGui
    from capsul.qt_gui.widgets import PipelineDeveloperView

    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication(sys.argv)
    pipeline = Capsul.executable(DummyPipeline)
    pipeline.input = '/tmp/file_in.nii'
    pipeline.output1 = '/tmp/file_out1.nii'
    pipeline.output2 = '/tmp/file_out2.nii'
    pipeline.output3 = '/tmp/file_out3.nii'
    view1 = PipelineDeveloperView(pipeline, show_sub_pipelines=True,
                                    allow_open_controller=True)
    view1.show()

    pipeline2 = Capsul.executable(DummyPipelineIterSimple)
    pipeline2.input = ['/tmp/file_in1.nii', '/tmp/file_in2.nii']
    pipeline2.output = '/tmp/file_out.nii'
    pipeline2.intermediate = ['/tmp/file_out1',
                                '/tmp/file_out2']
    view2 = PipelineDeveloperView(pipeline2, show_sub_pipelines=True,
                                    allow_open_controller=True)
    view2.show()

    pipeline3 = Capsul.executable(DummyPipelineIter)
    pipeline3.input = ['/tmp/file_in1.nii', '/tmp/file_in2.nii']
    pipeline3.output1 = '/tmp/file_out1.nii'
    pipeline3.output2 = '/tmp/file_out2.nii'
    pipeline3.output3 = '/tmp/file_out3.nii'
    view3 = PipelineDeveloperView(pipeline3, show_sub_pipelines=True,
                                    allow_open_controller=True)
    view3.show()

    app.exec_()
    del view1
    del view2
    del view3
