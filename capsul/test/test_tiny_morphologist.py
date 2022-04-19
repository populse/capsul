# -*- coding: utf-8 -*-

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from soma.controller import field, File
from soma.controller import Directory, undefined

from capsul.api import Capsul, Process, Pipeline
from capsul.config.configuration import ModuleConfiguration
from capsul.dataset import generate_paths

class FakeSPMConfiguration(ModuleConfiguration):
    ''' SPM configuration module
    '''
    name = 'fakespm'
    directory: Directory
    version: str

    def __init__(self):
        super().__init__()

    def is_valid_config(self, requirements):
        required_version = requirements.get('version')
        if required_version \
                and getattr(self, 'version', undefined) != required_version:
            return False
        return True

def init_execution_context(execution_context):
    '''
    Configure an execution context given a capsul_engine and some requirements.
    '''
    config =  execution_context.config['modules']['spm']
    execution_context.spm = SPMConfiguration()
    execution_context.spm.import_dict(config)


class BiasCorrection(Process):
    input: field(type_=File, extensions=('.nii',))
    strength: float = 0.8
    output: field(type_=File, write=True, extensions=('.nii',))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f'{content}Bias correction with strength={self.strength}\n'
        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, 'w') as f:
            f.write(content)

    metadata_schema = dict(
        bids={'output': {'part': 'nobias'}},
        brainvisa={'output': {'prefix': 'nobias'}}
    )

class FakeSPMNormalization12(Process):
    input: field(type_=File, extensions=('.nii',))
    template: field(
        type_=File, 
        extensions=('.nii',),
        completion='spm',
        dataset='fakespm'
    ) = '!{fakespm.directory}/template'
    output: field(type_=File, write=True, extensions=('.nii',))
    
    requirements = {
        'fakespm': {
            'version': '12'
        }
    }
    
    metadata_schema = dict(
        bids={'output': {'part': 'normalized_fakespm12'}},
        brainvisa={'output': {'prefix': 'normalized_fakespm12'}}
    )

    def execute(self, context):
        fakespmdir = Path(context.fakespm.directory)
        real_version = (fakespmdir / 'fakespm').read_text().strip()
        with open(self.input) as f:
            content = f.read()
        with open(self.template) as f:
            template = f.read().strip()
        content = f'{content}Normalization with fakespm {real_version} installed in {fakespmdir} using template "{template}"\n'
        with open(self.output, 'w') as f:
            f.write(content)

class FakeSPMNormalization8(FakeSPMNormalization12):
    requirements = {
        'fakespm': {
            'version': '8'
        }
    }

    metadata_schema = dict(
        bids={'output': {'part': 'normalized_fakespm8'}},
        brainvisa={'output': {'prefix': 'normalized_fakespm8'}}
    )

class AimsNormalization(Process):
    input: field(type_=File, extensions=('.nii',))
    origin: field(type_=list[float], default_factory=lambda: [1.2, 3.4, 5.6])
    output: field(type_=File, write=True, extensions=('.nii',))

    metadata_schema = dict(
        bids={'output': {'part': 'normalized_aims'}},
        brainvisa={'output': {'prefix': 'normalized_aims'}}
    )

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f'{content}Normalization with Aims, origin={self.origin}\n'
        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, 'w') as f:
            f.write(content)

class SplitBrain(Process):
    input: field(type_=File, extensions=('.nii',))
    right_output: field(type_=File, write=True, extensions=('.nii',))
    left_output: field(type_=File, write=True, extensions=('.nii',))

    metadata_schema = dict(
        bids={'output': {'part': 'split'}},
        brainvisa={'output': {'prefix': 'split'}}
    )

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        for side in ('left', 'right'):
            side_content = f'{content}Split brain side={side}\n'
            output = getattr(self, f'{side}_output')
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, 'w') as f:
                f.write(side_content)


class ProcessHemisphere(Process):
    input: field(type_=File, extensions=('.nii',))
    output: field(type_=File, write=True, extensions=('.nii',))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f'{content}Process hemisphere\n'
        with open(self.output, 'w') as f:
            f.write(content)

