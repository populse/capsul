# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

from capsul.api import StudyConfig, Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine
from capsul.attributes.fom_completion_engine \
    import FomProcessCompletionEngine, FomPathCompletionEngine
from traits.api import Str, Float, File, String, Undefined, List
from soma_workflow import configuration as swconfig
import unittest
import os
import sys
import tempfile
import shutil
import socket
import json
from six.moves import zip


def init_study_config(init_config={}):
    study_config = StudyConfig('test_study',
                               modules=['FomConfig',
                                        'SomaWorkflowConfig'],
                               init_config=init_config)
    study_config.input_directory = '/tmp/in'
    study_config.output_directory = '/tmp/out'
    study_config.attributes_schema_paths.append(
        'capsul.attributes.test.test_attributed_process')

    return study_config


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


class TestCompletion(unittest.TestCase):

    def setUp(self):
        if not hasattr(self, 'temps'):
            self.temps = []
        tmp_fom = tempfile.mkdtemp(prefix='capsul_fom')
        self.temps.append(tmp_fom)

        # write FOM file
        fom = {
            "fom_name": "custom_fom_test-1.0",

            "formats": {
                "text file": "txt"
            },

            "attribute_definitions" : {
              "group" : {"default_value" : "default_group"},
              "processing" : {"default_value" : "default_processing"},
            },

            "shared_patterns": {
              "acquisition": "<center>_<subject>",
            },

            "processes" : {
                "DummyProcess" : {
                    "truc": [["input:DummyProcess_truc_{acquisition}",
                              "text file",]],
                    "bidule": [["output:DummyProcess_bidule_{acquisition}",
                                "text file",]],
                },
                "DummyListProcess" : {
                    "truc": [["input:DummyListProcess_truc_{acquisition}",
                              "text file",]],
                    "bidule": [["input:DummyListProcess_bidule_{acquisition}",
                                "text file",]],
                    "result": [["output:DummyListProcess_result_<group>",
                                "text file"]],
                },
            }
        }
        
        with open(os.path.join(tmp_fom, 'custom_fom.json'), 'w') as f:
            json.dump(fom, f)


        self.study_config = init_study_config()
        self.study_config.fom_path = [tmp_fom]
        self.study_config.input_fom = 'custom_fom_test-1.0'
        self.study_config.output_fom = 'custom_fom_test-1.0'


    def tearDown(self):
        swm = self.study_config.modules['SomaWorkflowConfig']
        swc = swm.get_workflow_controller()
        if swc is not None:
            # stop workflow controller and wait for thread termination
            swc.stop_engine()
        if hasattr(self, 'temps'):
            for tdir in self.temps:
                try:
                    shutil.rmtree(tdir)
                except Exception as e:
                    print(e)
                    raise
            self.temps = []


    def test_completion(self):
        study_config = self.study_config
        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyProcess')
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values()
        self.assertTrue(isinstance(patt, FomProcessCompletionEngine))
        self.assertTrue(isinstance(
            patt.get_path_completion_engine(),
            FomPathCompletionEngine))
        atts.center = 'jojo'
        atts.subject = 'barbapapa'
        patt.complete_parameters()
        self.assertEqual(os.path.normpath(process.truc),
                         os.path.normpath('/tmp/in/DummyProcess_truc_jojo_barbapapa.txt'))
        self.assertEqual(os.path.normpath(process.bidule),
                         os.path.normpath('/tmp/out/DummyProcess_bidule_jojo_barbapapa.txt'))


    def test_iteration(self):
        study_config = self.study_config
        pipeline = study_config.get_iteration_pipeline(
            'iter',
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        cm = ProcessCompletionEngine.get_completion_engine(pipeline)
        atts = cm.get_attribute_values()
        atts.center = ['muppets']
        atts.subject = ['kermit', 'piggy', 'stalter', 'waldorf']
        cm.complete_parameters()
        self.assertEqual([os.path.normpath(p) for p in pipeline.truc],
                         [os.path.normpath(p) for p in
                            ['/tmp/in/DummyProcess_truc_muppets_kermit.txt',
                             '/tmp/in/DummyProcess_truc_muppets_piggy.txt',
                             '/tmp/in/DummyProcess_truc_muppets_stalter.txt',
                             '/tmp/in/DummyProcess_truc_muppets_waldorf.txt']])
        self.assertEqual(
            [os.path.normpath(p) for p in pipeline.bidule],
            [os.path.normpath(p) for p in
              ['/tmp/out/DummyProcess_bidule_muppets_kermit.txt',
                '/tmp/out/DummyProcess_bidule_muppets_piggy.txt',
                '/tmp/out/DummyProcess_bidule_muppets_stalter.txt',
                '/tmp/out/DummyProcess_bidule_muppets_waldorf.txt']])

    def test_list_completion(self):
        study_config = self.study_config
        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyListProcess')
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values()
        atts.center = ['jojo', 'koko']
        atts.subject = ['barbapapa', 'barbatruc']
        atts.group = 'cartoon'
        patt.complete_parameters()
        self.assertEqual(
            [os.path.normpath(p) for p in process.truc],
            [os.path.normpath(p) for p in
              ['/tmp/in/DummyListProcess_truc_jojo_barbapapa.txt',
                '/tmp/in/DummyListProcess_truc_koko_barbatruc.txt',]])
        self.assertEqual(
            [os.path.normpath(p) for p in process.bidule],
            [os.path.normpath(p) for p in
              ['/tmp/in/DummyListProcess_bidule_jojo_barbapapa.txt',
                '/tmp/in/DummyListProcess_bidule_koko_barbatruc.txt']]
        )
        self.assertEqual(os.path.normpath(process.result),
                         os.path.normpath(
                            '/tmp/out/DummyListProcess_result_cartoon.txt'))


    def test_run_iteraton_sequential(self):
        study_config = self.study_config
        tmp_dir = tempfile.mkdtemp(prefix='capsul_')
        self.temps.append(tmp_dir)

        study_config.input_directory = os.path.join(tmp_dir, 'in')
        study_config.output_directory = os.path.join(tmp_dir, 'out')
        os.mkdir(study_config.input_directory)
        os.mkdir(study_config.output_directory)

        pipeline = study_config.get_iteration_pipeline(
            'iter',
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        cm = ProcessCompletionEngine.get_completion_engine(pipeline)
        atts = cm.get_attribute_values()
        atts.center = ['muppets']
        atts.subject = ['kermit', 'piggy', 'stalter', 'waldorf']
        cm.complete_parameters()

        # create input files
        for s in atts.subject:
            with open(os.path.join(
                    study_config.input_directory,
                    'DummyProcess_truc_muppets_%s.txt' % s), 'w') as f:
                f.write('%s\n' %s)

        # run
        study_config.use_soma_workflow = False
        study_config.run(pipeline)

        # check outputs
        out_files = [
            os.path.join(
                study_config.output_directory,
                'DummyProcess_bidule_muppets_%s.txt' % s)
            for s in atts.subject]
        for s, out_file in zip(atts.subject, out_files):
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file) as f:
                self.assertTrue(f.read() == '%s\n' % s)


    def test_run_iteraton_swf(self):
        study_config = self.study_config
        tmp_dir = tempfile.mkdtemp(prefix='capsul_')
        self.temps.append(tmp_dir)

        study_config.input_directory = os.path.join(tmp_dir, 'in')
        study_config.output_directory = os.path.join(tmp_dir, 'out')
        os.mkdir(study_config.input_directory)
        os.mkdir(study_config.output_directory)

        pipeline = study_config.get_iteration_pipeline(
            'iter',
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        cm = ProcessCompletionEngine.get_completion_engine(pipeline)
        atts = cm.get_attribute_values()
        atts.center = ['muppets']
        atts.subject = ['kermit', 'piggy', 'stalter', 'waldorf']
        cm.complete_parameters()

        # create input files
        for s in atts.subject:
            with open(os.path.join(
                    study_config.input_directory,
                    'DummyProcess_truc_muppets_%s.txt' % s), 'w') as f:
                f.write('%s\n' %s)

        # run
        study_config.use_soma_workflow = True
        study_config.run(pipeline)

        # check outputs
        out_files = [
            os.path.join(
                study_config.output_directory,
                'DummyProcess_bidule_muppets_%s.txt' % s)
            for s in atts.subject]
        for s, out_file in zip(atts.subject, out_files):
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file) as f:
                self.assertTrue(f.read() == '%s\n' % s)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCompletion)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == '__main__':
    print("RETURNCODE: ", test())

    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:

        from capsul.qt_gui.widgets.pipeline_developper_view \
            import PipelineDeveloperView
        from capsul.qt_gui.widgets.attributed_process_widget \
            import AttributedProcessWidget
        from soma.qt_gui.qt_backend import QtGui, QtCore

        study_config = init_study_config()

        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyProcess')
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values()

        qapp = None
        if QtGui.QApplication.instance() is None:
            qapp = QtGui.QApplication(['test_app'])
        pv = PipelineDeveloperView(process, allow_open_controller=True,
                                    enable_edition=True,
                                    show_sub_pipelines=True)
        pc = AttributedProcessWidget(process, enable_attr_from_filename=True,
                                    enable_load_buttons=True)

        pv.show()
        pc.show()
        if qapp:
            qapp.exec_()
