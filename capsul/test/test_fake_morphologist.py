# -*- coding: utf-8 -*-

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import time
import copy

from soma.controller import Directory, undefined

from capsul.api import Capsul
from capsul.config.configuration import ModuleConfiguration, default_engine_start_workers
from capsul.dataset import ProcessMetadata, ProcessSchema, MetadataSchema, BrainVISASchema


class SharedSchema(MetadataSchema):
    '''Metadata schema for BrainVISA shared dataset
    '''
    schema_name = 'shared'
    data_id: str = ''
    side: str = None
    graph_version: str = None
    model_version: str = None

    def _path_list(self):
        '''
        The path has the following pattern:
        <something>
        '''

        full_side = {'L': 'left', 'R': 'right'}
        path_list = []
        filename = []
        if self.data_id == 'normalization_template':
            path_list = ['anatomical_templates']
            filename.append('MNI152_T1_2mm.nii.gz')
        elif self.data_id == 'trans_mni_to_acpc':
            path_list = ['transformation']
            filename.append('spm_template_novoxels_TO_talairach.trm')
        elif self.data_id == 'acpc_ref':
            path_list = ['registration']
            filename.append('Talairach-AC_PC-Anatomist.referential')
        elif self.data_id == 'trans_acpc_to_mni':
            path_list = ['transformation']
            filename.append('talairach_TO_spm_template_novoxels.trm')
        elif self.data_id == 'icbm152_ref':
            path_list = ['registration']
            filename.append('Talairach-MNI_template-SPM.referential')
        elif self.data_id == 'hemi_split_template':
            path_list = ['hemitemplate']
            filename.append('closedvoronoi.ima')
        elif self.data_id == 'sulcal_morphometry_sulci_file':
            path_list = ['nomenclature', 'translation']
            filename.append('sulci_default_list.json')
        elif self.data_id == 'sulci_spam_recognition_labels_trans':
            path_list = ['nomenclature', 'translation']
            filename.append(f'sulci_model_20{self.model_version}.trl')
        elif self.data_id == 'sulci_ann_recognition_model':
            path_list = ['models', f'models_20{self.model_version}', 'discriminative_models', self.graph_version, f'{self.side}folds_noroots']
            filename.append(f'{self.side}folds_noroots.arg')
        elif self.data_id == 'sulci_spam_recognition_global_model':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'global_registered_spam_{full_side[self.side]}']
            filename.append('spam_distribs.dat')
        elif self.data_id == 'sulci_spam_recognition_local_model':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename.append('spam_distribs.dat')
        elif self.data_id == 'sulci_spam_recognition_global_labels_priors':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'labels_priors',
                f'frequency_segments_priors_{full_side[self.side]}']
            filename.append('frequency_segments_priors.dat')
        elif self.data_id == 'sulci_spam_recognition_local_refs':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename.append('local_referentials.dat')
        elif self.data_id == 'sulci_spam_recognition_local_dir_priors':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename.append('bingham_direction_trm_priors.dat')
        elif self.data_id == 'sulci_spam_recognition_local_angle_priors':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename.append('vonmises_angle_trm_priors.dat')
        elif self.data_id == 'sulci_spam_recognition_local_trans_priors':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename.append('gaussian_translation_trm_priors.dat')
        elif self.data_id == 'sulci_spam_recognition_markov_rels':
            path_list = [
                'models', f'models_20{self.model_version}', 'descriptive_models', 'segments_relations',
                f'mindist_relations_{full_side[self.side]}']
            filename.append('gamma_exponential_mixture_distribs.dat')
        elif self.data_id == 'sulci_cnn_recognition_model':
            path_list = [
                'models', f'models_20{self.model_version}', 'cnn_models']
            filename.append(f'sulci_unet_model_{full_side[self.side]}.mdsm')
        elif self.data_id == 'sulci_cnn_recognition_param':
            path_list = [
                'models', f'models_20{self.model_version}', 'cnn_models']
            filename.append(f'sulci_unet_model_params_{full_side[self.side]}.mdsm')
        else:
            filename.append(self.data_id)
        path_list.append(''.join(filename))
        return path_list

#Dataset.schemas['shared'] = SharedSchema

# patch processes to setup their requirements and schemas

from capsul.pipeline.test.fake_morphologist.morphologist \
    import Morphologist
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm12_reinit \
    import normalization_t1_spm12_reinit
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm8_reinit \
    import normalization_t1_spm8_reinit
from capsul.pipeline.test.fake_morphologist.normalization_aimsmiregister \
    import normalization_aimsmiregister
from capsul.pipeline.test.fake_morphologist.normalization_fsl_reinit \
    import Normalization_FSL_reinit
from capsul.pipeline.test.fake_morphologist.t1biascorrection \
    import T1BiasCorrection
from capsul.pipeline.test.fake_morphologist.histoanalysis \
    import HistoAnalysis
from capsul.pipeline.test.fake_morphologist.brainsegmentation \
    import BrainSegmentation
from capsul.pipeline.test.fake_morphologist.skullstripping \
    import skullstripping
from capsul.pipeline.test.fake_morphologist.scalpmesh \
    import ScalpMesh
from capsul.pipeline.test.fake_morphologist.splitbrain \
    import SplitBrain
from capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi \
    import GreyWhiteClassificationHemi
from capsul.pipeline.test.fake_morphologist.greywhitetopology \
    import GreyWhiteTopology
from capsul.pipeline.test.fake_morphologist.greywhitemesh \
    import GreyWhiteMesh
from capsul.pipeline.test.fake_morphologist.pialmesh \
    import PialMesh
from capsul.pipeline.test.fake_morphologist.sulciskeleton \
    import SulciSkeleton
from capsul.pipeline.test.fake_morphologist.sulcigraph \
    import SulciGraph
from capsul.pipeline.test.fake_morphologist.sulcilabellingann \
    import SulciLabellingANN
from capsul.pipeline.test.fake_morphologist.sulcilabellingspamglobal \
    import SulciLabellingSPAMGlobal
from capsul.pipeline.test.fake_morphologist.sulcilabellingspamlocal \
    import SulciLabellingSPAMLocal
from capsul.pipeline.test.fake_morphologist.sulcilabellingspammarkov \
    import SulciLabellingSPAMMarkov
from capsul.pipeline.test.fake_morphologist.sulcideeplabeling \
    import SulciDeepLabeling


normalization_t1_spm12_reinit.requirements = {
    'spm': {
        'version': '12'
    }
}

class SPM12NormalizationBIDS(ProcessSchema, schema='bids', process=normalization_t1_spm12_reinit):
    output = {'part': 'normalized_spm12'}

class SPM12NormalizationBrainVISA(ProcessSchema, schema='brainvisa', process=normalization_t1_spm12_reinit):
    transformations_information = {'analysis': undefined,
                                   'suffix': 'sn',
                                   'extension': 'mat'}
    normalized_anatomy_data = {'analysis': undefined,
                               'prefix': 'normalized_SPM'}

class SPM12NormalizationShared(ProcessSchema, schema='shared', process=normalization_t1_spm12_reinit):
    anatomical_template = {'data_id': 'normalization_template'}


normalization_t1_spm8_reinit.requirements = {
    'spm': {
        'version': '8'
    }
}


class SPM8NormalizationBIDS(ProcessSchema, schema='bids', process=normalization_t1_spm8_reinit):
    output = {'part': 'normalized_spm8'}

class SPM8NormalizationBrainVISA(ProcessSchema, schema='brainvisa', process=normalization_t1_spm8_reinit):
    transformations_information = {'analysis': undefined,
                                   'suffix': 'sn',
                                   'extension': 'mat'}
    normalized_anatomy_data = {'analysis': undefined,
                               'prefix': 'normalized_SPM'}

class SPM8NormalizationShared(ProcessSchema, schema='shared', process=normalization_t1_spm8_reinit):
    anatomical_template = {'data_id': 'normalization_template'}


class AimsNormalizationBIDS(ProcessSchema, schema='bids', process=normalization_aimsmiregister):
    transformation_to_ACPC = {
        'part': 'normalized_aims',
        'extension': 'trm'
    }

class AimsNormalizationBrainVISA(ProcessSchema, schema='brainvisa', process=normalization_aimsmiregister):
    transformation_to_ACPC = {
        'prefix': 'normalized_aims',
        'extension': 'trm'
    }

class AimsNormalizationShared(ProcessSchema, schema='shared', process=normalization_aimsmiregister):
    anatomical_template = {'data_id': 'normalization_template'}


class FSLNormalizationBrainVISA(ProcessSchema, schema='brainvisa', process=Normalization_FSL_reinit):
    transformation_matrix = {
        'analysis': undefined,
        'suffix': 'fsl',
        'extension': 'mat'
    }

class T1BiasCorrectionBIDS(ProcessSchema, schema='bids', process=T1BiasCorrection):
    t1mri_nobias = {'part': 'nobias'}

class T1BiasCorrectionBrainVISA(ProcessSchema, schema='brainvisa', process=T1BiasCorrection):
    t1mri_nobias = {'prefix': 'nobias'}
    b_field = {'prefix': 'biasfield'}
    hfiltered = {'prefix': 'hfiltered'}
    white_ridges = {'prefix': 'whiteridge'}
    variance = {'prefix': 'variance'}
    edges = {'prefix': 'edges'}
    meancurvature = {'prefix': 'meancurvature'}

class HistoAnalysisBrainVISA(ProcessSchema, schema='brainvisa', process=HistoAnalysis):
    histo = {'prefix': 'nobias', 'extension': 'his'}
    histo_analysis = {'prefix': 'nobias', 'extension': 'han'}

class BrainSegmentationBrainVISA(ProcessSchema, schema='brainvisa',
                                 process=BrainSegmentation):
    _ = {
        '*': {'seg_directory': 'segmentation'}
    }
    brain_mask = {'prefix': 'brain'}


class skullstrippingBrainVISA(ProcessSchema, schema='brainvisa',
                              process=skullstripping):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    skull_stripped = {'prefix': 'skull_stripped'}


class ScalpMeshBrainVISA(ProcessSchema, schema='brainvisa', process=ScalpMesh):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    head_mask = {'prefix': 'head'}
    head_mesh = {'seg_directory': 'segmentation/mesh', 'suffix': 'head',
                 'extension': 'gii'}


