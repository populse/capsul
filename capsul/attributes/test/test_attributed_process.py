
from __future__ import print_function

from capsul.api import StudyConfig, Process, Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    PathCompletionEngine, PathCompletionEngineFactory
from capsul.attributes.attributes_schema import ProcessAttributes, \
    AttributesSchema, EditableAttributes
from traits.api import Str, Float, File, String, Undefined
from soma_workflow import configuration as swconfig
import unittest
import os
import sys
import tempfile
import shutil
import socket
if sys.version_info[0] >= 3:
    import io as StringIO
else:
    import StringIO


class DummyProcess(Process):
    f = Float(output=False)

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("truc", File(output=False))
        self.add_trait("bidule", File(output=True))

    def _run_process(self):
        open(self.bidule, 'w').write(open(self.truc).read())


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
        self.set_parameter_attributes('truc', 'input', 'Acquisition',
                                      dict(type='array'))
        self.set_parameter_attributes('bidule', 'output', 'Acquisition',
                                      dict(type='array'))

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
    study_config.attributes_schema_paths.append(
        'capsul.attributes.test.test_attributed_process')
    study_config.attributes_schemas['input'] = 'custom_ex'
    study_config.attributes_schemas['output'] = 'custom_ex'
    study_config.path_completion = 'custom_ex'

    return study_config


class TestCompletion(unittest.TestCase):

    def setUp(self):
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
        self.study_config = init_study_config()
        if not hasattr(self, 'temps'):
            self.temps = []


    def tearDown(self):
        shutil.rmtree(self.soma_workflow_temp_dir)


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
        pipeline = Pipeline()
        pipeline.set_study_config(study_config)
        pipeline.add_iterative_process(
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        pipeline.autoexport_nodes_parameters()
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


    def test_run_iteraton_sequential(self):
        study_config = self.study_config
        tmp_dir = tempfile.mkdtemp(prefix='capsul_')
        self.temps.append(tmp_dir)

        study_config.input_directory = os.path.join(tmp_dir, 'in')
        study_config.output_directory = os.path.join(tmp_dir, 'out')
        os.mkdir(study_config.input_directory)
        os.mkdir(study_config.output_directory)

        pipeline = Pipeline()
        pipeline.set_study_config(study_config)
        pipeline.add_iterative_process(
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        pipeline.autoexport_nodes_parameters()
        cm = ProcessCompletionEngine.get_completion_engine(pipeline)
        atts = cm.get_attribute_values()
        atts.center = ['muppets']
        atts.subject = ['kermit', 'piggy', 'stalter', 'waldorf']
        cm.complete_parameters()

        # create input files
        for s in atts.subject:
            open(os.path.join(
                study_config.input_directory,
                'DummyProcess_truc_muppets_%s' % s), 'w').write('%s\n' %s)

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
            self.assertTrue(open(out_file).read() == '%s\n' % s)


    def test_run_iteraton_swf(self):
        study_config = self.study_config
        tmp_dir = tempfile.mkdtemp(prefix='capsul_')
        self.temps.append(tmp_dir)

        study_config.input_directory = os.path.join(tmp_dir, 'in')
        study_config.output_directory = os.path.join(tmp_dir, 'out')
        os.mkdir(study_config.input_directory)
        os.mkdir(study_config.output_directory)

        pipeline = Pipeline()
        pipeline.set_study_config(study_config)
        pipeline.add_iterative_process(
            'dummy',
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            ['truc', 'bidule'])
        pipeline.autoexport_nodes_parameters()
        cm = ProcessCompletionEngine.get_completion_engine(pipeline)
        atts = cm.get_attribute_values()
        atts.center = ['muppets']
        atts.subject = ['kermit', 'piggy', 'stalter', 'waldorf']
        cm.complete_parameters()

        # create input files
        for s in atts.subject:
            open(os.path.join(
                study_config.input_directory,
                'DummyProcess_truc_muppets_%s' % s), 'w').write('%s\n' %s)

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
            self.assertTrue(open(out_file).read() == '%s\n' % s)


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
            import PipelineDevelopperView
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
        pv = PipelineDevelopperView(process, allow_open_controller=True,
                                    enable_edition=True,
                                    show_sub_pipelines=True)
        pc = AttributedProcessWidget(process, enable_attr_from_filename=True,
                                    enable_load_buttons=True)

        pv.show()
        pc.show()
        if qapp:
            qapp.exec_()


