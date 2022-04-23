# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from soma.controller import File, field
from soma_workflow import configuration as swconfig

from capsul.api import Process, executable, Capsul
from ...dataset import Dataset, MetadataSchema
from capsul.attributes.attributes_schema import ProcessAttributes
from capsul.dataset import generate_paths


class DummyProcess(Process):
    f: float = field(output=False)

    def __init__(self, definition):
        super(DummyProcess, self).__init__(definition)
        self.add_field('truc', type_=File, write=False)
        self.add_field('bidule', type_=File, write=True)

    def execute(self, context):
        with open(self.bidule, 'w') as f:
            with open(self.truc) as g:
                f.write(g.read())

    metadata_schema = {
        'custom': {
            '*': {'process': 'DummyProcess'},
            'truc': {'parameter': 'truc'},
            'bidule': {'parameter': 'bidule'},
        }
    }

class DummyListProcess(Process):
    truc: field(type_=list[File], write=False)
    bidule: field(type_=list[File], write=False)
    result: field(type_=File, write=True)

    def execute(self, context):
        with open(self.result, 'w') as f:
            f.write(
                '{\n    truc=%s,\n    bidule=%s\n}' % (self.truc, self.bidule))

    metadata_schema = {
        'custom': {
            '*': {'process': 'DummyListProcess'},
            'truc': {'parameter': 'truc'},
            'bidule': {'parameter': 'bidule'},
            'result': {'parameter': 'result'},
        }
    }

class CustomMetadataSchema(MetadataSchema):
    process: str
    parameter: str
    center: str
    subject: str
    analysis: str
    group: str
     
    def _path_list(self):
        items = []
        for field in self.fields():
            value = getattr(self, field.name, None)
            if value:
                items.append(value)
        return ['_'.join(items)]
    
Dataset.register_schema('custom', CustomMetadataSchema)


def setUpModule():
    global old_home
    global temp_home_dir
    # Run tests with a temporary HOME directory so that they are isolated from
    # the user's environment
    temp_home_dir = None
    old_home = os.environ.get('HOME')
    try:
        app_name = 'test_completion'
        temp_home_dir = Path(tempfile.mkdtemp(prefix='capsul_test_completion_'))
        os.environ['HOME'] = str(temp_home_dir)
        swconfig.change_soma_workflow_directory(temp_home_dir)
        config = temp_home_dir / '.config'
        config.mkdir()
        input = temp_home_dir / 'in'
        output = temp_home_dir / 'out'
        with (config / f'{app_name}.json').open('w') as f:
            json.dump({
                'local': {
                    'python_modules': [
                        'capsul.attributes.test.test_attributed_process'
                    ],
                    'dataset': {
                        'input': {
                            'path': str(input),
                            'metadata_schema': 'custom',
                        },
                        'output': {
                            'path': str(output),
                            'metadata_schema': 'custom',
                        }
                    }
                }
            }, f)
        capsul = Capsul(app_name)
    
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

    # def tearDown(self):
    #     swm = self.study_config.modules['SomaWorkflowConfig']
    #     swc = swm.get_workflow_controller()
    #     if swc is not None:
    #         # stop workflow controller and wait for thread termination
    #         swc.stop_engine()

    def test_completion(self):
        global temp_home_dir
    
        process = executable(
            'capsul.attributes.test.test_attributed_process.DummyProcess')
        execution_context = Capsul().engine().execution_context(process)
        generate_paths(process, execution_context, metadata = {
                'center': 'jojo',
                'subject': 'barbapapa',
            })
        process.resolve_paths(execution_context)
        self.assertEqual(os.path.normpath(process.truc),
                         os.path.normpath(f'{temp_home_dir}/in/DummyProcess_truc_jojo_barbapapa'))
        self.assertEqual(os.path.normpath(process.bidule),
                         os.path.normpath(f'{temp_home_dir}/out/DummyProcess_bidule_jojo_barbapapa'))


    def test_iteration(self):
        pipeline = Capsul().iteration_pipeline(
            'capsul.attributes.test.test_attributed_process.DummyProcess',
            iterative_plugs=['truc', 'bidule'])
        execution_context = Capsul().engine().execution_context(pipeline)
        generate_paths(pipeline, execution_context, metadata = [{
                'process': 'DummyProcess',
                'center': 'muppets',
                'subject': i,
            } for i in ['kermit', 'piggy', 'stalter', 'waldorf']])
        pipeline.resolve_paths(execution_context)
        self.assertEqual([os.path.normpath(p) for p in pipeline.truc],
                         [f'{temp_home_dir}/in/DummyProcess_truc_muppets_kermit',
                          f'{temp_home_dir}/in/DummyProcess_truc_muppets_piggy',
                          f'{temp_home_dir}/in/DummyProcess_truc_muppets_stalter',
                          f'{temp_home_dir}/in/DummyProcess_truc_muppets_waldorf'])
        self.assertEqual([os.path.normpath(p) for p in pipeline.bidule],
                         [f'{temp_home_dir}/out/DummyProcess_bidule_muppets_kermit',
                          f'{temp_home_dir}/out/DummyProcess_bidule_muppets_piggy',
                          f'{temp_home_dir}/out/DummyProcess_bidule_muppets_stalter',
                          f'{temp_home_dir}/out/DummyProcess_bidule_muppets_waldorf'])

    def test_list_completion(self):
        process = executable(
            'capsul.attributes.test.test_attributed_process.DummyListProcess')
        execution_context = Capsul().engine().execution_context(process)
        generate_paths(process, execution_context, 
            ignore={'result'},
            metadata = [
            {
                'center': 'jojo',
                'subject': 'barbapapa',
            },
            {
                'center': 'koko',
                'subject': 'barbatruc'
            }]
        )
        generate_paths(process, execution_context, 
            fields={'result'},
            metadata = {
                'group': 'cartoon',
            }
        )
        process.resolve_paths(execution_context)
        self.assertEqual([os.path.normpath(p) for p in process.truc],
                         [f'{temp_home_dir}/in/DummyListProcess_truc_jojo_barbapapa',
                          f'{temp_home_dir}/in/DummyListProcess_truc_koko_barbatruc',])
        self.assertEqual([os.path.normpath(p) for p in process.bidule],
                         [f'{temp_home_dir}/in/DummyListProcess_bidule_jojo_barbapapa',
                          f'{temp_home_dir}/in/DummyListProcess_bidule_koko_barbatruc']
        )
        self.assertEqual(os.path.normpath(process.result),
                         f'{temp_home_dir}/out/DummyListProcess_result_cartoon')


    @unittest.skip('reimplementation expected for capsul v3')
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


    @unittest.skip('reimplementation expected for capsul v3')
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