class SplitBrainBIDS(ProcessSchema, schema='bids', process=SplitBrain):
    split_brain = {'part': 'split'}


class SplitBrainBrainVISA(ProcessSchema, schema='brainvisa',
                          process=SplitBrain):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    split_brain = {'prefix': 'voronoi'}


class GreyWhiteClassificationHemiBrainVISA(
    ProcessSchema, schema='brainvisa', process=GreyWhiteClassificationHemi):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    grey_white = {'prefix': 'grey_white'}


class GreyWhiteTopologyBrainVISA(ProcessSchema, schema='brainvisa',
                                 process=GreyWhiteTopology):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    hemi_cortex = {'prefix': 'cortex'}


class GreyWhiteMeshBrainVISA(ProcessSchema, schema='brainvisa',
                             process=GreyWhiteMesh):
    _ = {
        '*': {'seg_directory': 'segmentation/mesh'},
    }
    white_mesh = {'suffix': 'white', 'extension': 'gii'}


class PialMeshBrainVISA(ProcessSchema, schema='brainvisa', process=PialMesh):
    _ = {
        '*': {'seg_directory': 'segmentation/mesh'},
    }
    pial_mesh = {'suffix': 'hemi', 'extension': 'gii'}


class SulciSkeletonBrainVISA(ProcessSchema, schema='brainvisa',
                             process=SulciSkeleton):
    _ = {
        '*': {'seg_directory': 'segmentation'},
    }
    skeleton = {'prefix': 'skeleton'}
    roots = {'prefix': 'roots'}


class SulciGraphBrainVISA(ProcessSchema, schema='brainvisa',
                          process=SulciGraph):
    _ = {
        '*': {'seg_directory': 'folds'},
    }
    graph = {'extension': 'arg',
             'sulci_graph_version': lambda **kwargs:
                f'{kwargs["process"].CorticalFoldsGraph_graph_version}'}
    sulci_voronoi = {'prefix': 'sulcivoronoi'}
    cortex_mid_interface = {'seg_directory': 'segmentation',
                            'prefix': 'gw_interface'}


class SulciLabellingANNBrainVISA(ProcessSchema, schema='brainvisa', process=SulciLabellingANN):
    _ = {
        '*': {'seg_directory': 'folds'},
    }
    output_graph = {'suffix': lambda **kwargs:
                        f'{kwargs["metadata"].sulci_recognition_session}',
                    'extension': 'arg'}
    energy_plot_file = {'suffix': lambda **kwargs:
                            f'{kwargs["metadata"].sulci_recognition_session}',
                        'extension': 'nrj'}


class SulciLabellingSPAMGlobalBrainVISA(ProcessSchema, schema='brainvisa',
                                        process=SulciLabellingSPAMGlobal):
    _ = {
        '*': {'seg_directory': 'folds'},
    }
    output_graph = {'suffix': lambda **kwargs:
                        f'{kwargs["metadata"].sulci_recognition_session}',
                    'extension': 'arg'}
    posterior_probabilities = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_proba',
        'extension': 'csv'}
    output_transformation = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_Tal_TO_SPAM',
        'extension': 'trm'}
    output_t1_to_global_transformation = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_T1_TO_SPAM',
        'extension': 'trm'}


class SulciLabellingSPAMLocalBrainVISA(ProcessSchema, schema='brainvisa',
                                       process=SulciLabellingSPAMLocal):
    _ = {
        '*': {'seg_directory': 'folds'},
    }
    output_graph = {'suffix': lambda **kwargs:
                        f'{kwargs["metadata"].sulci_recognition_session}',
                    'extension': 'arg'}
    posterior_probabilities = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_proba',
        'extension': 'csv'}
    output_local_transformations = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_global_TO_local',
        'extension': None}


class SulciLabellingSPAMMarkovBrainVISA(ProcessSchema, schema='brainvisa',
                                        process=SulciLabellingSPAMMarkov):
    _ = {
        '*': {'seg_directory': 'folds'},
    }
    output_graph = {'suffix': lambda **kwargs:
                        f'{kwargs["metadata"].sulci_recognition_session}',
                    'extension': 'arg'}
    posterior_probabilities = {
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].sulci_recognition_session}_proba',
        'extension': 'csv'}


class SulciDeepLabelingBrainVISA(ProcessSchema, schema='brainvisa',
                                 process=SulciDeepLabeling):
    _ = {
        '*': {'seg_directory': 'folds'}}

    labeled_graph = {'suffix':
                        lambda **kwargs:
                            f'{kwargs["metadata"].sulci_recognition_session}',
                     'extension': 'arg'}


class MorphologistBIDS(ProcessSchema, schema='bids', process=Morphologist):
    _ = {
        '*': {'process': 'morphologist'},
    }
    left_labelled_graph = {'part': 'left_hemi'}
    right_labelled_graph = {'part': 'right_hemi'}


