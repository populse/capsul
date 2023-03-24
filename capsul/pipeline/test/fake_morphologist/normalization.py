# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class Normalization(Pipeline):
    def pipeline_definition(self):
        # nodes
        self.add_process(
            "NormalizeFSL",
            "capsul.pipeline.test.fake_morphologist.fslnormalization.FSLNormalization",
        )
        self.add_process(
            "NormalizeSPM",
            "capsul.pipeline.test.fake_morphologist.spmnormalization.SPMNormalization",
        )
        self.add_process(
            "NormalizeBaladin",
            "capsul.pipeline.test.fake_morphologist.baladinnormalizationpipeline.BaladinNormalizationPipeline",
        )
        self.nodes["NormalizeBaladin"].enabled = False
        self.nodes["NormalizeBaladin"].nodes["ReorientAnatomy"].enabled = False
        self.add_process(
            "Normalization_AimsMIRegister",
            "capsul.pipeline.test.fake_morphologist.normalization_aimsmiregister.normalization_aimsmiregister",
        )
        self.add_switch(
            "select_Normalization_pipeline",
            [
                "NormalizeFSL",
                "NormalizeSPM",
                "NormalizeBaladin",
                "Normalization_AimsMIRegister",
            ],
            ["transformation", "normalized", "reoriented_t1mri"],
            export_switch=False,
        )

        # links
        self.export_parameter(
            "select_Normalization_pipeline",
            "switch",
            "select_Normalization_pipeline",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization_AimsMIRegister", "anatomy_data", "t1mri", is_optional=False
        )
        self.add_link("t1mri->NormalizeFSL.t1mri")
        self.add_link("t1mri->NormalizeSPM.t1mri")
        self.add_link("t1mri->NormalizeBaladin.t1mri")
        self.add_link(
            "t1mri->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_reoriented_t1mri"
        )
        self.export_parameter(
            "NormalizeBaladin", "allow_flip_initial_MRI", is_optional=False
        )
        self.add_link("allow_flip_initial_MRI->NormalizeSPM.allow_flip_initial_MRI")
        self.add_link("allow_flip_initial_MRI->NormalizeFSL.allow_flip_initial_MRI")
        self.export_parameter(
            "NormalizeFSL",
            "ReorientAnatomy_commissures_coordinates",
            "commissures_coordinates",
            is_optional=True,
        )
        self.add_link(
            "commissures_coordinates->NormalizeBaladin.ReorientAnatomy_commissures_coordinates"
        )
        self.add_link(
            "commissures_coordinates->NormalizeSPM.ReorientAnatomy_commissures_coordinates"
        )
        self.export_parameter(
            "NormalizeFSL",
            "NormalizeFSL_init_translation_origin",
            "init_translation_origin",
            is_optional=True,
        )
        self.add_link("init_translation_origin->NormalizeSPM.init_translation_origin")
        self.export_parameter(
            "NormalizeFSL", "template", "NormalizeFSL_template", is_optional=True
        )
        self.export_parameter(
            "NormalizeFSL", "alignment", "NormalizeFSL_alignment", is_optional=True
        )
        self.export_parameter(
            "NormalizeFSL",
            "set_transformation_in_source_volume",
            "NormalizeFSL_set_transformation_in_source_volume",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "allow_retry_initialization",
            "NormalizeFSL_allow_retry_initialization",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "NormalizeFSL_cost_function",
            "NormalizeFSL_NormalizeFSL_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "NormalizeFSL_search_cost_function",
            "NormalizeFSL_NormalizeFSL_search_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "ConvertFSLnormalizationToAIMS_standard_template",
            "NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM",
            "NormalizeSPM",
            "NormalizeSPM_NormalizeSPM",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM", "template", "NormalizeSPM_template", is_optional=True
        )
        self.export_parameter(
            "NormalizeSPM",
            "allow_retry_initialization",
            "NormalizeSPM_allow_retry_initialization",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM", "voxel_size", "NormalizeSPM_voxel_size", is_optional=True
        )
        self.export_parameter(
            "NormalizeSPM",
            "cutoff_option",
            "NormalizeSPM_cutoff_option",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM", "nbiteration", "NormalizeSPM_nbiteration", is_optional=True
        )
        self.export_parameter(
            "NormalizeSPM",
            "ConvertSPMnormalizationToAIMS_target",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_target",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM",
            "ConvertSPMnormalizationToAIMS_normalized_volume",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeSPM",
            "ConvertSPMnormalizationToAIMS_removeSource",
            "NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeBaladin",
            "template",
            "NormalizeBaladin_template",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeBaladin",
            "set_transformation_in_source_volume",
            "NormalizeBaladin_set_transformation_in_source_volume",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization_AimsMIRegister",
            "anatomical_template",
            "Normalization_AimsMIRegister_anatomical_template",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization_AimsMIRegister",
            "mni_to_acpc",
            "Normalization_AimsMIRegister_mni_to_acpc",
            is_optional=True,
        )
        self.export_parameter(
            "Normalization_AimsMIRegister",
            "smoothing",
            "Normalization_AimsMIRegister_smoothing",
            is_optional=True,
        )
        self.add_link(
            "NormalizeFSL.transformation->select_Normalization_pipeline.NormalizeFSL_switch_transformation"
        )
        self.add_link(
            "NormalizeFSL.reoriented_t1mri->select_Normalization_pipeline.NormalizeFSL_switch_reoriented_t1mri"
        )
        self.export_parameter(
            "NormalizeFSL",
            "NormalizeFSL_transformation_matrix",
            "NormalizeFSL_NormalizeFSL_transformation_matrix",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "NormalizeFSL.NormalizeFSL_normalized_anatomy_data->select_Normalization_pipeline.NormalizeFSL_switch_normalized"
        )
        self.export_parameter(
            "NormalizeSPM",
            "ReorientAnatomy_output_commissures_coordinates",
            "output_commissures_coordinates",
            is_optional=True,
        )
        self.add_link(
            "NormalizeFSL.ReorientAnatomy_output_commissures_coordinates->output_commissures_coordinates"
        )
        self.add_link(
            "NormalizeSPM.transformation->select_Normalization_pipeline.NormalizeSPM_switch_transformation"
        )
        self.export_parameter(
            "NormalizeSPM",
            "spm_transformation",
            "NormalizeSPM_spm_transformation",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "NormalizeSPM.normalized_t1mri->select_Normalization_pipeline.NormalizeSPM_switch_normalized"
        )
        self.add_link(
            "NormalizeSPM.reoriented_t1mri->select_Normalization_pipeline.NormalizeSPM_switch_reoriented_t1mri"
        )
        self.add_link(
            "NormalizeSPM.ReorientAnatomy_output_commissures_coordinates->output_commissures_coordinates"
        )
        self.add_link(
            "NormalizeBaladin.transformation->select_Normalization_pipeline.NormalizeBaladin_switch_transformation"
        )
        self.add_link(
            "NormalizeBaladin.reoriented_t1mri->select_Normalization_pipeline.NormalizeBaladin_switch_reoriented_t1mri"
        )
        self.export_parameter(
            "NormalizeBaladin",
            "NormalizeBaladin_transformation_matrix",
            "NormalizeBaladin_NormalizeBaladin_transformation_matrix",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "NormalizeBaladin.NormalizeBaladin_normalized_anatomy_data->select_Normalization_pipeline.NormalizeBaladin_switch_normalized"
        )
        self.add_link(
            "NormalizeBaladin.ReorientAnatomy_output_commissures_coordinates->output_commissures_coordinates"
        )
        self.export_parameter(
            "Normalization_AimsMIRegister",
            "transformation_to_template",
            "Normalization_AimsMIRegister_transformation_to_template",
            weak_link=True,
            is_optional=True,
        )
        self.add_link(
            "Normalization_AimsMIRegister.normalized_anatomy_data->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_normalized"
        )
        self.add_link(
            "Normalization_AimsMIRegister.transformation_to_MNI->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_transformation"
        )
        self.export_parameter(
            "Normalization_AimsMIRegister",
            "transformation_to_ACPC",
            "Normalization_AimsMIRegister_transformation_to_ACPC",
            weak_link=True,
            is_optional=True,
        )
        self.export_parameter(
            "select_Normalization_pipeline", "transformation", is_optional=False
        )
        self.export_parameter(
            "select_Normalization_pipeline", "normalized", is_optional=False
        )
        self.export_parameter(
            "select_Normalization_pipeline", "reoriented_t1mri", is_optional=False
        )

        # parameters order

        self.reorder_fields(
            (
                "select_Normalization_pipeline",
                "t1mri",
                "transformation",
                "allow_flip_initial_MRI",
                "commissures_coordinates",
                "reoriented_t1mri",
                "output_commissures_coordinates",
                "init_translation_origin",
                "normalized",
                "NormalizeFSL_template",
                "NormalizeFSL_alignment",
                "NormalizeFSL_set_transformation_in_source_volume",
                "NormalizeFSL_allow_retry_initialization",
                "NormalizeFSL_NormalizeFSL_transformation_matrix",
                "NormalizeFSL_NormalizeFSL_cost_function",
                "NormalizeFSL_NormalizeFSL_search_cost_function",
                "NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template",
                "NormalizeSPM_NormalizeSPM",
                "NormalizeSPM_spm_transformation",
                "NormalizeSPM_template",
                "NormalizeSPM_allow_retry_initialization",
                "NormalizeSPM_voxel_size",
                "NormalizeSPM_cutoff_option",
                "NormalizeSPM_nbiteration",
                "NormalizeSPM_ConvertSPMnormalizationToAIMS_target",
                "NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume",
                "NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource",
                "NormalizeBaladin_template",
                "NormalizeBaladin_set_transformation_in_source_volume",
                "NormalizeBaladin_NormalizeBaladin_transformation_matrix",
                "Normalization_AimsMIRegister_anatomical_template",
                "Normalization_AimsMIRegister_transformation_to_template",
                "Normalization_AimsMIRegister_transformation_to_ACPC",
                "Normalization_AimsMIRegister_mni_to_acpc",
                "Normalization_AimsMIRegister_smoothing",
            )
        )

        # default and initial values
        self.allow_flip_initial_MRI = False
        self.init_translation_origin = 0
        self.NormalizeFSL_alignment = "Not Aligned but Same Orientation"
        self.NormalizeFSL_set_transformation_in_source_volume = True
        self.NormalizeFSL_allow_retry_initialization = True
        self.NormalizeFSL_NormalizeFSL_cost_function = "corratio"
        self.NormalizeFSL_NormalizeFSL_search_cost_function = "corratio"
        self.NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template = 0
        self.NormalizeSPM_allow_retry_initialization = True
        self.NormalizeSPM_voxel_size = "[1 1 1]"
        self.NormalizeSPM_cutoff_option = 25
        self.NormalizeSPM_nbiteration = 16
        self.NormalizeSPM_ConvertSPMnormalizationToAIMS_target = "MNI template"
        self.NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource = False
        self.NormalizeBaladin_template = "/casa/host/build/share/brainvisa-share-5.1/anatomical_templates/MNI152_T1_1mm.nii.gz"
        self.NormalizeBaladin_set_transformation_in_source_volume = True
        self.Normalization_AimsMIRegister_anatomical_template = "/casa/host/build/share/brainvisa-share-5.1/anatomical_templates/MNI152_T1_2mm.nii.gz"
        self.Normalization_AimsMIRegister_mni_to_acpc = "/casa/host/build/share/brainvisa-share-5.1/transformation/talairach_TO_spm_template_novoxels.trm"
        self.Normalization_AimsMIRegister_smoothing = 1.0

        # nodes positions
        self.node_position = {
            "Normalization_AimsMIRegister": (538.0, 1375.0),
            "NormalizeBaladin": (479.0, 1041.0),
            "NormalizeFSL": (475.0, 0.0),
            "NormalizeSPM": (479.0, 489.5),
            "inputs": (0.0, 660.0),
            "outputs": (1212.0, 855.0),
            "select_Normalization_pipeline": (846.0, 764.0),
        }

        self.do_autoexport_nodes_parameters = False
