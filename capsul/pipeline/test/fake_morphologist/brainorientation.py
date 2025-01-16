from soma.controller import undefined

from capsul.api import Pipeline


class BrainOrientation(Pipeline):
    def pipeline_definition(self):
        # nodes
        self.add_process(
            "StandardACPC",
            "capsul.pipeline.test.fake_morphologist.acpcorientation.AcpcOrientation",
        )
        self.add_process(
            "Normalization",
            "capsul.pipeline.test.fake_morphologist.normalization.Normalization",
        )
        self.nodes["Normalization"].nodes["NormalizeBaladin"].enabled = False
        self.nodes["Normalization"].nodes["NormalizeBaladin"].nodes[
            "ReorientAnatomy"
        ].enabled = False
        self.add_process(
            "TalairachFromNormalization",
            "capsul.pipeline.test.fake_morphologist.talairachtransformationfromnormalization.TalairachTransformationFromNormalization",
        )
        self.add_switch(
            "select_AC_PC_Or_Normalization",
            ["StandardACPC", "Normalization"],
            ["commissure_coordinates", "reoriented_t1mri", "talairach_transformation"],
            make_optional=["talairach_transformation"],
            export_switch=False,
        )

        # links
        self.export_parameter(
            "select_AC_PC_Or_Normalization",
            "switch",
            "select_AC_PC_Or_Normalization",
            is_optional=True,
        )
        self.export_parameter("Normalization", "t1mri", "T1mri", is_optional=False)
        self.add_link("T1mri->StandardACPC.T1mri")
        self.export_parameter(
            "Normalization", "allow_flip_initial_MRI", is_optional=False
        )
        self.add_link("allow_flip_initial_MRI->StandardACPC.allow_flip_initial_MRI")
        self.export_parameter(
            "StandardACPC", "Normalised", "StandardACPC_Normalised", is_optional=True
        )
        self.export_parameter(
            "StandardACPC",
            "Anterior_Commissure",
            "StandardACPC_Anterior_Commissure",
            is_optional=True,
        )
        self.export_parameter(
            "StandardACPC",
            "Posterior_Commissure",
            "StandardACPC_Posterior_Commissure",
            is_optional=True,
        )
        self.export_parameter(
            "StandardACPC",
            "Interhemispheric_Point",
            "StandardACPC_Interhemispheric_Point",
            is_optional=True,
        )
        self.export_parameter(
            "StandardACPC",
            "Left_Hemisphere_Point",
            "StandardACPC_Left_Hemisphere_Point",
            is_optional=True,
        )
        self.export_parameter(
            "StandardACPC",
            "remove_older_MNI_normalization",
            "StandardACPC_remove_older_MNI_normalization",
            is_optional=True,
        )
        self.export_parameter(
            "StandardACPC",
            "older_MNI_normalization",
            "StandardACPC_older_MNI_normalization",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "select_Normalization_pipeline",
            "Normalization_select_Normalization_pipeline",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "commissures_coordinates",
            "Normalization_commissures_coordinates",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "init_translation_origin",
            "Normalization_init_translation_origin",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_template",
            "Normalization_NormalizeFSL_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_alignment",
            "Normalization_NormalizeFSL_alignment",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_set_transformation_in_source_volume",
            "Normalization_NormalizeFSL_set_transformation_in_source_volume",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_allow_retry_initialization",
            "Normalization_NormalizeFSL_allow_retry_initialization",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_NormalizeFSL_cost_function",
            "Normalization_NormalizeFSL_NormalizeFSL_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_NormalizeFSL_search_cost_function",
            "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template",
            "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_NormalizeSPM",
            "Normalization_NormalizeSPM_NormalizeSPM",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_template",
            "Normalization_NormalizeSPM_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_allow_retry_initialization",
            "Normalization_NormalizeSPM_allow_retry_initialization",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_voxel_size",
            "Normalization_NormalizeSPM_voxel_size",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_cutoff_option",
            "Normalization_NormalizeSPM_cutoff_option",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_nbiteration",
            "Normalization_NormalizeSPM_nbiteration",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_target",
            "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume",
            "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource",
            "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeBaladin_template",
            "Normalization_NormalizeBaladin_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeBaladin_set_transformation_in_source_volume",
            "Normalization_NormalizeBaladin_set_transformation_in_source_volume",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "Normalization_AimsMIRegister_anatomical_template",
            "Normalization_Normalization_AimsMIRegister_anatomical_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "Normalization_AimsMIRegister_mni_to_acpc",
            "Normalization_Normalization_AimsMIRegister_mni_to_acpc",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "Normalization_AimsMIRegister_smoothing",
            "Normalization_Normalization_AimsMIRegister_smoothing",
            is_optional=True,
        )
        self.export_parameter(
            "TalairachFromNormalization",
            "source_referential",
            "TalairachFromNormalization_source_referential",
            is_optional=True,
        )
        self.export_parameter(
            "TalairachFromNormalization",
            "normalized_referential",
            "TalairachFromNormalization_normalized_referential",
            is_optional=True,
        )
        self.export_parameter(
            "TalairachFromNormalization",
            "acpc_referential",
            "TalairachFromNormalization_acpc_referential",
            is_optional=True,
        )
        self.export_parameter(
            "TalairachFromNormalization",
            "transform_chain_ACPC_to_Normalized",
            "TalairachFromNormalization_transform_chain_ACPC_to_Normalized",
            is_optional=True,
        )
        self.add_link(
            "StandardACPC.commissure_coordinates->select_AC_PC_Or_Normalization.StandardACPC_switch_commissure_coordinates"
        )
        self.add_link(
            "StandardACPC.reoriented_t1mri->select_AC_PC_Or_Normalization.StandardACPC_switch_reoriented_t1mri"
        )
        self.export_parameter(
            "Normalization",
            "transformation",
            "normalization_transformation",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "Normalization.transformation->TalairachFromNormalization.normalization_transformation"
        )
        self.add_link(
            "Normalization.reoriented_t1mri->select_AC_PC_Or_Normalization.Normalization_switch_reoriented_t1mri"
        )
        self.add_link(
            "Normalization.reoriented_t1mri->TalairachFromNormalization.t1mri"
        )
        self.export_parameter(
            "Normalization",
            "normalized",
            "Normalization_normalized",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeFSL_NormalizeFSL_transformation_matrix",
            "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeSPM_spm_transformation",
            "Normalization_NormalizeSPM_spm_transformation",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "NormalizeBaladin_NormalizeBaladin_transformation_matrix",
            "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "Normalization_AimsMIRegister_transformation_to_template",
            "Normalization_Normalization_AimsMIRegister_transformation_to_template",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "Normalization",
            "Normalization_AimsMIRegister_transformation_to_ACPC",
            "Normalization_Normalization_AimsMIRegister_transformation_to_ACPC",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "TalairachFromNormalization.Talairach_transform->select_AC_PC_Or_Normalization.Normalization_switch_talairach_transformation"
        )
        self.add_link(
            "TalairachFromNormalization.commissure_coordinates->select_AC_PC_Or_Normalization.Normalization_switch_commissure_coordinates"
        )
        self.export_parameter(
            "select_AC_PC_Or_Normalization", "commissure_coordinates", is_optional=False
        )
        self.export_parameter(
            "select_AC_PC_Or_Normalization", "reoriented_t1mri", is_optional=False
        )
        self.export_parameter(
            "select_AC_PC_Or_Normalization",
            "talairach_transformation",
            is_optional=True,
        )

        # parameters order

        self.reorder_fields(
            (
                "select_AC_PC_Or_Normalization",
                "T1mri",
                "commissure_coordinates",
                "allow_flip_initial_MRI",
                "reoriented_t1mri",
                "talairach_transformation",
                "StandardACPC_Normalised",
                "StandardACPC_Anterior_Commissure",
                "StandardACPC_Posterior_Commissure",
                "StandardACPC_Interhemispheric_Point",
                "StandardACPC_Left_Hemisphere_Point",
                "StandardACPC_remove_older_MNI_normalization",
                "StandardACPC_older_MNI_normalization",
                "Normalization_select_Normalization_pipeline",
                "Normalization_commissures_coordinates",
                "Normalization_init_translation_origin",
                "Normalization_normalized",
                "Normalization_NormalizeFSL_template",
                "Normalization_NormalizeFSL_alignment",
                "Normalization_NormalizeFSL_set_transformation_in_source_volume",
                "Normalization_NormalizeFSL_allow_retry_initialization",
                "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix",
                "Normalization_NormalizeFSL_NormalizeFSL_cost_function",
                "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function",
                "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template",
                "Normalization_NormalizeSPM_NormalizeSPM",
                "Normalization_NormalizeSPM_spm_transformation",
                "Normalization_NormalizeSPM_template",
                "Normalization_NormalizeSPM_allow_retry_initialization",
                "Normalization_NormalizeSPM_voxel_size",
                "Normalization_NormalizeSPM_cutoff_option",
                "Normalization_NormalizeSPM_nbiteration",
                "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target",
                "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume",
                "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource",
                "Normalization_NormalizeBaladin_template",
                "Normalization_NormalizeBaladin_set_transformation_in_source_volume",
                "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix",
                "Normalization_Normalization_AimsMIRegister_anatomical_template",
                "Normalization_Normalization_AimsMIRegister_transformation_to_template",
                "Normalization_Normalization_AimsMIRegister_transformation_to_ACPC",
                "Normalization_Normalization_AimsMIRegister_mni_to_acpc",
                "Normalization_Normalization_AimsMIRegister_smoothing",
                "TalairachFromNormalization_source_referential",
                "TalairachFromNormalization_normalized_referential",
                "TalairachFromNormalization_acpc_referential",
                "TalairachFromNormalization_transform_chain_ACPC_to_Normalized",
                "normalization_transformation",
            )
        )

        # default and initial values
        self.select_AC_PC_Or_Normalization = "Normalization"
        self.allow_flip_initial_MRI = False
        self.StandardACPC_Normalised = "No"
        self.StandardACPC_remove_older_MNI_normalization = True
        self.Normalization_select_Normalization_pipeline = "NormalizeSPM"
        self.Normalization_init_translation_origin = 0
        self.Normalization_NormalizeFSL_alignment = "Not Aligned but Same Orientation"
        self.Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.Normalization_NormalizeFSL_allow_retry_initialization = True
        self.Normalization_NormalizeFSL_NormalizeFSL_cost_function = "corratio"
        self.Normalization_NormalizeFSL_NormalizeFSL_search_cost_function = "corratio"
        self.Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template = 0
        self.Normalization_NormalizeSPM_allow_retry_initialization = True
        self.Normalization_NormalizeSPM_voxel_size = "[1 1 1]"
        self.Normalization_NormalizeSPM_cutoff_option = 25
        self.Normalization_NormalizeSPM_nbiteration = 16
        self.Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target = (
            "MNI template"
        )
        self.Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource = (
            False
        )
        self.Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.Normalization_Normalization_AimsMIRegister_anatomical_template = "/casa/host/build/share/brainvisa-share-5.2/anatomical_templates/MNI152_T1_2mm.nii.gz"
        self.Normalization_Normalization_AimsMIRegister_mni_to_acpc = "/casa/host/build/share/brainvisa-share-5.2/transformation/talairach_TO_spm_template_novoxels.trm"
        self.Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.TalairachFromNormalization_acpc_referential = "/casa/host/build/share/brainvisa-share-5.2/registration/Talairach-AC_PC-Anatomist.referential"

        # nodes positions
        self.node_position = {
            "Normalization": (161.4, 227.6),
            "StandardACPC": (272.8, -169.0),
            "TalairachFromNormalization": (684.6, 485.4),
            "inputs": (-510.8, 14.8),
            "outputs": (1185.4, 441.8),
            "select_AC_PC_Or_Normalization": (925.6, 189.4),
        }

        self.do_autoexport_nodes_parameters = False