class MorphologistBrainVISA(ProcessSchema, schema='brainvisa',
                            process=Morphologist):
    _ = {
        '*': {'process': None, 'modality': 't1mri'},
    }

    _nodes = {
        'GreyWhiteClassification': {'*': {'side': 'L'}},
        'GreyWhiteTopology': {'*': {'side': 'L'}},
        'GreyWhiteMesh' : {'*': {'sidebis': 'L'}},
        'PialMesh': {'*': {'sidebis': 'L'}},
        'SulciSkeleton': {'*': {'side': 'L'}},
        'CorticalFoldsGraph': {'*': {'side': 'L'}},
        'SulciRecognition': {'*': {'side': 'L'}},
        '*_1': {'*': {'side': 'R'}},
        'GreyWhiteMesh_1': {'*': {'sidebis': 'R', 'side': None}},
        'PialMesh_1': {'*': {'sidebis': 'R', 'side': None}},
        'SulciRecognition*': {'*': {
            'sulci_graph_version':
                lambda **kwargs:
                    f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
            'sulci_recognition_session': 'default_session_auto',
            'prefix': None,
            'sidebis': None,
        }},
    }
    imported_t1mri = {
        'analysis': undefined,
        'side': None,
        'sidebis': None,
        'seg_directory': None,
        'suffix': None,
        'extension': 'nii',
    }
    t1mri_nobias = {
        'side': None,
        'sidebis': None,
        'seg_directory': None,
        'suffix': None,
        'extension': 'nii',
    }
    t1mri_referential= {
        'analysis': undefined,
        'seg_directory': 'registration',
        'short_prefix': 'RawT1-',
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].acquisition}',
        'extension': 'referential'}
    Talairach_transform = {
        'analysis': undefined,
        'seg_directory': 'registration',
        'prefix': '',
        'short_prefix': 'RawT1-',
        'suffix': lambda **kwargs:
            f'{kwargs["metadata"].acquisition}_TO_Talairach-ACPC',
        'side': None,
        'sidebis': None,
        'extension': 'trm'}
    left_labelled_graph = {
        'part': 'left_hemi'
    }
    right_labelled_graph = {
        'part': 'right_hemi'
    }