class TinyMorphologist(Pipeline):
    def pipeline_definition(self):
        self.add_process('nobias', BiasCorrection)

        self.add_switch('normalization', ['none', 'fakespm12', 'fakespm8', 'aims'], ['output'])
        self.add_process('fakespm_normalization_12', FakeSPMNormalization12)
        self.add_process('fakespm_normalization_8', FakeSPMNormalization8)
        self.add_process('aims_normalization', AimsNormalization)
        self.add_process('split', SplitBrain)
        self.add_process('right_hemi', ProcessHemisphere)
        self.add_process('left_hemi', ProcessHemisphere)

        self.add_link('nobias.output->normalization.none_switch_output')
        
        self.add_link('nobias.output->fakespm_normalization_12.input')
        self.add_link('fakespm_normalization_12.output->normalization.fakespm12_switch_output')
        self.add_link('nobias.output->fakespm_normalization_8.input')
        self.add_link('fakespm_normalization_8.output->normalization.fakespm8_switch_output')
        self.export_parameter('fakespm_normalization_12', 'template')
        self.add_link('nobias.output->aims_normalization.input')
        self.add_link('aims_normalization.output->normalization.aims_switch_output')

        self.export_parameter('nobias', 'output', 'nobias')

        self.add_link('normalization.output->split.input')
        self.export_parameter('normalization', 'output', 'normalized')
        self.add_link('split.right_output->right_hemi.input')
        self.export_parameter('right_hemi', 'output', 'right_hemisphere')
        self.add_link('split.left_output->left_hemi.input')
        self.export_parameter('left_hemi', 'output', 'left_hemisphere')

    metadata_schema = dict(
        bids={
            '*': {'pipeline': 'tinymorphologist'},
            'left_hemisphere': {'part': 'left_hemi'},
            'right_hemisphere': {'part': 'right_hemi'},
        },
        brainvisa={
            '*': {'process': 'tinymorphologist'},
            'left_hemisphere': {'prefix': 'left_hemi'},
            'right_hemisphere': {'prefix': 'right_hemi'},
        }
    )

def concatenate(inputs: list[File], result: File):
    with open(result, 'w') as o:
        for f in inputs:
            print('-' * 40, file=o)
            print(f, file=o)
            print('-' * 40, file=o)
            with open(f) as i:
                o.write(i.read())

