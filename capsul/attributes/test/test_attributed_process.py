
from __future__ import print_function

from capsul.api import StudyConfig, Process
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    PathCompletionEngine, PathCompletionEngineFactory
from capsul.attributes.attributes_schema import ProcessAttributes, \
    AttributesSchema, EditableAttributes
from traits.api import Str, Float, File, String, Undefined
import unittest
import os
import sys


class DummyProcess(Process):
    f = Float(output=False)

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("truc", File(output=False))
        self.add_trait("bidule", File(output=True))


class BrainvisaTestSchema(AttributesSchema):
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


def init_study_config():
    study_config = StudyConfig('test_study', modules=['AttributesConfig'])
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
        self.study_config = init_study_config()

    def test_completion(self):
        study_config = self.study_config
        process = study_config.get_process_instance(
            'capsul.attributes.test.test_attributed_process.DummyProcess')
        from capsul.attributes.test.test_attributed_process \
            import DummyProcessAttributes, MyPathCompletion
        patt = ProcessCompletionEngine.get_completion_engine(process)
        atts = patt.get_attribute_values(process)
        self.assertTrue(isinstance(patt, ProcessCompletionEngine))
        self.assertTrue(isinstance(atts, DummyProcessAttributes))
        self.assertTrue(isinstance(
            patt.get_path_completion_engine(process),
            MyPathCompletion))
        atts.center = 'jojo'
        atts.subject = 'barbapapa'
        patt.complete_parameters(process)
        self.assertEqual(process.truc,
                         '/tmp/in/DummyProcess_truc_jojo_barbapapa')
        self.assertEqual(process.bidule,
                         '/tmp/out/DummyProcess_bidule_jojo_barbapapa')


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
        atts = patt.get_attribute_values(process)

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