class MorphologistShared(ProcessSchema, schema='shared', process=Morphologist):
    PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template = {'data_id': 'normalization_template'}
    PrepareSubject_Normalization_NormalizeFSL_template = {'data_id': 'normalization_template'}
    PrepareSubject_Normalization_NormalizeSPM_template = {'data_id': 'normalization_template'}
    PrepareSubject_Normalization_NormalizeBaladin_template = {'data_id': 'normalization_template'}
    PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {'data_id': 'trans_acpc_to_mni'}
    PrepareSubject_TalairachFromNormalization_acpc_referential = {'data_id': 'acpc_ref'}
    Renorm_template =  {'data_id': 'normalization_template'}
    Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {'data_id': 'trans_mni_to_acpc'}
    PrepareSubject_TalairachFromNormalization_normalized_referential = {'data_id': 'icbm152_ref'}
    PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized = {'data_id': 'trans_acpc_to_mni'}
    SplitBrain_split_template = {'data_id': 'hemi_split_template'}
    sulcal_morphometry_sulci_file = {'data_id': 'sulcal_morphometry_sulci_file'}
    SulciRecognition_recognition2000_model = {'data_id': 'sulci_ann_recognition_model', 'side': 'L', 'graph_version': '3.1'}
    SulciRecognition_1_recognition2000_model = {'data_id': 'sulci_ann_recognition_model', 'side': 'R', 'graph_version': '3.1'}
    SPAM_recognition_labels_translation_map = {'data_id': 'sulci_spam_recognition_labels_trans', 'model_version': '08'}
    SulciRecognition_SPAM_recognition09_global_recognition_model = {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_global_recognition_model = {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_local_recognition_model = {'data_id': 'sulci_spam_recognition_local_model', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_local_recognition_model = {'data_id': 'sulci_spam_recognition_local_model', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_markovian_recognition_model = {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_markovian_recognition_model = {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_global_recognition_labels_priors = {'data_id': 'sulci_spam_recognition_global_labels_priors', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors = {'data_id': 'sulci_spam_recognition_global_labels_priors', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_local_recognition_local_referentials = {'data_id': 'sulci_spam_recognition_local_refs', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials = {'data_id': 'sulci_spam_recognition_local_refs', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_local_recognition_direction_priors = {'data_id': 'sulci_spam_recognition_local_dir_priors', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors = {'data_id': 'sulci_spam_recognition_local_dir_priors', 'model_version': '08', 'side': 'L'}
    SulciRecognition_SPAM_recognition09_local_recognition_angle_priors = {'data_id': 'sulci_spam_recognition_local_angle_priors', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors = {'data_id': 'sulci_spam_recognition_local_angle_priors', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_local_recognition_translation_priors = {'data_id': 'sulci_spam_recognition_local_trans_priors', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors = {'data_id': 'sulci_spam_recognition_local_trans_priors', 'model_version': '08', 'side': 'R'}
    SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model = {'data_id': 'sulci_spam_recognition_markov_rels', 'model_version': '08', 'side': 'L'}
    SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model = {'data_id': 'sulci_spam_recognition_markov_rels', 'model_version': '08', 'side': 'R'}
    SulciRecognition_CNN_recognition19_model_file = {'data_id': 'sulci_cnn_recognition_model', 'model_version': '19', 'side': 'L'}
    SulciRecognition_1_CNN_recognition19_model_file = {'data_id': 'sulci_cnn_recognition_model', 'model_version': '19', 'side': 'R'}
    SulciRecognition_CNN_recognition19_param_file = {'data_id': 'sulci_cnn_recognition_param', 'model_version': '19', 'side': 'L'}
    SulciRecognition_1_CNN_recognition19_param_file = {'data_id': 'sulci_cnn_recognition_param', 'model_version': '19', 'side': 'R'}


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
            'builtin': {
                #'config_modules': [
                    #'spm',
                #],
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
                'standalone': True,
            }
            config['builtin'].setdefault('spm', {})[
                f'spm_{version}_standalone'] = fakespm_config

        matlab_config = {
            'mcr_directory': str(tmp / 'software' / 'matlab'),
        }
        config['builtin'].setdefault('matlab', {})['matlab'] = matlab_config

        # Create a configuration file
        self.config_file = tmp / 'capsul_config.json'
        with self.config_file.open('w') as f:
            json.dump(config, f)

        Capsul.delete_singleton()
        self.capsul = Capsul('test_fake_morphologist',
                             site_file=self.config_file, user_file=None)
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
            'databases': {
                'builtin': {
                    'path': '/tmp/capsul_engine_database.rdb',
                    'type': 'redis+socket'
                }
            },

            'builtin': {
                'database': 'builtin',
                'start_workers': default_engine_start_workers,
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
                'spm': {
                    'spm_12_standalone': {
                        'directory': str(self.tmp / 'software' / 'fakespm-12'),
                        'version': '12',
                        'standalone': True,
                    },
                    'spm_8_standalone': {
                        'directory': str(self.tmp / 'software' / 'fakespm-8'),
                        'version': '8',
                        'standalone': True,
                    }
                },
                'matlab': {
                    'matlab': {
                        'mcr_directory': str(self.tmp / 'software' / 'matlab'),
                    },
                },
                #'config_modules': ['capsul.test.test_fake_morphologist'],
            }
        }
        print('\nconfig:', self.capsul.config.asdict(), '\n')
        self.assertEqual(self.capsul.config.asdict(), expected_config)

        engine = self.capsul.engine()
        morphologist = self.capsul.executable(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')

        morphologist.select_Talairach = 'StandardACPC'
        morphologist.perform_skull_stripped_renormalization = 'initial'
        
        context = engine.execution_context(morphologist)
        expected_context = {
            #'config_modules': ['capsul.test.test_fake_morphologist'],
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
        ds_context = {'dataset': dict_context['dataset']}
        #print('requirements:')
        #print(engine.executable_requirements(morphologist))
        self.assertEqual(dict_context, expected_context)
        # spms = list(expected_config['builtin']['spm'].values())
        # self.assertTrue(dict_context['spm'] in spms)

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
            'directory': str(self.tmp / 'software' / 'fakespm-12'),
            'version': '12',
            'standalone': True,
        }
        matlab_conf = {
            'mcr_directory': str(self.tmp / 'software' / 'matlab'),
        }
        expected_context['spm'] = fakespm12_conf
        expected_context['matlab'] = matlab_conf
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

        morphologist_iteration = self.capsul.executable_iteration(
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
        expected_context['spm'] = fakespm12_conf
        expected_context['matlab'] = matlab_conf
        context = engine.execution_context(morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

    def clear_values(self, morphologist):
        for field in morphologist.user_fields(): # noqa: F402
            if field.path_type:
                value = getattr(morphologist, field.name, undefined)
                if value in (None, undefined):
                    continue
                if isinstance(value, list):
                    setattr(morphologist, field.name, [])
                else:
                    setattr(morphologist, field.name, undefined)

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

        morphologist = self.capsul.executable(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')
        self.clear_values(morphologist)

        execution_context = engine.execution_context(morphologist)

        input = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/
                    'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')
        input_metadata \
            = execution_context.dataset['input'].schema.metadata(input)
        self.assertEqual(input_metadata, {
            'folder': 'rawdata',
            'sub': 'aleksander',
            'ses': 'm0',
            'data_type': 'anat',
            'suffix': 'T1w',
            'extension': 'nii',
            'session_metadata': 'session metadata for sub-aleksander_ses-m0_T2w.nii',
            'scan_metadata': 'scan metadata for sub-aleksander_ses-m0_T1w.nii',
            'json_metadata': 'JSON metadata for sub-aleksander_ses-m0_T1w.nii'})

        expected_params_per_schema = {
            'brainvisa': [
                'imported_t1mri', 'commissure_coordinates',
                'Talairach_transform', 't1mri_nobias',
                'histo_analysis',
                'BrainSegmentation_brain_mask',
                'split_brain',
                'HeadMesh_head_mesh',
                'GreyWhiteClassification_grey_white',
                'GreyWhiteClassification_1_grey_white',
                'GreyWhiteTopology_hemi_cortex',
                'GreyWhiteTopology_1_hemi_cortex',
                'GreyWhiteMesh_white_mesh',
                'GreyWhiteMesh_1_white_mesh',
                'SulciSkeleton_skeleton',
                'SulciSkeleton_1_skeleton',
                'PialMesh_pial_mesh',
                'PialMesh_1_pial_mesh',
                'left_graph',
                'right_graph',
                'left_labelled_graph',
                'right_labelled_graph',
                'sulcal_morpho_measures',
                't1mri_referential',
                'reoriented_t1mri',
                'normalization_fsl_native_transformation_pass1',
                'normalization_fsl_native_transformation',
                'normalization_baladin_native_transformation_pass1',
                'normalization_baladin_native_transformation',
                'normalized_t1mri',
                'MNI_transform',
                'normalization_spm_native_transformation',
                'normalization_spm_native_transformation_pass1',
                'BiasCorrection_b_field',
                'BiasCorrection_hfiltered',
                'BiasCorrection_white_ridges',
                'BiasCorrection_variance',
                'BiasCorrection_edges',
                'BiasCorrection_meancurvature',
                'HistoAnalysis_histo',
                'Renorm_skull_stripped',
                'HeadMesh_head_mask',
                'SulciSkeleton_roots',
                'CorticalFoldsGraph_sulci_voronoi',
                'CorticalFoldsGraph_cortex_mid_interface',
                'SulciRecognition_recognition2000_energy_plot_file',
                'SulciRecognition_SPAM_recognition09_global_recognition_posterior_probabilities',
                'SulciRecognition_SPAM_recognition09_global_recognition_output_transformation',
                'SulciRecognition_SPAM_recognition09_global_recognition_output_t1_to_global_transformation',
                'SulciRecognition_SPAM_recognition09_local_recognition_posterior_probabilities',
                'SulciRecognition_SPAM_recognition09_local_recognition_output_local_transformations',
                'SulciRecognition_SPAM_recognition09_markovian_recognition_posterior_probabilities',
                'SulciSkeleton_1_roots',
                'CorticalFoldsGraph_1_sulci_voronoi',
                'CorticalFoldsGraph_1_cortex_mid_interface',
                'SulciRecognition_1_recognition2000_energy_plot_file',
                'SulciRecognition_1_SPAM_recognition09_global_recognition_posterior_probabilities',
                'SulciRecognition_1_SPAM_recognition09_global_recognition_output_transformation',
                'SulciRecognition_1_SPAM_recognition09_global_recognition_output_t1_to_global_transformation',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_posterior_probabilities',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_output_local_transformations',
                'SulciRecognition_1_SPAM_recognition09_markovian_recognition_posterior_probabilities',
            ],
            'bids': ['t1mri'],
            'shared': [
                'PrepareSubject_TalairachFromNormalization_normalized_referential',
                'PrepareSubject_TalairachFromNormalization_acpc_referential',
                'PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized',
                'SPAM_recognition_labels_translation_map',
                'sulcal_morphometry_sulci_file',
                'PrepareSubject_Normalization_NormalizeFSL_template',
                'PrepareSubject_Normalization_NormalizeSPM_template',
                'PrepareSubject_Normalization_NormalizeBaladin_template',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template',
                'PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc',
                'Renorm_template',
                'Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc',
                'SplitBrain_split_template',
                'SulciRecognition_recognition2000_model',
                'SulciRecognition_SPAM_recognition09_global_recognition_labels_priors',
                'SulciRecognition_SPAM_recognition09_global_recognition_model',
                'SulciRecognition_SPAM_recognition09_local_recognition_model',
                'SulciRecognition_SPAM_recognition09_local_recognition_local_referentials',
                'SulciRecognition_SPAM_recognition09_local_recognition_direction_priors',
                'SulciRecognition_SPAM_recognition09_local_recognition_angle_priors',
                'SulciRecognition_SPAM_recognition09_local_recognition_translation_priors',
                'SulciRecognition_SPAM_recognition09_markovian_recognition_model',
                'SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model',
                'SulciRecognition_CNN_recognition19_model_file',
                'SulciRecognition_CNN_recognition19_param_file',
                'SulciRecognition_1_recognition2000_model',
                'SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors',
                'SulciRecognition_1_SPAM_recognition09_global_recognition_model',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_model',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors',
                'SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors',
                'SulciRecognition_1_SPAM_recognition09_markovian_recognition_model',
                'SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model',
                'SulciRecognition_1_CNN_recognition19_model_file',
                'SulciRecognition_1_CNN_recognition19_param_file'
            ],
        }

        # iterate manually
        count = -1
        for it, normalization in enumerate(zip(sel_tal, renorm, norm,
                                               normspm)):
            count += 1
            #morphologist.t1mri = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')
            morphologist.select_Talairach = normalization[0]
            morphologist.perform_skull_stripped_renormalization \
                = normalization[1]
            morphologist.Normalization_select_Normalization_pipeline \
                = normalization[2]
            morphologist.spm_normalization_version = normalization[3]
            morphologist.select_sulci_recognition = 'CNN_recognition19' # 'SPAM_recognition09'

            metadata = ProcessMetadata(morphologist, execution_context,
                                       datasets=datasets)

            expected_sch = expected_params_per_schema
            expected_sch['brainvisa'] = sorted(expected_sch['brainvisa'])

            got_sch = dict(metadata.parameters_per_schema)
            got_sch['brainvisa'] = sorted(got_sch['brainvisa'])

            self.maxDiff = None
            self.assertEqual(got_sch, expected_sch)

            metadata.bids = input_metadata
            self.assertEqual(
                metadata.bids.asdict(),
                {
                    'folder': 'rawdata',
                    'process': None,
                    'sub': 'aleksander',
                    'ses': 'm0',
                    'data_type': 'anat',
                    'task': None,
                    'acq': None,
                    'ce': None,
                    'rec': None,
                    'run': None,
                    'echo': None,
                    'part': None,
                    'suffix': 'T1w',
                    'extension': 'nii'
                })

            t0 = time.time()
            metadata.generate_paths(morphologist)
            t1 = time.time()
            print('completion time:', t1 - t0, 's')

            debug = False
            if debug:
                from soma.qt_gui.qt_backend import Qt
                from capsul.qt_gui.widgets.pipeline_developer_view import PipelineDeveloperView

                app = Qt.QApplication.instance()
                if app is None:
                    app = Qt.QApplication([])
                pv = PipelineDeveloperView(morphologist, allow_open_controller=True, enable_edition=True, show_sub_pipelines=True)
                pv.show()
                app.exec_()

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

            # run it
            #with self.capsul.engine() as engine:
                #status = engine.run(morphologist)
            #print('run status:', status)
            #self.assertEqual(
                #status,
                #{'status': 'ended', 'error': None, 'error_detail': None,
                 #'engine_output': ''})


    def test_fake_morphologist_iteration(self):
        expected_completion = {
            't1mri': [
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                '!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
            ],
            'left_labelled_graph': [
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
            ],
            't1mri_nobias': [
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/nobias_aleksander.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/nobias_casimiro.nii',
            ],
            'Normalization_select_Normalization_pipeline': [
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
            ],
            'right_labelled_graph': [
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                '!{dataset.output.path}/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
            ],
        }

        expected_resolution = {
            't1mri': [
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
                f'{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii',
            ],
            'left_labelled_graph': [
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg',
            ],
            't1mri_nobias': [
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/nobias_aleksander.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/nobias_casimiro.nii',
            ],
            'Normalization_select_Normalization_pipeline': [
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM',
            ],
            'right_labelled_graph': [
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
                f'{self.tmp}/brainvisa/whaterver/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg',
            ],
        }

        morphologist_iteration = self.capsul.executable_iteration(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist',
            non_iterative_plugs=['template'],
        )
        
        self.clear_values(morphologist_iteration)
        self.clear_values(morphologist_iteration.process)

        #class MorphologistIterationBrainVISA(ProcessSchema, schema='brainvisa',
                                             #process=morphologist_iteration):
            #_ = {
                #'*': {
                    #'suffix': lambda iteration_index, **kwargs: f'{{executable.normalization[{iteration_index}]}}',
                #}
            #}

        engine = self.capsul.engine()
        execution_context = engine.execution_context(morphologist_iteration)

        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        count = 0
        iter_meta_bids = []
        iter_meta_brainvisa = []
        select_Talairach = []
        perform_skull_stripped_renormalization = []
        Normalization_select_Normalization_pipeline = []
        spm_normalization_version = []

        for path in sorted(
                self.capsul.config.builtin.dataset.input.find(suffix='T1w',
                                                            extension='nii')):
            input_metadata \
                = execution_context.dataset['input'].schema.metadata(path)
            iter_meta_bids.extend([input_metadata]*3)
            select_Talairach += ['StandardACPC', 'Normalization',
                                 'Normalization']
            perform_skull_stripped_renormalization += [
                'initial', 'skull_stripped', 'skull_stripped']
            Normalization_select_Normalization_pipeline += [
                'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM']
            spm_normalization_version += [
                'normalization_t1_spm12_reinit',
                'normalization_t1_spm12_reinit',
                'normalization_t1_spm8_reinit']
            
            for i in range(3):
                brainvisa = BrainVISASchema()
                brainvisa.analysis = f'{select_Talairach[i]}-{Normalization_select_Normalization_pipeline[i]}'
                iter_meta_brainvisa.append(brainvisa)
            

        # Set the input data
        morphologist_iteration.select_Talairach = select_Talairach
        morphologist_iteration.perform_skull_stripped_renormalization \
            = perform_skull_stripped_renormalization
        morphologist_iteration.Normalization_select_Normalization_pipeline \
            = Normalization_select_Normalization_pipeline
        morphologist_iteration.spm_normalization_version \
            = spm_normalization_version

        metadata = ProcessMetadata(morphologist_iteration, execution_context,
                                   datasets=datasets, debug=False)
        metadata.bids = iter_meta_bids
        metadata.brainvisa = iter_meta_brainvisa
        p = self.capsul.executable(
            'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist')
        metadata.generate_paths(morphologist_iteration)
        
        # debug = False
        # if debug:
        #     from soma.qt_gui.qt_backend import Qt
        #     from capsul.qt_gui.widgets.pipeline_developer_view import PipelineDeveloperView

        #     app = Qt.QApplication.instance()
        #     if app is None:
        #         app = Qt.QApplication([])
        #     pv = PipelineDeveloperView(morphologist_iteration, allow_open_controller=True, enable_edition=True, show_sub_pipelines=True)
        #     pv.show()
        #     app.exec_()

        self.maxDiff = None
        for name, value in expected_completion.items():
            # print('test parameter:', name)
            self.assertEqual(getattr(morphologist_iteration, name, undefined),
                             value)
        morphologist_iteration.resolve_paths(execution_context)
        for name, value in expected_resolution.items():
            self.assertEqual(getattr(morphologist_iteration, name, undefined),
                             value)
        
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




def with_iteration(engine):
    morphologist_iteration = Capsul.executable_iteration(
        'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist',
        non_iterative_plugs=['template'],
    )

    execution_context = engine.execution_context(morphologist_iteration)

    # Parse the dataset with BIDS-specific query (here "suffix" is part
    #  of BIDS specification). The object returned contains info for main
    # BIDS fields (sub, ses, acq, etc.)
    count = 0
    iter_meta_bids = []
    select_Talairach = []
    perform_skull_stripped_renormalization = []
    Normalization_select_Normalization_pipeline = []
    spm_normalization_version = []
    analysis = []

    for path in sorted(
            self.capsul.config.builtin.dataset.input.find(suffix='T1w',
                                                        extension='nii')):
        input_metadata \
            = execution_context.dataset['input'].schema.metadata(path)
        iter_meta_bids.extend([input_metadata]*3)
        select_Talairach += ['StandardACPC', 'Normalization',
                            'Normalization']
        perform_skull_stripped_renormalization += [
            'initial', 'skull_stripped', 'skull_stripped']
        Normalization_select_Normalization_pipeline += [
            'NormalizeSPM', 'Normalization_AimsMIRegister', 'NormalizeSPM']
        spm_normalization_version += [
            'normalization_t1_spm12_reinit',
            'normalization_t1_spm12_reinit',
            'normalization_t1_spm8_reinit']
        analysis += ['StandardACPC-NormalizeSPM', 'Normalization-AimsMIRegister', 'Normalization-NormalizeSPM']
    # Set the input data
    morphologist_iteration.select_Talairach = select_Talairach
    morphologist_iteration.perform_skull_stripped_renormalization \
        = perform_skull_stripped_renormalization
    morphologist_iteration.Normalization_select_Normalization_pipeline \
        = Normalization_select_Normalization_pipeline
    morphologist_iteration.spm_normalization_version \
        = spm_normalization_version

    metadata = ProcessMetadata(morphologist_iteration, execution_context,
                               datasets=datasets)
    metadata.bids = iter_meta_bids
    metadata.brainvisa.analysis = analysis
    metadata.generate_paths(morphologist_iteration)

    execution_id = engine.start(morphologist_iteration)
    return execution_id


def without_iteration(engine):    
    select_Talairach=[
        'StandardACPC', 
        'Normalization', 
        'Normalization']
    perform_skull_stripped_renormalization = [
        'initial', 
        'skull_stripped', 
        'skull_stripped']
    Normalization_select_Normalization_pipeline = [
        'NormalizeSPM', 
        'Normalization_AimsMIRegister',
        'NormalizeSPM']
    spm_normalization_version = [
        'normalization_t1_spm12_reinit',
        'normalization_t1_spm12_reinit',
        'normalization_t1_spm8_reinit']

    execution_ids = []
    for path in sorted(
            self.capsul.config.builtin.dataset.input.find(suffix='T1w',
                                                        extension='nii')):
        for i in range(3):
            morphologist = Capsul.executable(
                'capsul.pipeline.test.fake_morphologist.morphologist.Morphologist',
            )
            execution_context = engine.execution_context(morphologist)
            input_metadata \
                = execution_context.dataset['input'].schema.metadata(path)

            # Set the input data
            morphologist.select_Talairach = select_Talairach[i]
            morphologist.perform_skull_stripped_renormalization \
                = perform_skull_stripped_renormalization[i]
            morphologist.Normalization_select_Normalization_pipeline \
                = Normalization_select_Normalization_pipeline[i]
            morphologist.spm_normalization_version \
                = spm_normalization_version[i]

            metadata = ProcessMetadata(morphologist, execution_context,
                                       datasets=datasets)
            metadata.bids = input_metadata
            metadata.generate_paths(morphologist)
            execution_ids.append(engine.start(morphologist))
    return execution_ids

if __name__ == '__main__':
    import sys
    from soma.qt_gui.qt_backend import Qt
    from capsul.web import CapsulBrowserWindow

    qt_app = Qt.QApplication.instance()
    if not qt_app:
        qt_app = Qt.QApplication(sys.argv)
    self = TestFakeMorphologist()
    self.subjects = [f'subject{i:04}' for i in range(20)]
    print(f'Setting up config and data files for {len(self.subjects)}')
    self.setUp()
    try:
        with self.capsul.engine() as engine:
            widget = CapsulBrowserWindow()
            widget.show()
            # import cProfile
            # cProfile.run(
            #     'execution_ids = without_iteration(engine)',
            #     '/tmp/without_iteration')       
            # cProfile.run(
            #     'execution_ids = with_iteration(engine)',
            #     '/tmp/with_iteration')
            start = time.time()
            execution_ids = with_iteration(engine)
            print('Duration:', time.time() - start)
            qt_app.exec_()
            del widget
            for execution_id in execution_ids:
                engine.dispose(execution_id)
    finally:
        self.tearDown()
