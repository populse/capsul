# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class NormalizationSkullStripped(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("SkullStripping", "capsul.pipeline.test.fake_morphologist.skullstripping.skullstripping")
        self.nodes["SkullStripping"].set_plug_value("t1mri", traits.Undefined)
        self.nodes["SkullStripping"].set_plug_value("brain_mask", traits.Undefined)
        self.add_process("Normalization", "capsul.pipeline.test.fake_morphologist.normalization.Normalization", make_optional=['reoriented_t1mri'])
        self.nodes["Normalization"].process.trait("reoriented_t1mri").optional = True

        self.nodes["Normalization"].plugs["reoriented_t1mri"].optional = True

        self.nodes["Normalization"].set_plug_value("NormalizeSPM_template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].set_plug_value("NormalizeBaladin_template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeSPM"].set_plug_value("template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeBaladin"].set_plug_value("template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["Normalization_AimsMIRegister"].process.trait("normalized_anatomy_data").optional = True

        self.nodes["Normalization"].process.nodes["Normalization_AimsMIRegister"].plugs["normalized_anatomy_data"].optional = True

        self.nodes["Normalization"].process.nodes["Normalization_AimsMIRegister"].process.trait("transformation_to_MNI").optional = True

        self.nodes["Normalization"].process.nodes["Normalization_AimsMIRegister"].plugs["transformation_to_MNI"].optional = True

        self.nodes["Normalization"].process.nodes["select_Normalization_pipeline"].plugs["reoriented_t1mri"].optional = True

        self.nodes["Normalization"].process.nodes["NormalizeSPM"].process.nodes["normalization_t1_spm12_reinit"].set_plug_value("anatomical_template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeSPM"].process.nodes["normalization_t1_spm8_reinit"].enabled = False
        self.nodes["Normalization"].process.nodes["NormalizeSPM"].process.nodes["normalization_t1_spm8_reinit"].set_plug_value("anatomical_template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeBaladin"].process.nodes["NormalizeBaladin"].set_plug_value("anatomical_template", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeBaladin"].process.nodes["ConvertBaladinNormalizationToAIMS"].set_plug_value("registered_volume", '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz')
        self.nodes["Normalization"].process.nodes["NormalizeBaladin"].process.nodes["ReorientAnatomy"].enabled = False
        self.nodes["Normalization"].process.nodes_activation = {'NormalizeFSL': True, 'NormalizeSPM': True, 'NormalizeBaladin': True, 'Normalization_AimsMIRegister': True}
        self.nodes["Normalization"].process.NormalizeSPM_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.nodes["Normalization"].process.NormalizeBaladin_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.add_process("TalairachFromNormalization", "capsul.pipeline.test.fake_morphologist.talairachtransformationfromnormalization.TalairachTransformationFromNormalization", make_optional=['commissure_coordinates'])
        self.nodes["TalairachFromNormalization"].set_plug_value("normalization_transformation", traits.Undefined)
        self.nodes["TalairachFromNormalization"].set_plug_value("t1mri", traits.Undefined)
        self.nodes["TalairachFromNormalization"].set_plug_value("source_referential", traits.Undefined)
        self.nodes["TalairachFromNormalization"].set_plug_value("normalized_referential", traits.Undefined)
        self.nodes["TalairachFromNormalization"].set_plug_value("transform_chain_ACPC_to_Normalized", traits.Undefined)
        self.nodes["TalairachFromNormalization"].process.trait("Talairach_transform").optional = False

        self.nodes["TalairachFromNormalization"].plugs["Talairach_transform"].optional = False

        self.nodes["TalairachFromNormalization"].process.trait("commissure_coordinates").optional = True

        self.nodes["TalairachFromNormalization"].plugs["commissure_coordinates"].optional = True


        # links
        self.export_parameter("TalairachFromNormalization", "t1mri", is_optional=False)
        self.add_link("t1mri->SkullStripping.t1mri")
        self.export_parameter("SkullStripping", "brain_mask", is_optional=False)
        self.export_parameter("Normalization", "NormalizeFSL_template", "template", is_optional=True)
        self.add_link("template->Normalization.Normalization_AimsMIRegister_anatomical_template")
        self.add_link("template->Normalization.NormalizeSPM_template")
        self.add_link("template->Normalization.NormalizeBaladin_template")
        self.export_parameter("Normalization", "select_Normalization_pipeline", "Normalization_select_Normalization_pipeline", is_optional=True)
        self.export_parameter("Normalization", "allow_flip_initial_MRI", "Normalization_allow_flip_initial_MRI", is_optional=True)
        self.export_parameter("Normalization", "commissures_coordinates", "Normalization_commissures_coordinates", is_optional=True)
        self.export_parameter("Normalization", "init_translation_origin", "Normalization_init_translation_origin", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_alignment", "Normalization_NormalizeFSL_alignment", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_set_transformation_in_source_volume", "Normalization_NormalizeFSL_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_allow_retry_initialization", "Normalization_NormalizeFSL_allow_retry_initialization", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_NormalizeFSL_cost_function", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_NormalizeFSL_search_cost_function", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_NormalizeSPM", "Normalization_NormalizeSPM_NormalizeSPM", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_allow_retry_initialization", "Normalization_NormalizeSPM_allow_retry_initialization", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_voxel_size", "Normalization_NormalizeSPM_voxel_size", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_cutoff_option", "Normalization_NormalizeSPM_cutoff_option", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_nbiteration", "Normalization_NormalizeSPM_nbiteration", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", is_optional=True)
        self.export_parameter("Normalization", "NormalizeBaladin_set_transformation_in_source_volume", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("Normalization", "Normalization_AimsMIRegister_mni_to_acpc", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", is_optional=True)
        self.export_parameter("Normalization", "Normalization_AimsMIRegister_smoothing", "Normalization_Normalization_AimsMIRegister_smoothing", is_optional=True)
        self.export_parameter("TalairachFromNormalization", "source_referential", "TalairachFromNormalization_source_referential", is_optional=True)
        self.export_parameter("TalairachFromNormalization", "normalized_referential", "TalairachFromNormalization_normalized_referential", is_optional=True)
        self.export_parameter("TalairachFromNormalization", "acpc_referential", "TalairachFromNormalization_acpc_referential", is_optional=True)
        self.export_parameter("TalairachFromNormalization", "transform_chain_ACPC_to_Normalized", "TalairachFromNormalization_transform_chain_ACPC_to_Normalized", is_optional=True)
        self.export_parameter("SkullStripping", "skull_stripped", is_optional=False)
        self.add_link("SkullStripping.skull_stripped->Normalization.t1mri")
        self.export_parameter("Normalization", "transformation", is_optional=True)
        self.add_link("Normalization.transformation->TalairachFromNormalization.normalization_transformation")
        self.export_parameter("Normalization", "reoriented_t1mri", "Normalization_reoriented_t1mri", is_optional=True)
        self.export_parameter("Normalization", "normalized", "Normalization_normalized", is_optional=True)
        self.export_parameter("Normalization", "NormalizeFSL_NormalizeFSL_transformation_matrix", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", is_optional=True)
        self.export_parameter("Normalization", "NormalizeSPM_spm_transformation", "Normalization_NormalizeSPM_spm_transformation", is_optional=True)
        self.export_parameter("Normalization", "NormalizeBaladin_NormalizeBaladin_transformation_matrix", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", is_optional=True)
        self.export_parameter("Normalization", "Normalization_AimsMIRegister_transformation_to_template", "Normalization_Normalization_AimsMIRegister_transformation_to_template", is_optional=True)
        self.export_parameter("Normalization", "Normalization_AimsMIRegister_transformation_to_ACPC", "Normalization_Normalization_AimsMIRegister_transformation_to_ACPC", is_optional=True)
        self.export_parameter("TalairachFromNormalization", "Talairach_transform", "talairach_transformation", is_optional=False)
        self.export_parameter("TalairachFromNormalization", "commissure_coordinates", is_optional=True)

        # parameters order

        self.reorder_traits(("t1mri", "brain_mask", "template", "skull_stripped", "transformation", "talairach_transformation", "commissure_coordinates", "Normalization_select_Normalization_pipeline", "Normalization_allow_flip_initial_MRI", "Normalization_commissures_coordinates", "Normalization_reoriented_t1mri", "Normalization_init_translation_origin", "Normalization_normalized", "Normalization_NormalizeFSL_alignment", "Normalization_NormalizeFSL_set_transformation_in_source_volume", "Normalization_NormalizeFSL_allow_retry_initialization", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "Normalization_NormalizeSPM_NormalizeSPM", "Normalization_NormalizeSPM_spm_transformation", "Normalization_NormalizeSPM_allow_retry_initialization", "Normalization_NormalizeSPM_voxel_size", "Normalization_NormalizeSPM_cutoff_option", "Normalization_NormalizeSPM_nbiteration", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", "Normalization_Normalization_AimsMIRegister_smoothing", "Normalization_Normalization_AimsMIRegister_transformation_to_template", "Normalization_Normalization_AimsMIRegister_transformation_to_ACPC", "TalairachFromNormalization_source_referential", "TalairachFromNormalization_normalized_referential", "TalairachFromNormalization_acpc_referential", "TalairachFromNormalization_transform_chain_ACPC_to_Normalized"))

        # default and initial values
        self.template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.Normalization_select_Normalization_pipeline = 'NormalizeSPM'
        self.Normalization_NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.Normalization_NormalizeFSL_allow_retry_initialization = True
        self.Normalization_NormalizeSPM_allow_retry_initialization = True
        self.Normalization_NormalizeSPM_cutoff_option = 25
        self.Normalization_NormalizeSPM_nbiteration = 16
        self.Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.Normalization_Normalization_AimsMIRegister_mni_to_acpc = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/transformation/talairach_TO_spm_template_novoxels.trm'
        self.Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.TalairachFromNormalization_acpc_referential = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/registration/Talairach-AC_PC-Anatomist.referential'

        # nodes positions
        self.node_position = {
            "Normalization": (832.0799999999998, 384.39999999999986),
            "SkullStripping": (672.1599999999999, 248.68),
            "TalairachFromNormalization": (1363.9600000000003, 79.84),
            "inputs": (50.0, 50.0),
            "outputs": (1646.84, 315.48),
        }

        self.do_autoexport_nodes_parameters = False
