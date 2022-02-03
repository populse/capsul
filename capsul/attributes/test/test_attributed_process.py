# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

from capsul.api import StudyConfig, Process, Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    PathCompletionEngine, PathCompletionEngineFactory
from capsul.attributes.attributes_schema import ProcessAttributes, \
    AttributesSchema, EditableAttributes
from traits.api import Str, Float, File, String, Undefined, List
from soma_workflow import configuration as swconfig
import unittest
import os
import sys
import tempfile
import shutil
import socket
from six.moves import zip


class DummyProcess(Process):
    f = Float(output=False)

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("truc", File(output=False))
        self.add_trait("bidule", File(output=True))

    def _run_process(self):
        with open(self.bidule, 'w') as f:
            with open(self.truc) as g:
                f.write(g.read())


class DummyListProcess(Process):
    truc = List(File(output=False))
    bidule = List(File(output=False))
    result = File(output=True)

    def _run_process(self):
        with open(self.result, 'w') as f:
            f.write(
                '{\n    truc=%s,\n    bidule=%s\n}' % (self.truc, self.bidule))


class CustomAttributesSchema(AttributesSchema):
    factory_id = 'custom_ex'

    class Acquisition(EditableAttributes):
        center = String()
        subject = String()

    class Group(EditableAttributes):
        group = String()

    class Processing(EditableAttributes):
        analysis = String()


class DummyProcessAttributes(ProcessAttributes):
    factory_id = 'DummyProcess'

    def __init__(self, process, schema_dict):
        super(DummyProcessAttributes, self).__init__(process, schema_dict)
        self.set_parameter_attributes('truc', 'input', 'Acquisition', {})
        self.set_parameter_attributes('bidule', 'output', 'Acquisition', {})


class DummyListProcessAttributes(ProcessAttributes):
    factory_id = 'DummyListProcess'

    def __init__(self, process, schema_dict):
        super(DummyListProcessAttributes, self).__init__(process, schema_dict)
        self.set_parameter_attributes('truc', 'input', 'Acquisition', {})
        self.set_parameter_attributes('bidule', 'input', 'Acquisition', {})
        self.set_parameter_attributes('result', 'output', 'Group', {})


class MyPathCompletion(PathCompletionEngineFactory, PathCompletionEngine):
    factory_id = 'custom_ex'

    def __init__(self):
        super(MyPathCompletion, self).__init__()

    def get_path_completion_engine(self, process):
        return self

    def attributes_to_path(self, process, parameter, attributes):
        study_config = process.get_study_config()
        att_dict = attributes.get_parameters_attributes()[parameter]
        elements = [process.name, parameter]
        # get attributes sorted by user_traits
        for key in attributes.user_traits().keys():
            val = att_dict.get(key)
            if val and val is not Undefined:
                elements.append(str(val))
        if 'generated_by_parameter' in att_dict:
            directory = study_config.output_directory
        else:
            directory = study_config.input_directory
        return os.path.join(directory, '_'.join(elements))


