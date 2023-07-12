# -*- coding: utf-8 -*-

from capsul.dataset import MetadataSchema


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
