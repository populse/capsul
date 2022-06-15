# -*- coding: utf-8 -*-

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import time

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

Dataset.schemas['shared'] = SharedSchema

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
    'fakespm': {
        'version': '12'
    }
}

class SPM12NormalizationBIDS(ProcessSchema, schema='bids', process_class=normalization_t1_spm12_reinit):
    output = {'part': 'normalized_fakespm12'}

class SPM12NormalizationBrainVISA(ProcessSchema, schema='brainvisa', process_class=normalization_t1_spm12_reinit):
    transformations_information = {'analysis': undefined,
                                   'suffix': 'sn',
                                   'extension': 'mat'},
    normalized_anatomy_data = {'analysis': undefined,
                               'prefix': 'normalized_SPM'},

class SPM12NormalizationShared(ProcessSchema, schema='shared', process_class=normalization_t1_spm12_reinit):
    anatomical_template = {'data_id': 'normalization_template'}


normalization_t1_spm8_reinit.requirements = {
    'fakespm': {
        'version': '8'
    }
}


class SPM8NormalizationBIDS(ProcessSchema, schema='bids', process_class=normalization_t1_spm8_reinit):
    output = {'part': 'normalized_fakespm8'}

class SPM8NormalizationBrainVISA(ProcessSchema, schema='brainvisa', process_class=normalization_t1_spm8_reinit):
    transformations_information = {'analysis': undefined,
                                   'suffix': 'sn',
                                   'extension': 'mat'},
    normalized_anatomy_data = {'analysis': undefined,
                               'prefix': 'normalized_SPM'},

class SPM8NormalizationShared(ProcessSchema, schema='shared', process_class=normalization_t1_spm8_reinit):
    anatomical_template = {'data_id': 'normalization_template'}


class AimsNormalizationBIDS(ProcessSchema, schema='bids', process_class=normalization_aimsmiregister):
    transformation_to_ACPC = {
        'part': 'normalized_aims',
        'extension': 'trm'
    }

class AimsNormalizationBrainVISA(ProcessSchema, schema='brainvisa', process_class=normalization_aimsmiregister):
    transformation_to_ACPC = {
        'prefix': 'normalized_aims',
        'extension': 'trm'
    }

class AimsNormalizationShared(ProcessSchema, schema='shared', process_class=normalization_aimsmiregister):
    anatomical_template = {'data_id': 'normalization_template'}


class FSLNormalizationBrainVISA(ProcessSchema, schema='brainvisa', process_class=Normalization_FSL_reinit):
    transformation_matrix = {
        'analysis': undefined,
        'suffix': 'fsl',
        'extension': 'mat'
    }

class T1BiasCorrectionBIDS(ProcessSchema, schema='bids', process_class=T1BiasCorrection):
    t1mri_nobias = {'part': 'nobias'}

class T1BiasCorrectionBrainVISA(ProcessSchema, schema='brainvisa', process_class=T1BiasCorrection):
    t1mri_nobias = {'prefix': 'nobias'}
    b_field = {'prefix': 'biasfield'}
    hfiltered = {'prefix': 'hfiltered'}
    white_ridges = {'prefix': 'whiteridge'}
    variance = {'prefix': 'variance'}
    edges = {'prefix': 'edges'}
    meancurvature = {'prefix': 'meancurvature'}

class HistoAnalysisBrainVISA(ProcessSchema, schema='brainvisa', process_class=HistoAnalysis):
    histo = {'prefix': 'nobias', 'extension': 'his'}
    histo_analysis = {'prefix': 'nobias', 'extension': 'han'}

class BrainSegmentationBrainVISA(ProcessSchema, schema='brainvisa', process_class=BrainSegmentation):
    _ = {
        '*': {'seg_directory': 'segmentation'}
    }
    brain_mask = {'prefix': 'brain'}

skullstripping.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'skull_stripped': {'prefix': 'skull_stripped'},
    }
)

ScalpMesh.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'head_mask': {'prefix': 'head'},
        'head_mesh': {'seg_directory': 'segmentation/mesh', 'suffix': 'head', 'extension': 'gii'},
    }
)

SplitBrain.metadata_schema = dict(
    bids={'split_brain': {'part': 'split'}},
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'split_brain': {'prefix': 'voronoi'},
    }
)

GreyWhiteClassificationHemi.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'grey_white': {'prefix': 'grey_white'},
    }
)

GreyWhiteTopology.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'hemi_cortex': {'prefix': 'cortex'},
    }
)

GreyWhiteMesh.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation/mesh'},
        'white_mesh': {'suffix': 'white', 'extension': 'gii'},
    }
)

PialMesh.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation/mesh'},
        'pial_mesh': {'suffix': 'hemi', 'extension': 'gii'},
    }
)

