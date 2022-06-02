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
from capsul.dataset import generate_paths, MetadataSchema, Dataset

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
    execution_context.spm = FakeSPMConfiguration()
    execution_context.spm.import_dict(config)

class SharedSchema(MetadataSchema):
    '''Metadata schema for BrainVISA shared dataset
    '''
    data_id: str = ''

    def _path_list(self):
        '''
        The path has the following pattern:
        <something>
        '''

        path_list = []
        filename = []
        if self.data_id == 'normalization_template':
            path_list = ['anatomical_templates']
            filename.append('MNI152_T1_2mm.nii.gz')
        else:
            filename.append(self.data_id)
        path_list.append(''.join(filename))
        return path_list

Dataset.schemas['shared'] = SharedSchema

# patch processes to setup their requirements and schemas

from capsul.pipeline.test.fake_morphologist.morphologist \
    import Morphologist
from capsul.pipeline.test.fake_morphologist.t1biascorrection \
    import T1BiasCorrection
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm12_reinit \
    import normalization_t1_spm12_reinit
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm8_reinit \
    import normalization_t1_spm8_reinit
from capsul.pipeline.test.fake_morphologist.normalization_aimsmiregister \
    import normalization_aimsmiregister

T1BiasCorrection.metadata_schema = dict(
    bids={'t1mri_nobias': {'part': 'nobias'}},
    brainvisa={'t1mri_nobias': {'prefix': 'nobias'}}
)

normalization_t1_spm12_reinit.requirements = {
    'fakespm': {
        'version': '12'
    }
}
    
#normalization_t1_spm12_reinit.metadata_schema = dict(
    #bids={'output': {'part': 'normalized_fakespm12'}},
    #brainvisa={'output': {'prefix': 'normalized_fakespm12'}},
    #shared={'anatomical_template': {'data_id': 'normalization_template'}},
#)


normalization_t1_spm8_reinit.requirements = {
    'fakespm': {
        'version': '8'
    }
}

#normalization_t1_spm8_reinit.metadata_schema = dict(
    #bids={'output': {'part': 'normalized_fakespm8'}},
    #brainvisa={'output': {'prefix': 'normalized_fakespm8'}}
#)

normalization_aimsmiregister.metadata_schema = dict(
    bids={'transformation_to_ACPC': {'part': 'normalized_aims',
                                     'extension': 'trm'}},
    brainvisa={'transformation_to_ACPC': {'prefix': 'normalized_aims',
                                          'extension': 'trm'}},
    shared={'anatomical_template': {'data_id': 'normalization_template'}},
)


#SplitBrain.metadata_schema = dict(
        #bids={'output': {'part': 'split'}},
        #brainvisa={'output': {'prefix': 'split'}}
    #)


Morphologist.metadata_schema = dict(
    bids={
        '*': {'pipeline': 'morphologist'},
        'left_labelled_graph': {'part': 'left_hemi'},
        'right_labelled_graph': {'part': 'right_hemi'},
    },
    brainvisa={
        '*': {'process': None, 'modality': 't1mri'},
        'imported_t1mri': {'analysis': undefined},
        'left_labelled_graph': {
            'seg_directory': 'folds',
            'sulci_graph_version': '3.1',
            'sulci_recognition_session': 'default_session_auto',
            'short_prefix': 'L',
            'suffix': 'default_session_auto',
            'extension': 'arg'},
        'right_labelled_graph': {
            'seg_directory': 'folds',
            'sulci_graph_version': '3.1',
            'sulci_recognition_session': 'default_session_auto',
            'short_prefix': 'R',
            'suffix': 'default_session_auto',
            'extension': 'arg'},
        'Talairach_transform': {
            'analysis': undefined,
            'seg_directory': 'registration',
            'short_prefix': 'RawT1-',
            'suffix': '%(acquisition)s_TO_Talairach-ACPC',
            'extension': 'trm'},
    },
    shared={
        'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': {'data_id': 'normalization_template'}
    },
)