class TestTinyMorphologist(unittest.TestCase):
    subjects = (
        'aleksander',
        'casimiro',
        # 'christophorus',
        # 'christy',
        # 'conchobhar',
        # 'cornelia',
        # 'dakila',
        # 'demosthenes',
        # 'devin',
        # 'ferit',
        # 'gautam',
        # 'hikmat',
        # 'isbel',
        # 'ivona',
        # 'jordana',
        # 'justyn',
        # 'katrina',
        # 'lyda',
        # 'melite',
        # 'til',
        # 'vanessza',
        # 'victoria'
    )

    def setUp(self):
        self.tmp = tmp = Path(tempfile.mkdtemp(prefix='capsul_test_'))
        print('setup', self.tmp)
        #-------------------#
        # Environment setup #
        #-------------------#

        # Create BIDS directory
        self.bids = bids = tmp / 'bids'
        # Write Capsul specific information
        bids.mkdir()
        with (bids / 'capsul.json').open('w') as f:
            json.dump({
                'metadata_schema': 'bids'
            }, f)

        # Create BrainVISA directory
        self.brainvisa = brainvisa = tmp / 'brainvisa'
        brainvisa.mkdir()
        # Write Capsul specific information
        with (brainvisa / 'capsul.json').open('w') as f:
            json.dump({
                'metadata_schema': 'brainvisa'
            }, f)

        # Generate fake T1 and T2 data in bids directory
        for subject in self.subjects:
            for session in ('m0', 'm12', 'm24'):
                for data_type in ('T1w', 'T2w'):
                    subject_dir = bids/ f'rawdata' / f'sub-{subject}'
                    session_dir = subject_dir / f'ses-{session}'
                    file = session_dir / 'anat' / f'sub-{subject}_ses-{session}_{data_type}.nii'
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file_name = str(file.name)
                    with file.open('w') as f:
                        print(f'{data_type} acquisition for subject {subject} acquired in session {session}', file=f)
                    
                    sessions_file = subject_dir / f'sub-{subject}_sessions.tsv'
                    if not sessions_file.exists():
                        with open(sessions_file, 'w') as f:
                            f.write('session_id\tsession_metadata\n')
                    with open(sessions_file, 'a') as f:
                        f.write(f'ses-{session}\tsession metadata for {file_name}\n')

                    scans_file = session_dir / f'sub-{subject}_ses-{session}_scans.tsv'
                    if not scans_file.exists():
                        with open(scans_file, 'w') as f:
                            f.write('filename\tscan_metadata\n')
                    with open(scans_file, 'a') as f:
                        f.write(f'{file.relative_to(session_dir)}\tscan metadata for {file_name}\n')

                    with file.with_suffix('.json').open('w') as f:
                        json.dump(dict(
                            json_metadata=f'JSON metadata for {file_name}'
                        ),f)

        # Configuration base dictionary
        config = {
            'local': {
                'load_modules': [
                    'capsul.test.test_tiny_morphologist',
                ],
                'dataset': {
                    'input': {
                        'path': str(self.bids),
                        'metadata_schema': 'bids',
                    },
                    'output': {
                        'path': str(self.brainvisa),
                        'metadata_schema': 'brainvisa',
                    }
                }
            }
        }
        # Create fake SPM directories
        for version in ('8', '12'):
            fakespm = tmp / 'software' / f'fakespm-{version}'
            fakespm.mkdir(parents=True, exist_ok=True)
            # Write a file containing only the version string that will be used
            # by fakespm module to check installation.
            (fakespm / 'fakespm').write_text(version)
            # Write a fake template file
            (fakespm / 'template').write_text(f'template of fakespm {version}')
            fakespm_config = {
                'directory': str(fakespm),
                'version': version,
            }
            config['local'].setdefault('fakespm', {})[f'fakespm_{version}'] = fakespm_config
            

        # Create a configuration file
        self.config_file = tmp / 'capsul_config.json'
        with self.config_file.open('w') as f:
            json.dump(config, f)

        self. capsul = Capsul('test_tiny_morphologist', site_file=self.config_file)
        return super().setUp()

    def tearDown(self):
        self.capsul = None
        Capsul.delete_singleton()
        print('tear down', self.tmp)
        shutil.rmtree(self.tmp)
        return super().tearDown()

    def test_tiny_morphologist_config(self):
        self.maxDiff = 2000
        expected_config = {
            'local': {
                'dataset': {
                    'input': {
                        'path': str(self.tmp / 'bids'),
                        'metadata_schema': 'bids',
                    },
                    'output': {
                        'path': str(self.tmp / 'brainvisa'),
                        'metadata_schema': 'brainvisa',
                    },
                },
                'fakespm': {
                    'fakespm_12': {
                        'directory': str(self.tmp / 'software' / 'fakespm-12'),
                        'version': '12'
                    },
                    'fakespm_8': {
                        'directory': str( self.tmp / 'software' / 'fakespm-8'),
                        'version': '8'
                    }
                },
                'load_modules': ['capsul.test.test_tiny_morphologist'],
            }            
        }
        self.assertEqual(self.capsul.config.asdict(), expected_config)

        engine = self.capsul.engine()
        tiny_morphologist = self.capsul.executable('capsul.test.test_tiny_morphologist.TinyMorphologist')
        
        context = engine.execution_context(tiny_morphologist)
        expected_context = {
            'dataset': {
                'input': {
                    'path': str(self.tmp / 'bids'),
                    'metadata_schema': 'bids',
                },
                'output': {
                    'path': str(self.tmp / 'brainvisa'),
                    'metadata_schema': 'brainvisa',
                },
            },
        }
        self.assertEqual(context.asdict(), expected_context)

        tiny_morphologist.normalization = 'fakespm12'
        context = engine.execution_context(tiny_morphologist)
        fakespm12_conf = {
            'directory': str( self.tmp / 'software' / 'fakespm-12'),
             'version': '12'
        }
        expected_context['fakespm'] = fakespm12_conf
        self.assertEqual(context.asdict(), expected_context)

        tiny_morphologist_iteration = self.capsul.custom_pipeline()
        tiny_morphologist_iteration.add_iterative_process(
            'tiny_morphologist',
            'capsul.test.test_tiny_morphologist.TinyMorphologist',
            non_iterative_plugs=['template'],
        )
        tiny_morphologist_iteration.autoexport_nodes_parameters(include_optional=True)
        context = engine.execution_context(tiny_morphologist_iteration)
        del expected_context['fakespm']
        context = engine.execution_context(tiny_morphologist_iteration)
        self.assertEqual(context.asdict(), expected_context)
        tiny_morphologist_iteration.normalization = ['none', 'aims', 'fakespm12']
        expected_context['fakespm'] = fakespm12_conf
        context = engine.execution_context(tiny_morphologist_iteration)
        self.assertEqual(context.asdict(), expected_context)

    def test_path_generation(self):
        expected = {
            'none': {
                'template': '!{fakespm.directory}/template',
                'nobias': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/nobias_aleksander.nii',
                'normalized': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/nobias_aleksander.nii',
                'right_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/right_hemi_aleksander.nii',
                'left_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/left_hemi_aleksander.nii',
            },
            'aims': {
                'template': '!{fakespm.directory}/template',
                'nobias': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/nobias_aleksander.nii',
                'normalized': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/normalized_aims_aleksander.nii',
                'right_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/right_hemi_aleksander.nii',
                'left_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/left_hemi_aleksander.nii',
            },
            'fakespm12': {
                'template': '!{fakespm.directory}/template',
                'nobias': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/nobias_aleksander.nii',
                'normalized': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/normalized_fakespm12_aleksander.nii',
                'right_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/right_hemi_aleksander.nii',
                'left_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/left_hemi_aleksander.nii',
            },
            'fakespm8': {
                'template': '!{fakespm.directory}/template',
                'nobias': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/nobias_aleksander.nii',
                'normalized': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/normalized_fakespm8_aleksander.nii',
                'right_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/right_hemi_aleksander.nii',
                'left_hemisphere': '!{dataset.output}/whaterver/aleksander/tinymorphologist/m0/default/left_hemi_aleksander.nii',
            },
        }
        engine = self.capsul.engine()
        for normalization in ('none', 'aims', 'fakespm12', 'fakespm8'):
            tiny_morphologist = self.capsul.executable('capsul.test.test_tiny_morphologist.TinyMorphologist')
            tiny_morphologist.input = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')
            tiny_morphologist.normalization = normalization
            execution_context = engine.execution_context(tiny_morphologist)
            # for field in execution_context.dataset.fields():
            #     dataset = getattr(execution_context.dataset, field.name)
            #     print(f'!dataset! {field.name} = {dataset.path} [{dataset.metadata_schema}]')
            # if getattr(execution_context, 'fakespm', undefined) is not undefined:
            #     print('!fakespm dir!', execution_context.fakespm.directory)
            generate_paths(tiny_morphologist, execution_context)
            params = dict((i, 
                getattr(tiny_morphologist, i, undefined)) for i in ('template', 
                    'nobias', 'normalized', 'right_hemisphere', 'left_hemisphere'))
            self.assertEqual(params, expected[normalization])
            # for field in tiny_morphologist.fields():
            #     value = getattr(tiny_morphologist, field.name, undefined)
            #     print(f'!{normalization}!', field.name, value)

    def test_pipeline_iteration(self):
        tiny_morphologist_iteration = self.capsul.custom_pipeline()
        tiny_morphologist_iteration.add_iterative_process(
            'tiny_morphologist',
            'capsul.test.test_tiny_morphologist.TinyMorphologist',
            non_iterative_plugs=['template'],
        )
        tiny_morphologist_iteration.autoexport_nodes_parameters(include_optional=True)
        
        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        count = 0
        inputs = []
        normalizations = []

        from pprint import pprint
        for path in self.capsul.config.local.dataset.input.find(suffix='T1w', extension='nii'):
            inputs.extend([str(path)]*3)
            normalizations += ['none', 'aims', 'fakespm8']
        # Set the input data
        tiny_morphologist_iteration.input = inputs
        tiny_morphologist_iteration.normalization = normalizations
        engine = self.capsul.engine()
        execution_context = engine.execution_context(tiny_morphologist_iteration)
        generate_paths(tiny_morphologist_iteration, execution_context, debug=True)
        for field in tiny_morphologist_iteration.fields():
            value = getattr(tiny_morphologist_iteration, field.name, undefined)
            print(f'!param!', field.name, value)
            

    #         # for field in tiny_morphologist.fields():
    #         #     value = getattr(tiny_morphologist, field.name, None)
    #         #     print('   ', ('<-' if field.is_output() else '->'), field.name, '=', value)
    #         # for node_name, node in tiny_morphologist.nodes.items():
    #         #     if not node_name:
    #         #         continue
    #         #     print('   ', node_name, ':', getattr(node ,'definition', node.__class__.__name__))
    #         #     if isinstance(node,Process):
    #         #         for field in node.fields():
    #         #             value = getattr(node, field.name, None)
    #         #             print('       ', ('<-' if field.is_output() else '->'), field.name, '=', value)
    
    #     # for node_name, node in processing_pipeline.nodes.items():
    #     #     if not node_name:
    #     #         continue
    #     #     print('   ', node_name, ':', getattr(node ,'definition', node.__class__.__name__))
    #     #     if isinstance(node,Process):
    #     #         for field in node.fields():
    #     #             value = getattr(node, field.name, None)
    #     #             print('       ', ('<-' if field.is_output() else '->'), field.name, '=', value)

    #     pprint(processing_pipeline.json())
    #     try:
    #         with capsul.engine() as ce:
    #             # Finally execute all the TinyMorphologist instances
    #             execution_id = ce.run(processing_pipeline)
    #     except Exception:
    #         import traceback
    #         traceback.print_exc()

    #     # for f in pipeline_files:
    #     #     if os.path.exists(f):
    #     #         print('-' * 40)
    #     #         print(f)
    #     #         print('-' * 40)
    #     #         with open(f) as file:
    #     #             print(file.read())

    #     import sys
    #     sys.stdout.flush()
    #     from soma.qt_gui.qt_backend import QtGui
    #     from capsul.qt_gui.widgets import PipelineDeveloperView
    #     app = QtGui.QApplication.instance()
    #     if not app:
    #         app = QtGui.QApplication(sys.argv)
    #     view1 = PipelineDeveloperView(processing_pipeline, show_sub_pipelines=True)
    #     view1.show()
    #     app.exec_()
    #     del view1
