from __future__ import print_function

import unittest
from capsul.api import Process, Pipeline, StudyConfig
from capsul.pipeline import pipeline_workflow
from capsul.pipeline import python_export
from capsul.pipeline import xml
import traits.api as traits
import os
import tempfile
import sys


class TestProcess(Process):
    def __init__(self):
        super(TestProcess, self).__init__()
        self.add_trait('in1', traits.File(output=False))
        self.add_trait('model', traits.File(output=False))
        self.add_trait('out1', traits.File(output=True))

    def _run_process(self):
        print('in1:', self.in1)
        print('out1:', self.out1)
        with open(self.out1, 'wb') as f:
            for ifile in self.in1:
                with open(ifile, 'rb') as ff:
                    f.write(ff.read())


class TrainProcess1(Process):
    def __init__(self):
        super(TrainProcess1, self).__init__()
        self.add_trait('in1', traits.List(traits.File(), output=False))
        self.add_trait('out1', traits.File(output=True))


class TrainProcess2(Process):
    def __init__(self):
        super(TrainProcess2, self).__init__()
        self.add_trait('in1', traits.List(traits.File(), output=False))
        self.add_trait('in2', traits.File(output=False))
        self.add_trait('out1', traits.File(output=True))


class Pipeline1(Pipeline):
    def pipeline_definition(self):
        self.add_process('train1', TrainProcess1())
        self.add_process('train2', TrainProcess2())

        self.add_custom_node('LOO',
                             'capsul.pipeline.custom_nodes.exclude_node')
        self.add_custom_node('output_file',
                             'capsul.pipeline.custom_nodes.cat_node.CatNode',
                             parameters={'parameters': ['base', 'subject'],
                                         'concat_plug': 'out_file',
                                         'param_types': ['Directory', 'Str',
                                                         'File'],
                                         'outputs': ['base'],
                                         'separator': os.path.sep,
                                         },
                              make_optional='subject')
        self.nodes['output_file'].subject = 'output_file'

        self.add_custom_node('intermediate_output',
                             'capsul.pipeline.custom_nodes.cat_node.CatNode',
                             parameters={'parameters': ['base', 'sep',
                                                        'subject', 'suffix'],
                                         'concat_plug': 'out_file',
                                         'outputs': ['base'],
                                         'param_types': ['Directory', 'Str',
                                                         'Str', 'Str', 'File']
                                         },
                              make_optional=['subject', 'sep', 'suffix'])
        self.nodes['intermediate_output'].sep = os.sep
        self.nodes['intermediate_output'].subject = 'output_file'
        self.nodes['intermediate_output'].suffix = '_interm'

        self.add_process('test', TestProcess())

        self.add_custom_node('test_output',
                             'capsul.pipeline.custom_nodes.cat_node.CatNode',
                             parameters={'parameters': ['base', 'sep',
                                                        'subject', 'suffix'],
                                         'concat_plug': 'out_file',
                                         'outputs': ['base'],
                                         'param_types': ['Directory', 'Str',
                                                         'Str', 'Str', 'File']
                                         },
                              make_optional=['subject', 'sep', 'suffix'])
        self.nodes['test_output'].sep = os.path.sep
        self.nodes['test_output'].subject = 'output_file'
        self.nodes['test_output'].suffix = '_test_output'

        self.export_parameter('LOO', 'inputs', 'main_inputs')
        self.export_parameter('LOO', 'exclude', 'left_out')
        self.export_parameter('output_file', 'base', 'output_directory')
        self.export_parameter('output_file', 'subject')
        #self.export_parameter('test', 'out1', 'test_output', is_optional=True)
        self.add_link('LOO.filtered->train1.in1')
        self.add_link('main_inputs->train2.in1')
        self.add_link('train1.out1->train2.in2')
        self.add_link('train1.out1->intermediate_output.out_file')
        self.add_link('intermediate_output.base->output_directory')
        self.add_link('subject->intermediate_output.subject')
        self.add_link('train2.out1->output_file.out_file')
        self.add_link('left_out->test.in1')
        self.add_link('train2.out1->test.model')
        self.add_link('test.out1->test_output.out_file')
        self.add_link('test_output.base->output_directory')
        self.add_link('subject->test_output.subject')

        #self.do_not_export = set([('train2', 'out1'),
                                  #('intermediate_output', 'base'),
                                  #('intermediate_output', 'suffix'),
                                  #('intermediate_output', 'out_file')])

        self.node_position = {
            'LOO': (157.165005, 137.83779999999996),
            'inputs': (-58.0, 198.49999999999994),
            'intermediate_output': (380.19948, 19.431299999999965),
            'output_file': (588.66203, 106.0),
            'outputs': (922.7516925, 160.97519999999992),
            'test': (577.7010925, 328.2691),
            'test_output': (700.5415049999999, 242.76909999999995),
            'train1': (277.82609249999996, 152.83779999999996),
            'train2': (429.6447925, 249.58780000000002)}