datasets = {
    't1mri': 'input',
    'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': 'shared',
    'PrepareSubject_TalairachFromNormalization_normalized_referential': 'shared',
    'PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized': 'shared',
    'PrepareSubject_TalairachFromNormalization_acpc_referential': 'shared',
    'PrepareSubject_StandardACPC_older_MNI_normalization': None,
    'PrepareSubject_Normalization_commissures_coordinates': None,
    'PrepareSubject_Normalization_NormalizeFSL_template': 'shared',
    'PrepareSubject_Normalization_NormalizeSPM_template': 'shared',
    'PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume': None,
    'PrepareSubject_Normalization_NormalizeBaladin_template': 'shared',
    'PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc': 'shared',
    'BrainSegmentation_lesion_mask': None,
    'Renorm_template': 'shared',
    'Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume': None,
    'Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc': 'shared',
    'HeadMesh_remove_mask': None,
    'SplitBrain_split_template': 'shared',
    'GreyWhiteClassification_lesion_mask': None,
    'SulciRecognition_SPAM_recognition09_global_recognition_labels_priors': 'shared',
    'SulciRecognition_SPAM_recognition09_global_recognition_initial_transformation': None,
    'SulciRecognition_SPAM_recognition09_global_recognition_model': 'shared',
    'SulciRecognition_SPAM_recognition09_local_recognition_model': 'shared',
    'SulciRecognition_SPAM_recognition09_local_recognition_local_referentials': 'shared',
    'SulciRecognition_SPAM_recognition09_local_recognition_direction_priors': 'shared',
    'SulciRecognition_SPAM_recognition09_local_recognition_angle_priors': 'shared',
    'SulciRecognition_SPAM_recognition09_local_recognition_translation_priors': 'shared',
    'SulciRecognition_SPAM_recognition09_markovian_recognition_model': 'shared',
    'SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model': 'shared',
    'SulciRecognition_CNN_recognition19_model_file': 'shared',
    'SulciRecognition_CNN_recognition19_param_file': 'shared',
    'GreyWhiteClassification_1_lesion_mask': None,
    'SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors': 'shared',
    'SulciRecognition_1_SPAM_recognition09_global_recognition_initial_transformation': None,
    'SulciRecognition_1_SPAM_recognition09_global_recognition_model': 'shared',
    'SulciRecognition_1_SPAM_recognition09_local_recognition_model': 'shared',
    'SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials': 'shared',
    'SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors': 'shared',
    'SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors': 'shared',
    'SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors': 'shared',
    'SulciRecognition_1_SPAM_recognition09_markovian_recognition_model': 'shared',
    'SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model': 'shared',
    'SulciRecognition_1_CNN_recognition19_model_file': 'shared',
    'SulciRecognition_1_CNN_recognition19_param_file': 'shared',
    'SPAM_recognition_labels_translation_map': 'shared',
    'SulciRecognition_recognition2000_model': 'shared',
    'SulciRecognition_1_recognition2000_model': 'shared',
    'sulcal_morphometry_sulci_file': 'shared',
}


def get_shared_path():
    try:
        from soma import aims
        return aims.carto.Paths.resourceSearchPath()[-1]
    except Exception:
        #return '/casa/host/build/share/brainvisa-share-5.1'
        return '!{dataset.shared.path}'