def init_study_config(init_config={}):
    study_config = StudyConfig('test_study',
                               modules=['AttributesConfig',
                                        'SomaWorkflowConfig'],
                               init_config=init_config)
    study_config.input_directory = '/tmp/in'
    study_config.output_directory = '/tmp/out'
    study_config.attributes_schema_paths \
        = study_config.attributes_schema_paths \
            + ['capsul.attributes.test.test_attributed_process']
    study_config.attributes_schemas['input'] = 'custom_ex'
    study_config.attributes_schemas['output'] = 'custom_ex'
    #print('attributes_schema_paths:', study_config.attributes_schema_paths)
    study_config.path_completion = 'custom_ex'
    #print('attributes_schema_paths 2:', study_config.attributes_schema_paths)

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
        self.study_config = init_study_config()
        if not hasattr(self, 'temps'):
            self.temps = []


    def tearDown(self):
        swm = self.study_config.modules['SomaWorkflowConfig']
        swc = swm.get_workflow_controller()
        if swc is not None:
            # stop workflow controller and wait for thread termination
            swc.stop_engine()


    def __del__(self):
        if hasattr(self, 'temps'):
            for tdir in self.temps:
                shutil.rmtree(tdir)


    def test_completion(self):
        study_config = self.study_config
        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyProcess')
        from capsul.attributes.test.test_attributed_process \
            import DummyProcessAttributes, MyPathCompletion
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values()
        self.assertTrue(isinstance(patt, ProcessCompletionEngine))
        self.assertTrue(isinstance(atts, DummyProcessAttributes))
        self.assertTrue(isinstance(
            patt.get_path_completion_engine(),
            MyPathCompletion))
        atts.center = 'jojo'
        atts.subject = 'barbapapa'
        patt.complete_parameters()
        self.assertEqual(os.path.normpath(process.truc),
                         os.path.normpath('/tmp/in/DummyProcess_truc_jojo_barbapapa'))
        self.assertEqual(os.path.normpath(process.bidule),
                         os.path.normpath('/tmp/out/DummyProcess_bidule_jojo_barbapapa'))


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
                            ['/tmp/in/DummyProcess_truc_muppets_kermit',
                             '/tmp/in/DummyProcess_truc_muppets_piggy',
                             '/tmp/in/DummyProcess_truc_muppets_stalter',
                             '/tmp/in/DummyProcess_truc_muppets_waldorf']])
        self.assertEqual([os.path.normpath(p) for p in pipeline.bidule],
                         [os.path.normpath(p) for p in 
                            ['/tmp/out/DummyProcess_bidule_muppets_kermit',
                             '/tmp/out/DummyProcess_bidule_muppets_piggy',
                             '/tmp/out/DummyProcess_bidule_muppets_stalter',
                             '/tmp/out/DummyProcess_bidule_muppets_waldorf']])

    def test_list_completion(self):
        study_config = self.study_config
        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyListProcess')
        from capsul.attributes.test.test_attributed_process \
            import DummyListProcessAttributes, MyPathCompletion
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values()
        self.assertTrue(isinstance(patt, ProcessCompletionEngine))
        self.assertTrue(isinstance(atts, DummyListProcessAttributes))
        self.assertTrue(isinstance(
            patt.get_path_completion_engine(),
            MyPathCompletion))
        atts.center = ['jojo', 'koko']
        atts.subject = ['barbapapa', 'barbatruc']
        atts.group = 'cartoon'
        patt.complete_parameters()
        self.assertEqual([os.path.normpath(p) for p in process.truc],
                         [os.path.normpath(p) for p in
                            ['/tmp/in/DummyListProcess_truc_jojo_barbapapa',
                             '/tmp/in/DummyListProcess_truc_koko_barbatruc',]])
        self.assertEqual([os.path.normpath(p) for p in process.bidule],
                         [os.path.normpath(p) for p in
                            ['/tmp/in/DummyListProcess_bidule_jojo_barbapapa',
                             '/tmp/in/DummyListProcess_bidule_koko_barbatruc']]
        )
        self.assertEqual(os.path.normpath(process.result),
                         os.path.normpath(
                            '/tmp/out/DummyListProcess_result_cartoon'))


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
                    'DummyProcess_truc_muppets_%s' % s), 'w') as f:
                f.write('%s\n' %s)

        # run
        study_config.use_soma_workflow = False
        study_config.run(pipeline)

        # check outputs
        out_files = [
            os.path.join(
                study_config.output_directory,
                'DummyProcess_bidule_muppets_%s' % s) for s in atts.subject]
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
                    'DummyProcess_truc_muppets_%s' % s), 'w') as f:
                f.write('%s\n' %s)

        #from capsul.pipeline import pipeline_workflow
        #wf = pipeline_workflow.workflow_from_pipeline(pipeline)
        #from soma_workflow import client as swc
        #swc.Helper.serialize('/tmp/workflow.workflow', wf)

        # run
        study_config.use_soma_workflow = True
        study_config.run(pipeline)

        # check outputs
        out_files = [
            os.path.join(
                study_config.output_directory,
                'DummyProcess_bidule_muppets_%s' % s) for s in atts.subject]
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