SulciSkeleton.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'segmentation'},
        'skeleton': {'prefix': 'skeleton'},
        'roots': {'prefix': 'roots'},
    }
)

SulciGraph.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'graph': {'extension': 'arg', 'sulci_graph_version': '!{executable.graph_version}'},
        'sulci_voronoi': {'prefix': 'sulcivoronoi'},
        'cortex_mid_interface': {'seg_directory': 'segmentation',
                                 'prefix': 'gw_interface'},
    }
)

SulciLabellingANN.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'output_graph': {'suffix': '!{sulci_recognition_session}',
                         'extension': 'arg'},
        'energy_plot_file': {'suffix': '!{sulci_recognition_session}',
                             'extension': 'nrj'},
    }
)

SulciLabellingSPAMGlobal.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'output_graph': {'suffix': '!{sulci_recognition_session}',
                         'extension': 'arg'},
        'posterior_probabilities':
        {
            'suffix': '!{sulci_recognition_session}_proba',
            'extension': 'csv'},
        'output_transformation': {
            'suffix': '!{sulci_recognition_session}_Tal_TO_SPAM',
            'extension': 'trm'},
        'output_t1_to_global_transformation': {
            'suffix': '!{sulci_recognition_session}_T1_TO_SPAM',
            'extension': 'trm'},
    }
)

SulciLabellingSPAMLocal.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'output_graph': {'suffix': '!{sulci_recognition_session}',
                         'extension': 'arg'},
        'posterior_probabilities':
        {
            'suffix': '!{sulci_recognition_session}_proba',
            'extension': 'csv'},
        'output_local_transformations': {
            'suffix': '!{sulci_recognition_session}_global_TO_local',
            'extension': None},
    }
)

SulciLabellingSPAMMarkov.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'output_graph': {'suffix': '!{sulci_recognition_session}',
                         'extension': 'arg'},
        'posterior_probabilities':
        {
            'suffix': '!{sulci_recognition_session}_proba',
            'extension': 'csv'},
    }
)

SulciDeepLabeling.metadata_schema = dict(
    brainvisa={
        '*': {'seg_directory': 'folds'},
        'labeled_graph': {'suffix': '!{sulci_recognition_session}',
                          'extension': 'arg'},
    }
)