class TestFakeMorphologist(unittest.TestCase):
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
                'config_modules': [
                    'capsul.test.test_fake_morphologist',
                ],
                'dataset': {
                    'input': {
                        'path': str(self.bids),
                        'metadata_schema': 'bids',
                    },
                    'output': {
                        'path': str(self.brainvisa),
                        'metadata_schema': 'brainvisa',
                    },
                    'shared': {
                        'path': get_shared_path(),
                        'metadata_schema': 'shared',
                    },
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

        self.capsul = Capsul('test_fake_morphologist', site_file=self.config_file)
        return super().setUp()

    def tearDown(self):
        #print('tmp dir:', self.tmp)
        #input('continue ?')
        self.capsul = None
        Capsul.delete_singleton()
        shutil.rmtree(self.tmp)
        return super().tearDown()

    def test_fake_morphologist_config(self):
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
                    'shared': {
                        'path': get_shared_path(),
                        'metadata_schema': 'shared',
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
                'config_modules': ['capsul.test.test_fake_morphologist'],
            }
        }
        self.assertEqual(self.capsul.config.asdict(), expected_config)

        engine = self.capsul.engine()
        morphologist = self.capsul.executable(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')

        morphologist.select_Talairach = 'StandardACPC'
        morphologist.perform_skull_stripped_renormalization = 'initial'
        
        context = engine.execution_context(morphologist)
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
                'shared': {
                    'path': get_shared_path(),
                    'metadata_schema': 'shared',
                },
            },
        }
        dict_context = context.asdict()
        #print('context:')
        #print(dict_context)
        #print('requirements:')
        #print(engine.executable_requirements(morphologist))
        self.assertEqual(dict_context, expected_context)

        morphologist.select_Talairach = 'Normalization'
        morphologist.perform_skull_stripped_renormalization = 'skull_stripped'
        morphologist.Normalization_select_Normalization_pipeline = 'NormalizeSPM'
        morphologist.spm_normalization_version \
            = 'normalization_t1_spm12_reinit'

        context = engine.execution_context(morphologist)
        #print('context:')
        #print(dict_context)
        #print('requirements:')
        #print(engine.executable_requirements(morphologist))
        fakespm12_conf = {
            'directory': str( self.tmp / 'software' / 'fakespm-12'),
            'version': '12'
        }
        expected_context['fakespm'] = fakespm12_conf
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

        morphologist_iteration = self.capsul.iteration_pipeline(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist',
            #non_iterative_plugs=['template'],
        )

        context = engine.execution_context(morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)
        morphologist_iteration.select_Talairach \
            = ['StandardACPC', 'Normalization', 'Normalization']
        morphologist_iteration.perform_skull_stripped_renormalization \
            = ['initial', 'skull_stripped', 'skull_stripped']

        morphologist_iteration.Normalization_select_Normalization_pipeline = [
            'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM']
        expected_context['fakespm'] = fakespm12_conf
        context = engine.execution_context(morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

    #@unittest.skip('not ready')
    def test_path_generation(self):
        expected = {
            ('StandardACPC', 'initial', 'NormalizeSPM',
             'normalization_t1_spm12_reinit'): {
                'imported_t1mri': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/aleksander.nii',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': '!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz',
                't1mri_nobias': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii',
                'Talairach_transform': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm',
                'left_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                'right_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
            },
            ('Normalization', 'skull_stripped', 'Normalization_AimsMIRegister',
             'normalization_t1_spm12_reinit'): {
                'imported_t1mri': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/aleksander.nii',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': '!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz',
                't1mri_nobias': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii',
                'Talairach_transform': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm',
                'left_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                'right_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
            },
            ('Normalization', 'skull_stripped', 'NormalizeSPM',
             'normalization_t1_spm12_reinit'): {
                'imported_t1mri': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/aleksander.nii',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': '!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz',
                't1mri_nobias': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii',
                'Talairach_transform': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm',
                'left_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                'right_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
            },
            ('Normalization', 'skull_stripped', 'NormalizeSPM',
             'normalization_t1_spm8_reinit'): {
                'imported_t1mri': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/aleksander.nii',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': '!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz',
                't1mri_nobias': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii',
                'Talairach_transform': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm',
                'left_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                'right_labelled_graph': '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
            },
        }
        engine = self.capsul.engine()
        sel_tal = ['StandardACPC', 'Normalization', 'Normalization',
                   'Normalization']
        renorm = ['initial', 'skull_stripped', 'skull_stripped',
                  'skull_stripped']
        norm = ['NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM']
        normspm = ['normalization_t1_spm12_reinit',
                   'normalization_t1_spm12_reinit',
                   'normalization_t1_spm12_reinit',
                   'normalization_t1_spm8_reinit']
        for normalization in zip(sel_tal, renorm, norm, normspm):
            morphologist = self.capsul.executable(
                'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')
            #morphologist.field('t1mri').dataset = 'bids'

            morphologist.t1mri = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')
            morphologist.select_Talairach = normalization[0]
            morphologist.perform_skull_stripped_renormalization \
                = normalization[1]
            morphologist.Normalization_select_Normalization_pipeline \
                = normalization[2]
            morphologist.spm_normalization_version = normalization[3]

            execution_context = engine.execution_context(morphologist)
            # for field in execution_context.dataset.fields():
            #     dataset = getattr(execution_context.dataset, field.name)
            #     print(f'!dataset! {field.name} = {dataset.path} [{dataset.metadata_schema}]')
            # if getattr(execution_context, 'fakespm', undefined) is not undefined:
            #     print('!fakespm dir!', execution_context.fakespm.directory)
            generate_paths(morphologist, execution_context, datasets=datasets,
                           source_fields=['t1mri'], debug=False)
            params = dict((i, 
                getattr(morphologist, i, undefined)) for i in (
                    'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template',
                    'imported_t1mri',
                    't1mri_nobias',
                    'Talairach_transform',
                    'left_labelled_graph',
                    'right_labelled_graph'))
            self.maxDiff = None
            self.assertEqual(params, expected[normalization])
            # for field in morphologist.fields():
            #     value = getattr(morphologist, field.name, undefined)
            #     print(f'!{normalization}!', field.name, value)


    @unittest.skip('not ready')
    def test_pipeline_iteration(self):
        expected_completion = {
            'input': [f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii'],
            'left_hemisphere': ['!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_{executable.normalization[0]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_{executable.normalization[1]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_{executable.normalization[2]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_{executable.normalization[3]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_{executable.normalization[4]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_{executable.normalization[5]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_{executable.normalization[6]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_{executable.normalization[7]}.nii',
                                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_{executable.normalization[8]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_{executable.normalization[9]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_{executable.normalization[10]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_{executable.normalization[11]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_{executable.normalization[12]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_{executable.normalization[13]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_{executable.normalization[14]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_{executable.normalization[15]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_{executable.normalization[16]}.nii',
                                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_{executable.normalization[17]}.nii'],
            'nobias': ['!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_{executable.normalization[0]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_{executable.normalization[1]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_{executable.normalization[2]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_{executable.normalization[3]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_{executable.normalization[4]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_{executable.normalization[5]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_{executable.normalization[6]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_{executable.normalization[7]}.nii',
                        '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_{executable.normalization[8]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_{executable.normalization[9]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_{executable.normalization[10]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_{executable.normalization[11]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_{executable.normalization[12]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_{executable.normalization[13]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_{executable.normalization[14]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_{executable.normalization[15]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_{executable.normalization[16]}.nii',
                        '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_{executable.normalization[17]}.nii'],
            'normalization': ['none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8'],
            'right_hemisphere': ['!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_{executable.normalization[0]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_{executable.normalization[1]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_{executable.normalization[2]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_{executable.normalization[3]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_{executable.normalization[4]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_{executable.normalization[5]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_{executable.normalization[6]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_{executable.normalization[7]}.nii',
                                    '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_{executable.normalization[8]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_{executable.normalization[9]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_{executable.normalization[10]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_{executable.normalization[11]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_{executable.normalization[12]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_{executable.normalization[13]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_{executable.normalization[14]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_{executable.normalization[15]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_{executable.normalization[16]}.nii',
                                    '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_{executable.normalization[17]}.nii'],
        }

        expected_resolution = {
            'input': [f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                        f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii'],
            'left_hemisphere': [f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/left_hemi_casimiro_fakespm8.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/left_hemi_casimiro_fakespm8.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/left_hemi_casimiro_fakespm8.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/left_hemi_aleksander_fakespm8.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/left_hemi_aleksander_fakespm8.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_none.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_aims.nii',
                                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/left_hemi_aleksander_fakespm8.nii'],
            'nobias': [f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/casimiro_fakespm8.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/casimiro_fakespm8.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/casimiro_fakespm8.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/aleksander_fakespm8.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/aleksander_fakespm8.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_none.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_aims.nii',
                        f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/aleksander_fakespm8.nii'],
            'normalization': ['none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8',
                                'none',
                                'aims',
                                'fakespm8'],
            'right_hemisphere': [f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/default_analysis/right_hemi_casimiro_fakespm8.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/default_analysis/right_hemi_casimiro_fakespm8.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/default_analysis/right_hemi_casimiro_fakespm8.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/default_analysis/right_hemi_aleksander_fakespm8.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/default_analysis/right_hemi_aleksander_fakespm8.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_none.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_aims.nii',
                                    f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/default_analysis/right_hemi_aleksander_fakespm8.nii']
        }

        morphologist_iteration = self.capsul.iteration_pipeline(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist',
            non_iterative_plugs=['template'],
        )
        
        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        count = 0
        inputs = []
        normalizations = []
        for path in self.capsul.config.local.dataset.input.find(suffix='T1w', extension='nii'):
            inputs.extend([str(path)]*3)
            normalizations += ['none', 'aims', 'fakespm8']
        # Set the input data
        morphologist_iteration.input = inputs
        morphologist_iteration.normalization = normalizations
        morphologist_iteration.metadata_schema = {
            'brainvisa': {
                '*': {
                    'suffix': '!{{executable.normalization[{list_index}]}}',
                }
            }
        }
        engine = self.capsul.engine()
        execution_context = engine.execution_context(morphologist_iteration)
        generate_paths(morphologist_iteration, execution_context)
        for name, value in expected_completion.items():
            self.assertEqual(getattr(morphologist_iteration, name), value)
        morphologist_iteration.resolve_paths(execution_context)
        for name, value in expected_resolution.items():
            self.assertEqual(getattr(morphologist_iteration, name), value)
    #     try:
    #         with capsul.engine() as ce:
    #             # Finally execute all the Morphologist instances
    #             execution_id = ce.run(processing_pipeline)
    #     except Exception:
    #         import traceback
    #         traceback.print_exc()

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


def test():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFakeMorphologist)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()

if __name__ == '__main__':
    test()