class PipelineLOO(Pipeline):
    def pipeline_definition(self):
        self.add_iterative_process('train', Pipeline1,
                                   iterative_plugs=['left_out',
                                                    'subject'])
                                   #,
                                                    #'test_output']),
                                   #do_not_export=['test_output'])
        self.export_parameter('train', 'main_inputs')
        self.export_parameter('train', 'subject', 'subjects')
        #self.export_parameter('train', 'test_output', 'test_outputs')
        self.add_link('main_inputs->train.left_out')
        self.pipeline_node.plugs['subjects'].optional = False

        self.node_position = {
            'inputs': (-65.0, 172.0),
            'outputs': (374.0, 194.0),
            'train': (150.0, 150.0)}


class TestCustomNodes(unittest.TestCase):
    def setUp(self):
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            try:
                os.unlink(f)
            except:
                pass
        self.temp_files = []

    def _test_custom_nodes(self, pipeline):
        pipeline.main_inputs = ['/dir/file%d' % i for i in range(4)]
        pipeline.left_out = pipeline.main_inputs[2]
        pipeline.subject = 'subject2'
        pipeline.output_directory = '/dir/out_dir'
        self.assertEqual(pipeline.nodes['train1'].process.out1,
                         os.path.join(pipeline.output_directory,
                                      '%s_interm' % pipeline.subject))
        self.assertEqual(pipeline.nodes['train2'].process.out1,
                         os.path.join(pipeline.output_directory,
                                      pipeline.subject))
        self.assertEqual(pipeline.nodes['test'].process.out1,
                         os.path.join(pipeline.output_directory,
                                      '%s_test_output' % pipeline.subject))
        out_trait_type \
            = pipeline.nodes['test_output'].trait('out_file').trait_type
        self.assertTrue(isinstance(out_trait_type, traits.File))

    def test_custom_nodes(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(Pipeline1)
        self._test_custom_nodes(pipeline)

    def test_custom_nodes_workflow(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(Pipeline1)
        pipeline.main_input = '/dir/file'
        pipeline.output_directory = '/dir/out_dir'
        wf = pipeline_workflow.workflow_from_pipeline(pipeline,
                                                      create_directories=False)
        self.assertEqual(len(wf.jobs), 3)
        self.assertEqual(len(wf.dependencies), 2)
        self.assertEqual(
            sorted([[x.name for x in d] for d in wf.dependencies]),
            sorted([['train1', 'train2'], ['train2', 'test']]))

    def _test_loo_pipeline(self, pipeline2):
        pipeline2.main_inputs = ['/dir/file%d' % i for i in range(4)]
        pipeline2.subjects = ['subject%d' % i for i in range(4)]
        pipeline2.output_directory = '/dir/out_dir'
        wf = pipeline_workflow.workflow_from_pipeline(pipeline2,
                                                      create_directories=False)
        self.assertEqual(len(wf.jobs), 12)
        self.assertEqual(len(wf.dependencies), 8)
        deps = sorted([['train1', 'train2'], ['train2', 'test']] * 4)
        self.assertEqual(
            sorted([[x.name for x in d] for d in wf.dependencies]),
            deps)
        train1_jobs = [job for job in wf.jobs if job.name == 'train1']
        self.assertEqual(
            sorted([job.command[job.command.index('out1') +1]
                    for job in train1_jobs]),
            [os.path.join(pipeline2.output_directory, 'subject%d_interm' % i)
             for i in range(4)])
        train2_jobs = [job for job in wf.jobs if job.name == 'train2']
        self.assertEqual(
            sorted([job.command[job.command.index('out1') +1]
                    for job in train2_jobs]),
            [os.path.join(pipeline2.output_directory, 'subject%d' % i)
             for i in range(4)])
        test_jobs = [job for job in wf.jobs if job.name == 'test']
        self.assertEqual(
            sorted([job.command[job.command.index('out1') +1]
                    for job in test_jobs]),
            [os.path.join(pipeline2.output_directory,
                          'subject%d_test_output' % i)
             for i in range(4)])

    def test_leave_one_out_pipeline(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(PipelineLOO)
        self._test_loo_pipeline(pipeline)

    def test_custom_nodes_py_io(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(Pipeline1)
        py_file = tempfile.mkstemp(suffix='_capsul.py')
        pyfname = py_file[1]
        os.close(py_file[0])
        self.temp_files.append(pyfname)
        python_export.save_py_pipeline(pipeline, pyfname)
        pipeline2 = sc.get_process_instance(pyfname)
        self._test_custom_nodes(pipeline)

    def test_custom_nodes_xml_io(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(Pipeline1)
        xml_file = tempfile.mkstemp(suffix='_capsul.xml')
        xmlfname = xml_file[1]
        os.close(xml_file[0])
        self.temp_files.append(xmlfname)
        xml.save_xml_pipeline(pipeline, xmlfname)
        pipeline2 = sc.get_process_instance(xmlfname)
        self._test_custom_nodes(pipeline2)

    def test_loo_py_io(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(PipelineLOO)
        py_file = tempfile.mkstemp(suffix='_capsul.py')
        pyfname = py_file[1]
        os.close(py_file[0])
        self.temp_files.append(pyfname)
        python_export.save_py_pipeline(pipeline, pyfname)
        pipeline2 = sc.get_process_instance(pyfname)
        self._test_loo_pipeline(pipeline2)

    def test_loo_xml_io(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(PipelineLOO)
        xml_file = tempfile.mkstemp(suffix='_capsul.xml')
        xmlfname = xml_file[1]
        os.close(xml_file[0])
        self.temp_files.append(xmlfname)
        xml.save_xml_pipeline(pipeline, xmlfname)
        pipeline2 = sc.get_process_instance(xmlfname)
        self._test_loo_pipeline(pipeline2)


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCustomNodes)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == '__main__':
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        import sys
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDevelopperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        #pipeline = Pipeline1()
        #pipeline.main_inputs = ['/dir/file%d' % i for i in range(4)]
        #pipeline.left_out = pipeline.main_inputs[2]
        #pipeline.subject = 'subject2'
        #pipeline.output_directory = '/dir/out_dir'
        #view1 = PipelineDevelopperView(pipeline, allow_open_controller=True,
                                       #show_sub_pipelines=True,
                                       #enable_edition=True)
        #view1.show()

        pipeline2 = PipelineLOO()
        pipeline2.main_inputs = ['/dir/file%d' % i for i in range(4)]
        pipeline2.left_out = pipeline2.main_inputs[2]
        pipeline2.subjects = ['subject%d' % i for i in range(4)]
        pipeline2.output_directory = '/dir/out_dir'
        wf = pipeline_workflow.workflow_from_pipeline(pipeline2,
                                                      create_directories=False)
        view2 = PipelineDevelopperView(pipeline2, allow_open_controller=True,
                                       show_sub_pipelines=True,
                                       enable_edition=True)
        view2.show()

        app.exec_()
        #del view1
        del view2