Morphologist.metadata_schema = dict(
    bids={
        '*': {'pipeline': 'morphologist'},
        'left_labelled_graph': {'part': 'left_hemi'},
        'right_labelled_graph': {'part': 'right_hemi'},
    },
    brainvisa={
        '*': {'process': None, 'modality': 't1mri'},
        'imported_t1mri': {'analysis': undefined},
        't1mri_referential': {
            'analysis': undefined,
            'seg_directory': 'registration',
            'short_prefix': 'RawT1-',
            'suffix': '!{acquisition}',
            'extension': 'referential'},
        'reoriented_t1mri': {'analysis': undefined},

        'GreyWhiteClassification.*': {'side': 'L'},
        'GreyWhiteTopology.*': {'side': 'L'},
        'GreyWhiteMesh.*': {'sidebis': 'L'},
        'PialMesh.*': {'sidebis': 'L'},
        'SulciSkeleton.*': {'side': 'L'},
        'CorticalFoldsGraph.*': {'side': 'L'},
        'SulciRecognition.*': {'side': 'L'},
        '*_1.*': {'side': 'R'},
        'GreyWhiteMesh_1.*': {'sidebis': 'R', 'side': None},
        'PialMesh_1.*': {'sidebis': 'R', 'side': None},
        'SulciRecognition*.*': {
            'sulci_graph_version':
                '!{pipeline.CorticalFoldsGraph_graph_version}',
            'sulci_recognition_session': 'default_session_auto',
        },

        #'*.*': {'suffix': '!{field}'},

        #'left_labelled_graph': {
            #'seg_directory': 'folds',
            #'sulci_graph_version': '3.1',
            #'sulci_recognition_session': 'default_session_auto',
            #'suffix': 'default_session_auto',
            #'extension': 'arg'},
        #'right_labelled_graph': {
            #'seg_directory': 'folds',
            #'sulci_graph_version': '3.1',
            #'sulci_recognition_session': 'default_session_auto',
            #'suffix': 'default_session_auto',
            #'extension': 'arg'},
        'Talairach_transform': {
            'analysis': undefined,
            'seg_directory': 'registration',
            'short_prefix': 'RawT1-',
            'suffix': '!{acquisition}_TO_Talairach-ACPC',
            'extension': 'trm'},
    },
    shared={
        'PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template': {'data_id': 'normalization_template'},
        'PrepareSubject_Normalization_NormalizeFSL_template': {'data_id': 'normalization_template'},
        'PrepareSubject_Normalization_NormalizeSPM_template': {'data_id': 'normalization_template'},
        'PrepareSubject_Normalization_NormalizeBaladin_template': {'data_id': 'normalization_template'},
        'PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc': {'data_id': 'trans_acpc_to_mni'},
        'PrepareSubject_TalairachFromNormalization_acpc_referential': {'data_id': 'acpc_ref'},
        'Renorm_template':  {'data_id': 'normalization_template'},
        'Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc': {'data_id': 'trans_mni_to_acpc'},
        'PrepareSubject_TalairachFromNormalization_normalized_referential':{'data_id': 'icbm152_ref'},
        'PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized': {'data_id': 'trans_acpc_to_mni'},
        'SplitBrain_split_template': {'data_id': 'hemi_split_template'},
        'sulcal_morphometry_sulci_file': {'data_id': 'sulcal_morphometry_sulci_file'},
        'SulciRecognition_recognition2000_model': {'data_id': 'sulci_ann_recognition_model', 'side': 'L', 'graph_version': '3.1'},
        'SulciRecognition_1_recognition2000_model': {'data_id': 'sulci_ann_recognition_model', 'side': 'R', 'graph_version': '3.1'},
        'SPAM_recognition_labels_translation_map': {'data_id': 'sulci_spam_recognition_labels_trans', 'model_version': '08'},
        'SulciRecognition_SPAM_recognition09_global_recognition_model': {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_global_recognition_model': {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_local_recognition_model': {'data_id': 'sulci_spam_recognition_local_model', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_local_recognition_model': {'data_id': 'sulci_spam_recognition_local_model', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_markovian_recognition_model': {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_markovian_recognition_model': {'data_id': 'sulci_spam_recognition_global_model', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_global_recognition_labels_priors': {'data_id': 'sulci_spam_recognition_global_labels_priors', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors': {'data_id': 'sulci_spam_recognition_global_labels_priors', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_local_recognition_local_referentials': {'data_id': 'sulci_spam_recognition_local_refs', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials': {'data_id': 'sulci_spam_recognition_local_refs', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_local_recognition_direction_priors': {'data_id': 'sulci_spam_recognition_local_dir_priors', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors': {'data_id': 'sulci_spam_recognition_local_dir_priors', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_SPAM_recognition09_local_recognition_angle_priors': {'data_id': 'sulci_spam_recognition_local_angle_priors', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors': {'data_id': 'sulci_spam_recognition_local_angle_priors', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_local_recognition_translation_priors': {'data_id': 'sulci_spam_recognition_local_trans_priors', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors': {'data_id': 'sulci_spam_recognition_local_trans_priors', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model': {'data_id': 'sulci_spam_recognition_markov_rels', 'model_version': '08', 'side': 'L'},
        'SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model': {'data_id': 'sulci_spam_recognition_markov_rels', 'model_version': '08', 'side': 'R'},
        'SulciRecognition_CNN_recognition19_model_file': {'data_id': 'sulci_cnn_recognition_model', 'model_version': '19', 'side': 'L'},
        'SulciRecognition_1_CNN_recognition19_model_file': {'data_id': 'sulci_cnn_recognition_model', 'model_version': '19', 'side': 'R'},
        'SulciRecognition_CNN_recognition19_param_file': {'data_id': 'sulci_cnn_recognition_param', 'model_version': '19', 'side': 'L'},
        'SulciRecognition_1_CNN_recognition19_param_file': {'data_id': 'sulci_cnn_recognition_param', 'model_version': '19', 'side': 'R'},
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
        def clear_values(morphologist):
            for field in morphologist.user_fields(): # noqa: F402
                if field.path_type:
                    value = getattr(morphologist, field.name, undefined)
                    if value in (None, undefined):
                        continue
                    if isinstance(value, list):
                        setattr(morphologist, field.name, [])
                    else:
                        setattr(morphologist, field.name, undefined)

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
            clear_values(morphologist)

            morphologist.t1mri = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii')
            morphologist.select_Talairach = normalization[0]
            morphologist.perform_skull_stripped_renormalization \
                = normalization[1]
            morphologist.Normalization_select_Normalization_pipeline \
                = normalization[2]
            morphologist.spm_normalization_version = normalization[3]
            morphologist.select_sulci_recognition = 'CNN_recognition19' # 'SPAM_recognition09'

            execution_context = engine.execution_context(morphologist)
            # for field in execution_context.dataset.fields():
            #     dataset = getattr(execution_context.dataset, field.name)
            #     print(f'!dataset! {field.name} = {dataset.path} [{dataset.metadata_schema}]')
            # if getattr(execution_context, 'fakespm', undefined) is not undefined:
            #     print('!fakespm dir!', execution_context.fakespm.directory)
            t0 = time.time()
            generate_paths(morphologist, execution_context, datasets=datasets,
                           source_fields=['t1mri'], debug=False)
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
