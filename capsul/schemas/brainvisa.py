# -*- coding: utf-8 -*-

from capsul.dataset import ProcessSchema, MetadataSchema, Append
from soma.controller import undefined
import importlib


class BrainVISASharedSchema(MetadataSchema):
    '''Metadata schema for BrainVISA shared dataset
    '''
    schema_name = 'brainvisa_shared'
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
        filename = ''
        if self.data_id == 'normalization_template':
            path_list = ['anatomical_templates']
            filename = 'MNI152_T1_2mm.nii.gz'
        elif self.data_id == 'trans_mni_to_acpc':
            path_list = ['transformation']
            filename = 'spm_template_novoxels_TO_talairach.trm'
        elif self.data_id == 'acpc_ref':
            path_list = ['registration']
            filename = 'Talairach-AC_PC-Anatomist.referential'
        elif self.data_id == 'trans_acpc_to_mni':
            path_list = ['transformation']
            filename = 'talairach_TO_spm_template_novoxels.trm'
        elif self.data_id == 'icbm152_ref':
            path_list = ['registration']
            filename = 'Talairach-MNI_template-SPM.referential'
        elif self.data_id == 'hemi_split_template':
            path_list = ['hemitemplate']
            filename = 'closedvoronoi.ima'
        elif self.data_id == 'sulcal_morphometry_sulci_file':
            path_list = ['nomenclature', 'translation']
            filename = 'sulci_default_list.json'
        elif self.data_id == 'sulci_spam_recognition_labels_trans':
            path_list = ['nomenclature', 'translation']
            filename = f'sulci_model_20{self.model_version}.trl'
        elif self.data_id == 'sulci_ann_recognition_model':
            path_list = ['models', f'models_20{self.model_version}',
                         'discriminative_models', self.graph_version,
                         f'{self.side}folds_noroots']
            filename = f'{self.side}folds_noroots.arg'
        elif self.data_id == 'sulci_spam_recognition_global_model':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'global_registered_spam_{full_side[self.side]}']
            filename = 'spam_distribs.dat'
        elif self.data_id == 'sulci_spam_recognition_local_model':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename = 'spam_distribs.dat'
        elif self.data_id == 'sulci_spam_recognition_global_labels_priors':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'labels_priors',
                f'frequency_segments_priors_{full_side[self.side]}']
            filename = 'frequency_segments_priors.dat'
        elif self.data_id == 'sulci_spam_recognition_local_refs':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename = 'local_referentials.dat'
        elif self.data_id == 'sulci_spam_recognition_local_dir_priors':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename = 'bingham_direction_trm_priors.dat'
        elif self.data_id == 'sulci_spam_recognition_local_angle_priors':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename = 'vonmises_angle_trm_priors.dat'
        elif self.data_id == 'sulci_spam_recognition_local_trans_priors':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments',
                f'locally_from_global_registred_spam_{full_side[self.side]}']
            filename = 'gaussian_translation_trm_priors.dat'
        elif self.data_id == 'sulci_spam_recognition_markov_rels':
            path_list = [
                'models', f'models_20{self.model_version}',
                'descriptive_models', 'segments_relations',
                f'mindist_relations_{full_side[self.side]}']
            filename = 'gamma_exponential_mixture_distribs.dat'
        elif self.data_id == 'sulci_cnn_recognition_model':
            path_list = [
                'models', f'models_20{self.model_version}', 'cnn_models']
            filename = f'sulci_unet_model_{full_side[self.side]}.mdsm'
        elif self.data_id == 'sulci_cnn_recognition_param':
            path_list = [
                'models', f'models_20{self.model_version}', 'cnn_models']
            filename = f'sulci_unet_model_params_{full_side[self.side]}.mdsm'
        else:
            filename = self.data_id

        path_list.append(filename)
        return path_list


morphologist_datasets = {
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
    'GlobalMorphometry_subject': 'output',
    'Report_normative_brain_stats': None,
    'Report_subject': 'output',
}
''' standard, shared datasets associated with shared input data for
Morphologist
'''


