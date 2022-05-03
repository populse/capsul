# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import unittest
from capsul.api import Process, Pipeline, StudyConfig
from capsul.pipeline import pipeline_workflow
from capsul.pipeline import pipeline_tools
import traits.api as traits
import os
import os.path as osp
import tempfile
import sys
import shutil
import json
from six.moves import range


class TestProcess(Process):
    def __init__(self):
        super(TestProcess, self).__init__()
        self.add_trait('in1', traits.File(output=False))
        self.add_trait('model', traits.File(output=False))
        self.add_trait('out1', traits.File(output=True))

    def _run_process(self):
        print('in1:', self.in1)
        print('out1:', self.out1)
        with open(self.out1, 'w') as f:
            print('test: %s' % os.path.basename(self.out1), file=f)
            print('##############', file=f)
            with open(self.in1, 'r') as ff:
                f.write(ff.read())
            print('model: %s' % os.path.basename(self.model), file=f)
            print('##############', file=f)
            with open(self.model, 'r') as ff:
                f.write(ff.read())
        # TODO FIXME: this should be automatic
        output_dict = {'out1': self.out1}
        return output_dict


class TrainProcess1(Process):
    def __init__(self):
        super(TrainProcess1, self).__init__()
        self.add_trait('in1', traits.List(traits.File(), output=False))
        self.add_trait('out1', traits.File(output=True))

    def _run_process(self):
        with open(self.out1, 'w') as of:
            for fname in self.in1:
                print('train1. File: %s' % os.path.basename(fname), file=of)
                print('--------------------', file=of)
                with open(fname) as f:
                    of.write(f.read())


class TrainProcess2(Process):
    def __init__(self):
        super(TrainProcess2, self).__init__()
        self.add_trait('in1', traits.List(traits.File(), output=False))
        self.add_trait('in2', traits.File(output=False))
        self.add_trait('out1', traits.File(output=True))

    def _run_process(self):
        with open(self.out1, 'w') as of:
            for fname in self.in1:
                print('train2, in1. File: %s' % os.path.basename(fname),
                      file=of)
                print('===================', file=of)
                with open(fname) as f:
                    of.write(f.read())
            print('train2, in2. File: %s' % os.path.basename(fname), file=of)
            print('====================', file=of)
            with open(self.in2) as f:
                of.write(f.read())

class CatFileProcess(Process):
    def __init__(self):
        super(CatFileProcess, self).__init__()
        self.add_trait('files', traits.List(traits.File(), output=False))
        self.add_trait('output', traits.File(output=True))

    def _run_process(self):
        with open(self.output, 'w') as of:
            for fname in self.files:
                with open(fname) as f:
                    of.write(f.read())

class Pipeline1(Pipeline):
    def pipeline_definition(self):
        self.add_process('train1', TrainProcess1())
        self.add_process('train2', TrainProcess2())

        self.add_custom_node('LOO',
                             'capsul.pipeline.custom_nodes.loo_node',
                             parameters={'test_is_output': False,
                                         'has_index': False})
        self.nodes['LOO'].activation_mode = 'by test'
        self.add_custom_node(
            'output_file',
            'capsul.pipeline.custom_nodes.strcat_node.StrCatNode',
            parameters={'parameters': ['base', 'separator', 'subject'],
                        'concat_plug': 'out_file',
                        'param_types': ['Directory', 'Str',
                                        'Str'],
                        'outputs': ['base'],
            },
            make_optional=['subject', 'separator'])
        self.nodes['output_file'].subject = 'output_file'
        self.nodes['output_file'].separator = os.path.sep

        self.add_custom_node(
            'intermediate_output',
            'capsul.pipeline.custom_nodes.strcat_node.StrCatNode',
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

        self.add_custom_node(
            'test_output',
            'capsul.pipeline.custom_nodes.strcat_node.StrCatNode',
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
        self.export_parameter('LOO', 'test', 'test')
        self.export_parameter('output_file', 'base', 'output_directory')
        self.export_parameter('output_file', 'subject')
        self.export_parameter('test', 'out1', 'test_output', is_optional=True)
        # test_output will be assigned internally by the cat node 'test_output'
        # thus should not be a temporary
        self.trait('test_output').input_filename = False
        self.add_link('LOO.train->train1.in1')
        self.add_link('main_inputs->train2.in1')
        self.add_link('train1.out1->train2.in2')
        self.add_link('train1.out1->intermediate_output.out_file')
        self.add_link('intermediate_output.base->output_directory')
        self.add_link('subject->intermediate_output.subject')
        self.add_link('train2.out1->output_file.out_file')
        self.add_link('test->test.in1')
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
        self.add_iterative_process(
            'train', 'capsul.pipeline.test.test_custom_nodes.Pipeline1',
            iterative_plugs=['test',
                            'subject',
                            'test_output'])
            #do_not_export=['test_output'])
        self.add_process(
            'global_output',
            'capsul.pipeline.test.test_custom_nodes.CatFileProcess')
        self.export_parameter('train', 'main_inputs')
        self.export_parameter('train', 'subject', 'subjects')
        self.export_parameter('train', 'output_directory')
        #self.export_parameter('train', 'test_output')
        self.export_parameter('global_output', 'output', 'test_output')
        self.add_link('main_inputs->train.test')
        self.add_link('train.test_output->global_output.files')
        self.pipeline_node.plugs['subjects'].optional = False

        self.node_position = {
            'global_output': (416.6660345018389, 82.62713792979389),
            'inputs': (-56.46187758535915, 33.76663793099311),
            'outputs': (567.2173021071882, 10.355615517551513),
            'train': (139.93023967435616, 5.012399999999985)}

class CVtest(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("test", "capsul.pipeline.test.test_custom_nodes.TestProcess")
        self.nodes["test"].process.out1 = u'%s_test_output' % os.path.sep
        self.add_custom_node("test_output", "capsul.pipeline.custom_nodes.strcat_node.StrCatNode", {'concat_plug': u'out_file', 'outputs': [u'base'], 'param_types': ['Str', 'Str', 'Str', 'Str', 'Any'], 'parameters': [u'base', u'sep', u'subject', u'suffix']})
        self.nodes["test_output"].plugs["sep"].optional = True
        self.nodes["test_output"].plugs["suffix"].optional = True
        self.nodes["test_output"].sep = os.path.sep
        self.nodes["test_output"].suffix = u'_test_output'

        # links
        self.export_parameter("test", "in1")
        self.export_parameter("test", "model")
        self.export_parameter("test_output", "subject")
        self.export_parameter("test", "out1")
        self.trait('out1').input_filename = False  # don't force from outside
        self.add_link("test.out1->test_output.out_file")
        self.export_parameter("test_output", "base")

        # default and initial values
        self.out1 = u'%s_test_output' % os.path.sep

        # nodes positions
        self.node_position = {
            "test": (-65.0, -52.0),
            "inputs": (-250.109375, -12.0),
            "test_output": (108.0, -57.0),
            "outputs": (296.453125, -57.0),
        }

        # nodes dimensions
        self.node_dimension = {
            "test": (104.390625, 110.0),
            "inputs": (113.265625, 145.0),
            "test_output": (113.265625, 180.0),
            "outputs": (113.265625, 110.0),
        }

        self.do_autoexport_nodes_parameters = False


class PipelineCVFold(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("train1", "capsul.pipeline.test.test_custom_nodes.TrainProcess1")
        self.nodes["train1"].process.out1 = u'%s_interm' % os.path.sep
        self.add_process("train2", "capsul.pipeline.test.test_custom_nodes.TrainProcess2")
        self.nodes["train2"].process.in2 = u'%s_interm' % os.path.sep
        self.nodes["train2"].process.out1 = os.path.sep
        self.add_iterative_process("test_it", "capsul.pipeline.test.test_custom_nodes.CVtest", iterative_plugs=set([u'out1', u'in1', u'subject']),
                                   make_optional=['out1'])
        self.add_custom_node("output_file", "capsul.pipeline.custom_nodes.strcat_node.StrCatNode", {'concat_plug': 'out_file', 'outputs': ['base'], 'param_types': ['Directory', 'Str', 'Str', 'Any'], 'parameters': ['base', 'separator', 'subject']})
        self.nodes["output_file"].plugs["separator"].optional = True
        self.nodes["output_file"].plugs["subject"].optional = True
        self.nodes["output_file"].separator = os.path.sep
        self.add_custom_node("intermediate_output", "capsul.pipeline.custom_nodes.strcat_node.StrCatNode", {'concat_plug': 'out_file', 'outputs': ['base'], 'param_types': ['Directory', 'Str', 'Str', 'Str', 'File'], 'parameters': ['base', 'sep', 'subject', 'suffix']})
        self.nodes["intermediate_output"].plugs["sep"].optional = True
        self.nodes["intermediate_output"].plugs["subject"].optional = True
        self.nodes["intermediate_output"].plugs["suffix"].optional = True
        self.nodes["intermediate_output"].sep = os.path.sep
        self.nodes["intermediate_output"].suffix = '_interm'
        self.add_custom_node("CV", "capsul.pipeline.custom_nodes.cv_node.CrossValidationFoldNode", {'param_type': 'File'})
        self.nodes["CV"].plugs["inputs"].optional = True
        self.nodes["CV"].plugs["fold"].optional = True
        self.nodes["CV"].plugs["nfolds"].optional = True
        self.nodes["CV"].plugs["train"].optional = True
        self.nodes["CV"].plugs["test"].optional = True
        self.add_custom_node("CV_subject", "capsul.pipeline.custom_nodes.cv_node.CrossValidationFoldNode", {'param_type': 'Str'})
        self.nodes["CV_subject"].plugs["inputs"].optional = True
        self.nodes["CV_subject"].plugs["fold"].optional = True
        self.nodes["CV_subject"].plugs["nfolds"].optional = True
        self.nodes["CV_subject"].plugs["train"].optional = True
        self.nodes["CV_subject"].plugs["test"].optional = True
        self.add_custom_node("CV_str", "capsul.pipeline.custom_nodes.strconv.StrConvNode", {'param_type': 'Int'})
        self.nodes["CV_str"].plugs["input"].optional = True
        self.nodes["CV_str"].plugs["output"].optional = True

        # links
        self.export_parameter("train2", "in1", "main_inputs")
        self.add_link("main_inputs->CV.inputs")
        self.export_parameter("CV_subject", "fold")
        self.add_link("fold->CV.fold")
        self.add_link("fold->CV_str.input")
        self.export_parameter("CV_subject", "nfolds")
        self.add_link("nfolds->CV.nfolds")
        self.export_parameter("CV_subject", "inputs", "subjects")
        self.add_link("train1.out1->intermediate_output.out_file")
        self.add_link("train1.out1->train2.in2")
        self.add_link("train2.out1->test_it.model")
        self.add_link("train2.out1->output_file.out_file")
        #self.export_parameter("test_it", "out1")
        self.export_parameter("intermediate_output", "base", "output_directory")
        self.add_link("test_it.base->output_directory")
        self.add_link("output_file.base->output_directory")
        self.add_link("intermediate_output.base->output_directory")
        self.add_link("CV.train->train1.in1")
        self.add_link("CV.test->test_it.in1")
        self.add_link("CV_subject.test->test_it.subject")
        self.add_link("CV_str.output->intermediate_output.subject")
        self.add_link("CV_str.output->output_file.subject")

        # nodes positions
        self.node_position = {
            "inputs": (-193.81409672616152, 179.57571591106034),
            "test_output": (773.8854751232217, 301.4076846200484),
            "CV_subject": (124.49272432968576, 300.1841121088647),
            "intermediate_output": (429.7825366016713, 10.297579047060516),
            "outputs": (922.7516925, 160.97519999999992),
            "test_it": (609.4159229330792, 348.80997764736793),
            "LOO": (127.01453333816809, 136.6317811335267),
            "output_file": (592.1421868108927, 89.46925514825949),
            "train1": (277.82609249999996, 152.83779999999996),
            "train2": (429.64479249999994, 241.14566793468708),
            "test": (577.7010925, 333.28052580768554),
            "CV": (87.47511701769065, 24.222253721445696),
            "CV_str": (260.7152514566675, 58.92183893386279),
        }

        # nodes dimensions
        self.node_dimension = {
            "inputs": (226.71875, 215.0),
            "test_output": (113.265625, 180.0),
            "CV_subject": (106.0, 145.0),
            "intermediate_output": (136.640625, 180.0),
            "outputs": (226.71875, 110.0),
            "test_it": (112.265625, 145.0),
            "LOO": (106.0, 110.0),
            "output_file": (128.75, 145.0),
            "train1": (82.828125, 75.0),
            "train2": (82.828125, 110.0),
            "test": (104.390625, 110.0),
            "CV": (106.0, 145.0),
            "CV_str": (112.828125, 75.0),
        }

        self.do_autoexport_nodes_parameters = False


class PipelineCV(Pipeline):
    def pipeline_definition(self):
        self.add_iterative_process(
            'train', 'capsul.pipeline.test.test_custom_nodes.PipelineCVFold',
            iterative_plugs=['fold'])
            #do_not_export=['test_output'])
        self.export_parameter('train', 'main_inputs')
        self.export_parameter('train', 'subjects', 'subjects')
        self.export_parameter('train', 'fold')
        self.export_parameter('train', 'nfolds')
        self.export_parameter('train', 'output_directory')

        self.node_position = {
            'inputs': (-56.46187758535915, 33.76663793099311),
            'outputs': (567.2173021071882, 10.355615517551513),
            'train': (139.93023967435616, 5.012399999999985)}


class PipelineMapReduce(Pipeline):
    def pipeline_definition(self):
        self.add_process(
            'proc1', 'capsul.pipeline.test.test_custom_nodes.Pipeline1')
        self.add_process(
            'proc2', 'capsul.pipeline.test.test_custom_nodes.Pipeline1')
        self.add_custom_node(
            'map', 'capsul.pipeline.custom_nodes.map_node',
            parameters={'input_names': ['map_input', 'subjects'],
                        'output_names': ['test_%d', 'subject_%d'],
                        'input_types': ['File', 'Str']})
        # extract inputs list len as a list of 1 item
        # [2, 2] -> 2, 2
        self.add_custom_node(
            'input_len1', 'capsul.pipeline.custom_nodes.map_node',
            parameters={'input_types': ['Int']})
        # 2 -> [2]
        self.add_custom_node(
            'input_len2', 'capsul.pipeline.custom_nodes.reduce_node',
            parameters={'input_types': ['Int']},
            make_optional=['lengths'], do_not_export=['skip_empty'])
        # real reduce
        self.add_custom_node(
            'reduce', 'capsul.pipeline.custom_nodes.reduce_node',
            parameters={'input_names': ['in_output_%d'],
                        'input_types': ['File']}, do_not_export=['skip_empty'])
        self.add_process(
            'cat', 'capsul.pipeline.test.test_custom_nodes.CatFileProcess')
        self.export_parameter('proc1', 'main_inputs', 'main_inputs')
        self.export_parameter('map', 'subjects')
        self.export_parameter('proc1', 'output_directory')
        #self.export_parameter('proc1', 'test_output', 'test_output1')
        #self.export_parameter('proc2', 'test_output', 'test_output2')
        self.export_parameter('cat', 'output', 'output_file')
        self.add_link('main_inputs->map.map_input')
        self.add_link('main_inputs->proc2.main_inputs')
        self.add_link('proc2.output_directory->output_directory')
        self.main_inputs = ['file1', 'file2']
        self.subjects = ['subject1', 'subject2']
        self.add_link('map.test_0->proc1.test')
        self.add_link('map.test_1->proc2.test')
        self.add_link('map.subject_0->proc1.subject')
        self.add_link('map.subject_1->proc2.subject')
        self.add_link('map.lengths->input_len1.inputs')
        self.add_link('input_len1.output_0->input_len2.input_0')
        self.add_link('input_len2.outputs->reduce.lengths')
        self.add_link('proc1.test_output->reduce.in_output_0')
        self.add_link('proc2.test_output->reduce.in_output_1')
        self.add_link('reduce.outputs->cat.files')

        self.node_position = {
            'inputs': (-56.46187758535915, 33.76663793099311),
            'outputs': (567.2173021071882, 10.355615517551513),
            'proc1': (139.93023967435616, 5.012399999999985)}


class TestCustomNodes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='swf_custom')
        self.temp_files = [self.temp_dir]
        os.mkdir(os.path.join(self.temp_dir, 'out_dir'))
        lines = [
            ['water', 'snow', 'vapor', 'ice'],
            ['stone', 'mud', 'earth'],
            ['wind', 'storm', 'air'],
            ['fire', 'flame'],
        ]
        for i in range(4):
            fline = lines.pop(0)
            with open(os.path.join(self.temp_dir, 'file%d' % i), 'w') as f:
                f.write('file%d:\n++++++\n' % i)
                for l, line in enumerate(fline):
                    f.write('line%d: %s\n' % (l, line))

    def tearDown(self):
        if '--keep-temp' not in sys.argv[1:]:
            for f in self.temp_files:
                if os.path.isdir(f):
                    try:
                        shutil.rmtree(f)
                    except OSError:
                        pass
                else:
                    try:
                        os.unlink(f)
                    except OSError:
                        pass
            self.temp_files = []
        else:
            print('Files not removed in %s' % self.temp_dir)

    def add_py_tmpfile(self, pyfname):
        '''
        add the given .py file and the associated .pyc file to the list of temp
        files to remove after testing
        '''
        self.temp_files.append(pyfname)
        if sys.version_info[0] < 3:
            self.temp_files.append(pyfname + 'c')
        else:
            cache_dir = osp.join(osp.dirname(pyfname), '__pycache__')
            # print('cache_dir:', cache_dir)
            cpver = 'cpython-%d%d.pyc' % sys.version_info[:2]
            pyfname_we = osp.basename(pyfname[:pyfname.rfind('.')])
            pycfname = osp.join(cache_dir, '%s.%s' % (pyfname_we, cpver))
            self.temp_files.append(pycfname)
            # print('added py tmpfile:', pyfname, pycfname)

    def _test_custom_nodes(self, pipeline):
        pipeline.main_inputs = [os.path.join(self.temp_dir, 'file%d' % i)
                                for i in range(4)]
        pipeline.test = pipeline.main_inputs[2]
        pipeline.subject = 'subject2'
        pipeline.output_directory = os.path.join(self.temp_dir, 'out_dir')
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
        pipeline.main_input = os.path.join(self.temp_dir, 'file')
        pipeline.output_directory = os.path.join(self.temp_dir, 'out_dir')
        wf = pipeline_workflow.workflow_from_pipeline(pipeline,
                                                      create_directories=False)
        self.assertEqual(len(wf.jobs), 7)
        self.assertEqual(len(wf.dependencies), 6)
        self.assertEqual(
            sorted([[x.name for x in d] for d in wf.dependencies]),
            sorted([['LOO', 'train1'], ['train1', 'train2'],
                    ['train1', 'intermediate_output'], ['train2', 'test'],
                    ['train2', 'output_file'], ['test', 'test_output']]))

    def _test_loo_pipeline(self, pipeline2):
        pipeline2.main_inputs = [os.path.join(self.temp_dir, 'file%d' % i)
                                 for i in range(4)]
        pipeline2.subjects = ['subject%d' % i for i in range(4)]
        pipeline2.output_directory = os.path.join(self.temp_dir, 'out_dir')
        pipeline2.test_output = os.path.join(self.temp_dir, 'out_dir',
                                             'outputs')
        wf = pipeline_workflow.workflow_from_pipeline(pipeline2,
                                                      create_directories=False)
        import soma_workflow.client as swc
        swc.Helper.serialize(os.path.join(self.temp_dir,
                                          'custom_nodes.workflow'), wf)
        import six
        #print('workflow:')
        #print('jobs:', wf.jobs)
        #print('dependencies:', sorted([(x[0].name, x[1].name) for x in wf.dependencies]))
        #print('dependencies:', wf.dependencies)
        #print('links:', {n.name: {p: (l[0].name, l[1]) for p, l in six.iteritems(links)} for n, links in six.iteritems(wf.param_links)})
        self.assertEqual(len(wf.jobs), 31)
        self.assertEqual(len(wf.dependencies), 16*4 + 1)
        deps = sorted([['Pipeline1_map', 'LOO'],
                       ['Pipeline1_map', 'intermediate_output'],
                       ['Pipeline1_map', 'train2'],
                       ['Pipeline1_map', 'output_file'],
                       ['Pipeline1_map', 'test'],
                       ['Pipeline1_map', 'test_output'],
                       ['LOO', 'train1'],
                       ['train1', 'train2'], ['train1', 'intermediate_output'],
                       ['train2', 'test'], ['train2', 'output_file'],
                       ['test', 'test_output'],
                       ['intermediate_output', 'Pipeline1_reduce'],
                       ['output_file', 'Pipeline1_reduce'],
                       ['test_output', 'Pipeline1_reduce'],
                       ['test', 'Pipeline1_reduce']] * 4
                      + [['Pipeline1_reduce', 'global_output']])
        self.assertEqual(
            sorted([[x.name for x in d] for d in wf.dependencies]),
            deps)
        train1_jobs = [job for job in wf.jobs if job.name == 'train1']
        self.assertEqual(
            sorted([job.param_dict['out1'] for job in train1_jobs]),
            [os.path.join(pipeline2.output_directory, 'subject%d_interm' % i)
             for i in range(4)])
        train2_jobs = [job for job in wf.jobs if job.name == 'train2']
        self.assertEqual(
            sorted([job.param_dict['out1'] for job in train2_jobs]),
            [os.path.join(pipeline2.output_directory, 'subject%d' % i)
             for i in range(4)])
        test_jobs = [job for job in wf.jobs if job.name == 'test']
        self.assertEqual(len(test_jobs), 4)
        test_outputs = [job for job in wf.jobs if job.name == 'test_output']
        #print('test_output jobs:', test_outputs)
        #for j in test_outputs:
            #print('param_dict:', j.param_dict)
        out = sorted([job.param_dict['out_file'] for job in test_outputs])
        self.assertEqual(
            sorted([job.param_dict['out_file'] for job in test_outputs]),
            [os.path.join(pipeline2.output_directory,
                          'subject%d_test_output' % i)
             for i in range(4)])

    def _test_cv_pipeline(self, pipeline):
        pipeline.main_inputs = [os.path.join(self.temp_dir, 'file%d' % i)
                                for i in range(4)]
        pipeline.nfolds = 4
        pipeline.subjects = ['subject%d' % i for i in range(4)]
        pipeline.output_directory = os.path.join(self.temp_dir, 'out_dir')
        pipeline.fold = list(range(pipeline.nfolds))
        wf = pipeline_workflow.workflow_from_pipeline(pipeline,
                                                      create_directories=False)
        import soma_workflow.client as swc
        swc.Helper.serialize(os.path.join(self.temp_dir,
                                          'custom_nodes.workflow'), wf)
        import six
        #print('workflow:')
        #print('jobs:', wf.jobs)
        #print('n deps:', len(wf.dependencies))
        #print('dependencies:', sorted([(x[0].name, x[1].name) for x in wf.dependencies]))
        #print('links:', {n.name: {p: (l[0].name, l[1]) for p, l in six.iteritems(links)} for n, links in six.iteritems(wf.param_links)})
        self.assertEqual(len(wf.jobs), 42)
        self.assertEqual(len(wf.dependencies), 76)
        deps = sorted([
                       ['CV', 'CVtest_map'],
                       ['CV', 'train1'],
                       ['CV_subject', 'CVtest_map'],
                       ['CVtest_map', 'test'],
                       ['CVtest_map', 'test_output'],
                       #['CVtest_reduce', 'PipelineCVFold_reduce'],
                       ['PipelineCVFold_map', 'CV'],
                       ['PipelineCVFold_map', 'CV_subject'],
                       ['PipelineCVFold_map', 'intermediate_output'],
                       ['PipelineCVFold_map', 'output_file'],
                       ['PipelineCVFold_map', 'train2'],
                       ['intermediate_output', 'PipelineCVFold_reduce'],
                       ['output_file', 'PipelineCVFold_reduce'],
                       ['test', 'CVtest_reduce'],
                       ['test', 'test_output'],
                       ['test_output', 'CVtest_reduce'],
                       ['train1', 'intermediate_output'],
                       ['train1', 'train2'],
                       ['train2', 'CVtest_map'],
                       ['train2', 'output_file'],
                       ] * 4)
        self.assertEqual(
            sorted([[x.name for x in d] for d in wf.dependencies]),
            deps)
        train1_jobs = [job for job in wf.jobs if job.name == 'train1']
        self.assertEqual(
            sorted([job.param_dict['out1'] for job in train1_jobs]),
            [os.path.join(pipeline.output_directory, '%d_interm' % i)
             for i in range(4)])
        train2_jobs = [job for job in wf.jobs if job.name == 'train2']
        self.assertEqual(
            sorted([job.param_dict['out1'] for job in train2_jobs]),
            [os.path.join(pipeline.output_directory, '%d' % i)
             for i in range(4)])
        test_jobs = [job for job in wf.jobs if job.name == 'test']
        self.assertEqual(len(test_jobs), 4)
        test_outputs = [job for job in wf.jobs if job.name == 'test_output']
        #print('test_output jobs:', test_outputs)
        #for j in test_outputs:
            #print('param_dict:', j.param_dict)
        out = sorted([job.param_dict['out_file'] for job in test_outputs])
        self.assertEqual(
            sorted([job.param_dict['out_file'] for job in test_outputs]),
            [os.path.join(pipeline.output_directory,
                          'subject%d_test_output' % i)
             for i in range(4)])

    def test_leave_one_out_pipeline(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(PipelineLOO)
        self._test_loo_pipeline(pipeline)

    def _test_custom_io(self, pipeline, test_func, format):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(pipeline)
        py_file = tempfile.mkstemp(suffix='_capsul.%s' % format)
        pyfname = py_file[1]
        os.close(py_file[0])
        if format == 'py':
            self.add_py_tmpfile(pyfname)
        else:
            self.temp_files.append(pyfname)
        pipeline_tools.save_pipeline(pipeline, pyfname, format=format)
        pipeline2 = sc.get_process_instance(pyfname)
        test_func(pipeline2)

    def _test_custom_nodes_io(self, format):
        self._test_custom_io(Pipeline1, self._test_custom_nodes, format)

    def test_custom_nodes_py_io(self):
        self._test_custom_nodes_io('py')

    def test_custom_nodes_xml_io(self):
        self._test_custom_nodes_io('xml')

    def test_custom_nodes_json_io(self):
        self._test_custom_nodes_io('json')

    def test_loo_py_io(self):
        self._test_custom_io(PipelineLOO, self._test_loo_pipeline, 'py')

    def test_loo_xml_io(self):
        self._test_custom_io(PipelineLOO, self._test_loo_pipeline, 'xml')

    def test_loo_json_io(self):
        self._test_custom_io(PipelineLOO, self._test_loo_pipeline, 'json')

    def test_mapreduce(self):
        sc = StudyConfig()
        pipeline = sc.get_process_instance(PipelineMapReduce)
        pipeline.main_inputs = [os.path.join(self.temp_dir, 'file%d' % i)
                                for i in range(4)]
        pipeline.subjects = ['Robert', 'Gustave']
        pipeline.output_directory = os.path.join(self.temp_dir, 'out_dir')
        self.assertEqual(
            pipeline.nodes['cat'].process.files,
            [os.path.join(pipeline.output_directory,
                          '%s_test_output' % pipeline.subjects[0]),
            os.path.join(pipeline.output_directory,
                          '%s_test_output' % pipeline.subjects[1])])
        wf = pipeline_workflow.workflow_from_pipeline(pipeline,
                                                      create_directories=False)
        self.assertEqual(len(wf.jobs), 19)
        #print(sorted([(d[0].name, d[1].name) for d in wf.dependencies]))
        self.assertEqual(len(wf.dependencies), 28)

    def test_cv_py_io(self):
        self._test_custom_io(PipelineCV, self._test_cv_pipeline, 'py')

    def test_cv_xml_io(self):
        self._test_custom_io(PipelineCV, self._test_cv_pipeline, 'xml')

    def test_cv_json_io(self):
        self._test_custom_io(PipelineCV, self._test_cv_pipeline, 'json')


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCustomNodes)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == '__main__':
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        import sys
        from soma.qt_gui.qt_backend import QtGui
        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication.instance()
        if not app:
            app = QtGui.QApplication(sys.argv)
        #pipeline = Pipeline1()
        #pipeline.main_inputs = [os.path.join(self.temp_dir, 'file%d' % i
        #for i in range(4)])
        #pipeline.test = pipeline.main_inputs[2]
        #pipeline.subject = 'subject2'
        #pipeline.output_directory = os.path.join(self.temp_dir, 'out_dir')
        #view1 = PipelineDeveloperView(pipeline, allow_open_controller=True,
                                       #show_sub_pipelines=True,
                                       #enable_edition=True)
        #view1.show()

        pipeline2 = PipelineLOO()
        pipeline2.main_inputs = ['/tmp/file%d' % i for i in range(4)]
        pipeline2.test = pipeline2.main_inputs[2]
        pipeline2.subjects = ['subject%d' % i for i in range(4)]
        pipeline2.output_directory = '/tmp/out_dir'
        pipeline2.nfolds = 4
        pipeline2.fold = list(range(pipeline2.nfolds))
        #wf = pipeline_workflow.workflow_from_pipeline(pipeline2,
                                                      #create_directories=False)
        view2 = PipelineDeveloperView(pipeline2, allow_open_controller=True,
                                       show_sub_pipelines=True,
                                       enable_edition=True)
        view2.show()

        app.exec_()
        #del view1
        del view2