def declare_morpho_schemas(morpho_module):
    ''' Declares Morphologist and sub-processes completion schemas for
    BIDS, BrainVisa and shared organizations.

    It may apply to the "real" Morphologist pipeline (morphologist.capsul
    parent module), or to the "fake" morphologist test replica
    (capsul.pipeline.test.fake_morphologist parent module)
    '''

    axon_module = morpho_module
    cnn_module = '{}.sulcideeplabeling'.format(morpho_module)
    if morpho_module.startswith('morphologist.'):
        axon_module = '{}.axon'.format(morpho_module)
        cnn_module = 'deepsulci.sulci_labeling.capsul.labeling'

    morphologist = importlib.import_module(
        '{}.morphologist'.format(morpho_module))
    normalization_t1_spm12_reinit = importlib.import_module(
        '{}.normalization_t1_spm12_reinit'.format(axon_module))
    normalization_t1_spm8_reinit = importlib.import_module(
        '{}.normalization_t1_spm8_reinit'.format(axon_module))
    normalization_aimsmiregister = importlib.import_module(
        '{}.normalization_aimsmiregister'.format(axon_module))
    normalization_fsl_reinit = importlib.import_module(
        '{}.normalization_fsl_reinit'.format(axon_module))
    t1biascorrection = importlib.import_module(
        '{}.t1biascorrection'.format(axon_module))
    histoanalysis = importlib.import_module(
        '{}.histoanalysis'.format(axon_module))
    brainsegmentation = importlib.import_module(
        '{}.brainsegmentation'.format(axon_module))
    skullstripping = importlib.import_module(
        '{}.skullstripping'.format(axon_module))
    scalpmesh = importlib.import_module(
        '{}.scalpmesh'.format(axon_module))
    splitbrain = importlib.import_module(
        '{}.splitbrain'.format(axon_module))
    greywhiteclassificationhemi = importlib.import_module(
        '{}.greywhiteclassificationhemi'.format(axon_module))
    greywhitetopology = importlib.import_module(
        '{}.greywhitetopology'.format(axon_module))
    greywhitemesh = importlib.import_module(
        '{}.greywhitemesh'.format(axon_module))
    pialmesh = importlib.import_module(
        '{}.pialmesh'.format(axon_module))
    sulciskeleton = importlib.import_module(
        '{}.sulciskeleton'.format(axon_module))
    sulcigraph = importlib.import_module(
        '{}.sulcigraph'.format(axon_module))
    sulcilabellingann = importlib.import_module(
        '{}.sulcilabellingann'.format(axon_module))
    sulcilabellingspamglobal = importlib.import_module(
        '{}.sulcilabellingspamglobal'.format(axon_module))
    sulcilabellingspamlocal = importlib.import_module(
        '{}.sulcilabellingspamlocal'.format(axon_module))
    sulcilabellingspammarkov = importlib.import_module(
        '{}.sulcilabellingspammarkov'.format(axon_module))
    sulcideeplabeling = importlib.import_module(cnn_module)
    brainvolumes = importlib.import_module(
        '{}.brainvolumes'.format(axon_module))
    morpho_report = importlib.import_module(
        '{}.morpho_report'.format(axon_module))
    sulcigraphmorphometrybysubject = importlib.import_module(
        '{}.sulcigraphmorphometrybysubject'.format(axon_module))

    # patch processes to setup their requirements and schemas

    Morphologist = morphologist.Morphologist
    normalization_t1_spm12_reinit \
        = normalization_t1_spm12_reinit.normalization_t1_spm12_reinit
    normalization_t1_spm8_reinit \
        = normalization_t1_spm8_reinit.normalization_t1_spm8_reinit
    normalization_aimsmiregister \
        = normalization_aimsmiregister.normalization_aimsmiregister
    Normalization_FSL_reinit \
        = normalization_fsl_reinit.Normalization_FSL_reinit
    T1BiasCorrection = t1biascorrection.T1BiasCorrection
    HistoAnalysis = histoanalysis.HistoAnalysis
    BrainSegmentation = brainsegmentation.BrainSegmentation
    skullstripping = skullstripping.skullstripping
    ScalpMesh = scalpmesh.ScalpMesh
    SplitBrain = splitbrain.SplitBrain
    GreyWhiteClassificationHemi \
        = greywhiteclassificationhemi.GreyWhiteClassificationHemi
    GreyWhiteTopology = greywhitetopology.GreyWhiteTopology
    GreyWhiteMesh = greywhitemesh.GreyWhiteMesh
    PialMesh = pialmesh.PialMesh
    SulciSkeleton = sulciskeleton.SulciSkeleton
    SulciGraph = sulcigraph.SulciGraph
    SulciLabellingANN = sulcilabellingann.SulciLabellingANN
    SulciLabellingSPAMGlobal \
        = sulcilabellingspamglobal.SulciLabellingSPAMGlobal
    SulciLabellingSPAMLocal = sulcilabellingspamlocal.SulciLabellingSPAMLocal
    SulciLabellingSPAMMarkov \
        = sulcilabellingspammarkov.SulciLabellingSPAMMarkov
    SulciDeepLabeling = sulcideeplabeling.SulciDeepLabeling
    morpho_report = morpho_report.morpho_report
    brainvolumes = brainvolumes.brainvolumes
    sulcigraphmorphometrybysubject \
        = sulcigraphmorphometrybysubject.sulcigraphmorphometrybysubject

    class MorphologistBIDS(ProcessSchema, schema='bids', process=Morphologist):
        _ = {
            '*': {'process': 'morphologist'},
        }
        left_labelled_graph = {'part': 'left_hemi'}

    class MorphologistBrainVISA(ProcessSchema, schema='brainvisa',
                                process=Morphologist):
        _ = {
            '*': {'process': None, 'modality': 't1mri'},
            '*_pass1': Append('suffix', 'pass1'),
        }

        _nodes = {
            'GreyWhiteClassification': {'*': {'side': 'L'}},
            'GreyWhiteTopology': {'*': {'side': 'L'}},
            'GreyWhiteMesh': {'*': {'sidebis': 'L'}},
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
            '*.ReorientAnatomy': {
                '_meta_links': {
                    'transformation': {
                        '*': [],
                    },
                },
            },
            '*.Convert*normalizationToAIMS': {
                '_meta_links': {
                    '*': {
                        '*': [],
                    },
                },
            },
        }
        imported_t1mri = {
            'analysis': undefined,
            'side': None,
            'sidebis': None,
            'seg_directory': None,
            'suffix': None,
        }
        normalized_t1mri = {
            'seg_directory': None,
            'analysis': undefined,
        }
        normalization_spm_native_transformation = {
            'seg_directory': None,
            'prefix': None
        }
        reoriented_t1mri = {
            'analysis': undefined,
        }
        commissure_coordinates = {
            'seg_directory': None,
            'analysis': undefined,
            'prefix': None,
            'extension': 'APC',
        }
        t1mri_referential = {
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
        MNI_transform = {
            'analysis': undefined,
            'seg_directory': 'registration',
            'prefix': '',
            'short_prefix': 'RawT1-',
            'suffix': lambda **kwargs:
                f'{kwargs["metadata"].acquisition}_TO_Talairach-MNI',
            'side': None,
            'sidebis': None,
            'extension': 'trm'}
        left_graph = {
            'prefix': None,
            'suffix': None,
        }
        right_graph = {
            'prefix': None,
            'suffix': None,
        }
        left_labelled_graph = {
            'side': 'L'
        }
        right_labelled_graph = {
            'side': 'R'
        }
        Report_subject = {'modality': None}
        GlobalMorphometry_subject = {'modality': None}

    class SPM12NormalizationBIDS(ProcessSchema, schema='bids',
                                 process=normalization_t1_spm12_reinit):
        output = {'part': 'normalized_spm12'}

    class SPM12NormalizationBrainVISA(ProcessSchema, schema='brainvisa',
                                      process=normalization_t1_spm12_reinit):
        transformations_informations = {'analysis': undefined,
                                        'suffix': 'sn',
                                        'extension': 'mat'}
        normalized_anatomy_data = {'analysis': undefined,
                                   'prefix': 'normalized_SPM'}

    class SPM12NormalizationShared(ProcessSchema, schema='brainvisa_shared',
                                   process=normalization_t1_spm12_reinit):
        anatomical_template = {'data_id': 'normalization_template'}

    class SPM8NormalizationBIDS(ProcessSchema, schema='bids',
                                process=normalization_t1_spm8_reinit):
        output = {'part': 'normalized_spm8'}

    class SPM8NormalizationBrainVISA(ProcessSchema, schema='brainvisa',
                                     process=normalization_t1_spm8_reinit):
        transformations_informations = {'analysis': undefined,
                                        'suffix': 'sn',
                                        'extension': 'mat'}
        normalized_anatomy_data = {'analysis': undefined,
                                   'prefix': 'normalized_SPM'}

    class SPM8NormalizationShared(ProcessSchema, schema='brainvisa_shared',
                                  process=normalization_t1_spm8_reinit):
        anatomical_template = {'data_id': 'normalization_template'}

    class AimsNormalizationBIDS(ProcessSchema, schema='bids',
                                process=normalization_aimsmiregister):
        transformation_to_ACPC = {
            'part': 'normalized_aims',
            'extension': 'trm'
        }

    class AimsNormalizationBrainVISA(ProcessSchema, schema='brainvisa',
                                     process=normalization_aimsmiregister):
        transformation_to_ACPC = {
            'prefix': 'normalized_aims',
            'extension': 'trm'
        }

    class AimsNormalizationShared(ProcessSchema, schema='brainvisa_shared',
                                  process=normalization_aimsmiregister):
        anatomical_template = {'data_id': 'normalization_template'}

    class FSLNormalizationBrainVISA(ProcessSchema, schema='brainvisa',
                                    process=Normalization_FSL_reinit):
        transformation_matrix = {
            'seg_directory': 'registration',
            'analysis': undefined,
            'suffix': 'fsl',
            'extension': 'mat'
        }
        normalized_anatomy_data = {
            'seg_directory': None,
            'analysis': undefined,
            'prefix': 'normalized_FSL',
            'suffix': None,
        }

    class T1BiasCorrectionBIDS(ProcessSchema, schema='bids',
                               process=T1BiasCorrection):
        t1mri_nobias = {'part': 'nobias'}

    class T1BiasCorrectionBrainVISA(ProcessSchema, schema='brainvisa',
                                    process=T1BiasCorrection):
        _ = {
            '*': {
                'seg_directory': None,
                'analysis': lambda **kwargs:
                    f'{kwargs["initial_meta"].analysis}',
            }
        }
        t1mri_nobias = {'prefix': 'nobias'}
        b_field = {'prefix': 'biasfield'}
        hfiltered = {'prefix': 'hfiltered'}
        white_ridges = {'prefix': 'whiteridge'}
        variance = {'prefix': 'variance'}
        edges = {'prefix': 'edges'}
        meancurvature = {'prefix': 'meancurvature'}

    class HistoAnalysisBrainVISA(ProcessSchema, schema='brainvisa',
                                 process=HistoAnalysis):
        histo = {'prefix': 'nobias', 'extension': 'his'}
        histo_analysis = {'prefix': 'nobias', 'extension': 'han'}

    class BrainSegmentationBrainVISA(ProcessSchema, schema='brainvisa',
                                     process=BrainSegmentation):
        _ = {
            '*': {'seg_directory': 'segmentation'}
        }
        brain_mask = {'prefix': 'brain'}
        _meta_links = {
            'histo_analysis': {
                '*': [],
            }
        }

    class skullstrippingBrainVISA(ProcessSchema, schema='brainvisa',
                                  process=skullstripping):
        _ = {
            '*': {'seg_directory': 'segmentation'},
        }
        skull_stripped = {'prefix': 'skull_stripped'}

    class ScalpMeshBrainVISA(ProcessSchema, schema='brainvisa',
                             process=ScalpMesh):
        _ = {
            '*': {'seg_directory': 'segmentation'},
        }
        head_mask = {'prefix': 'head'}
        head_mesh = {'seg_directory': 'segmentation/mesh', 'suffix': 'head',
                     'prefix': None, 'extension': 'gii'}
        _meta_links = {
            'histo_analysis': {'*': []}
        }

    class SplitBrainBIDS(ProcessSchema, schema='bids', process=SplitBrain):
        split_brain = {'part': 'split'}

    class SplitBrainBrainVISA(ProcessSchema, schema='brainvisa',
                              process=SplitBrain):
        _ = {
            '*': {'seg_directory': 'segmentation'},
        }
        split_brain = {'prefix': 'voronoi',
                       'analysis': lambda **kwargs:
                           f'{kwargs["initial_meta"].analysis}'}
        _meta_links = {
            'histo_analysis': {'*': []}
        }

    class GreyWhiteClassificationHemiBrainVISA(
            ProcessSchema, schema='brainvisa',
            process=GreyWhiteClassificationHemi):
        _ = {
            '*': {'seg_directory': 'segmentation'},
        }
        grey_white = {'prefix': 'grey_white'}
        _meta_links = {
            'histo_analysis': {'*': []}
        }

    class GreyWhiteTopologyBrainVISA(ProcessSchema, schema='brainvisa',
                                     process=GreyWhiteTopology):
        _ = {
            '*': {'seg_directory': 'segmentation'},
        }
        hemi_cortex = {'prefix': 'cortex'}
        _meta_links = {
            'histo_analysis': {'*': []}
        }

    class GreyWhiteMeshBrainVISA(ProcessSchema, schema='brainvisa',
                                 process=GreyWhiteMesh):
        _ = {
            '*': {'seg_directory': 'segmentation/mesh'},
        }
        white_mesh = {'prefix': None, 'suffix': 'white', 'extension': 'gii'}

    class PialMeshBrainVISA(ProcessSchema, schema='brainvisa',
                            process=PialMesh):
        _ = {
            '*': {'seg_directory': 'segmentation/mesh'},
        }
        pial_mesh = {'prefix': None, 'suffix': 'hemi', 'extension': 'gii'}

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
            '*': {'seg_directory': 'folds', 'sidebis': None},
        }
        graph = {'extension': 'arg',
                 'sulci_graph_version': lambda **kwargs:
                     f'{kwargs["process"].CorticalFoldsGraph_graph_version}'}
        sulci_voronoi = {
            'prefix': 'sulcivoronoi',
            'sulci_graph_version': lambda **kwargs:
                f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
        }
        cortex_mid_interface = {'seg_directory': 'segmentation',
                                'prefix': 'gw_interface'}
        _meta_links = {
            '*_mesh': {'*': []},
        }

    class SulciLabellingANNBrainVISA(ProcessSchema, schema='brainvisa',
                                     process=SulciLabellingANN):
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

    class sulcigraphmorphometrybysubject(
            ProcessSchema, schema='brainvisa',
            process=sulcigraphmorphometrybysubject):
        sulcal_morpho_measures = {
            'extension': 'csv',
            'side': None,
            '_': Append('suffix', 'sulcal_morphometry'),
        }

    class BrainVolumesBIDS(ProcessSchema, schema='bids',
                           process=brainvolumes):
        pass

    class BrainVolumesBrainVISA(ProcessSchema, schema='brainvisa',
                                process=brainvolumes):
        _ = {
            '*': {'seg_directory': 'segmentation'}}
        left_csf = {
            'prefix': 'csf',
            'side': 'L',
            'sidebis': None,
            'sulci_graph_version': None,
            'sulci_recognition_session': None,
            'suffix': None,
        }
        right_csf = {
            'prefix': 'csf',
            'side': 'R',
            'sidebis': None,
            'sulci_graph_version': None,
            'sulci_recognition_session': None,
            'suffix': None,
        }
        brain_volumes_file = {
            'prefix': 'brain_volumes',
            'suffix': None,
            'side': None,
            'sidebis': None,
            'sulci_graph_version': None,
            'sulci_recognition_session': None,
            'extension': 'csv',
        }
        subject = {
            'seg_directory': None,
            'prefix': None,
            'center': undefined,
            'side': None,
            'modality': None,
            'acquisition': None,
            'analysis': undefined,
            'subject_in_filename': False,
            'extension': None
        }
        _meta_links = {
            '*_labelled_graph': {'*': []}
        }

    class MorphoReportBIDS(ProcessSchema, schema='bids',
                           process=morpho_report):
        pass

    class MorphoReportBrainVISA(ProcessSchema, schema='brainvisa',
                                process=morpho_report):
        _ = {
            '*': {'seg_directory': None}}
        report = {
            'prefix': None,
            'side': None,
            'sidebis': None,
            'subject_in_filename': False,
            'sulci_graph_version': None,
            'sulci_recognition_session': None,
            'suffix': 'morphologist_report',
            'extension': 'pdf'
        }
        subject = {
            'prefix': None,
            'center': undefined,
            'side': None,
            'modality': None,
            'acquisition': None,
            'analysis': undefined,
            'subject_in_filename': False,
            'extension': None
        }

    class MorphologistShared(ProcessSchema, schema='brainvisa_shared',
                             process=Morphologist):
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
