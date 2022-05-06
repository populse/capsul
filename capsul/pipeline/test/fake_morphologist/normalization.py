# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class Normalization(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("NormalizeFSL", "capsul.pipeline.test.fake_morphologist.fslnormalization.FSLNormalization", make_optional=['NormalizeFSL_cost_function', 'NormalizeFSL_search_cost_function', 'NormalizeFSL_init_translation_origin', 'ConvertFSLnormalizationToAIMS_standard_template', 'NormalizeFSL_transformation_matrix', 'NormalizeFSL_normalized_anatomy_data', 'ConvertFSLnormalizationToAIMS_write'])
        self.nodes["NormalizeFSL"].activated = False
        self.add_process("NormalizeSPM", "capsul.pipeline.test.fake_morphologist.spmnormalization.SPMNormalization", make_optional=['ConvertSPMnormalizationToAIMS_target', 'ConvertSPMnormalizationToAIMS_removeSource'])
        self.nodes["NormalizeSPM"].activated = False
        self.add_process("NormalizeBaladin", "capsul.pipeline.test.fake_morphologist.baladinnormalizationpipeline.BaladinNormalizationPipeline", make_optional=['NormalizeBaladin_transformation_matrix', 'NormalizeBaladin_normalized_anatomy_data', 'ConvertBaladinNormalizationToAIMS_write'])
        self.nodes["NormalizeBaladin"].enabled = False
        self.nodes["NormalizeBaladin"].activated = False
        self.add_process("Normalization_AimsMIRegister", "capsul.pipeline.test.fake_morphologist.normalization_aimsmiregister.normalization_aimsmiregister")
        self.add_switch("select_Normalization_pipeline", ['NormalizeFSL', 'Normalization_AimsMIRegister', 'NormalizeSPM', 'NormalizeBaladin'], ['transformation', 'normalized', 'reoriented_t1mri'], export_switch=False)

        # links
        self.export_parameter("select_Normalization_pipeline", "switch", "select_Normalization_pipeline")
        self.export_parameter("NormalizeBaladin", "t1mri")
        self.add_link("t1mri->Normalization_AimsMIRegister.anatomy_data")
        self.add_link("t1mri->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_reoriented_t1mri")
        self.add_link("t1mri->NormalizeFSL.t1mri")
        self.add_link("t1mri->NormalizeSPM.t1mri")
        self.export_parameter("NormalizeFSL", "allow_flip_initial_MRI")
        self.add_link("allow_flip_initial_MRI->NormalizeSPM.allow_flip_initial_MRI")
        self.add_link("allow_flip_initial_MRI->NormalizeBaladin.allow_flip_initial_MRI")
        self.export_parameter("NormalizeSPM", "ReorientAnatomy_commissures_coordinates", "commissures_coordinates")
        self.add_link("commissures_coordinates->NormalizeBaladin.ReorientAnatomy_commissures_coordinates")
        self.add_link("commissures_coordinates->NormalizeFSL.ReorientAnatomy_commissures_coordinates")
        self.export_parameter("NormalizeFSL", "NormalizeFSL_init_translation_origin", "init_translation_origin")
        self.add_link("init_translation_origin->NormalizeSPM.init_translation_origin")
        self.export_parameter("NormalizeFSL", "template", "NormalizeFSL_template")
        self.export_parameter("NormalizeFSL", "alignment", "NormalizeFSL_alignment")
        self.export_parameter("NormalizeFSL", "set_transformation_in_source_volume", "NormalizeFSL_set_transformation_in_source_volume")
        self.export_parameter("NormalizeFSL", "allow_retry_initialization", "NormalizeFSL_allow_retry_initialization")
        self.export_parameter("NormalizeFSL", "NormalizeFSL_cost_function", "NormalizeFSL_NormalizeFSL_cost_function")
        self.export_parameter("NormalizeFSL", "NormalizeFSL_search_cost_function", "NormalizeFSL_NormalizeFSL_search_cost_function")
        self.export_parameter("NormalizeFSL", "ConvertFSLnormalizationToAIMS_standard_template", "NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template")
        self.export_parameter("NormalizeSPM", "NormalizeSPM", "NormalizeSPM_NormalizeSPM")
        self.export_parameter("NormalizeSPM", "template", "NormalizeSPM_template")
        self.export_parameter("NormalizeSPM", "allow_retry_initialization", "NormalizeSPM_allow_retry_initialization")
        self.export_parameter("NormalizeSPM", "voxel_size", "NormalizeSPM_voxel_size")
        self.export_parameter("NormalizeSPM", "cutoff_option", "NormalizeSPM_cutoff_option")
        self.export_parameter("NormalizeSPM", "nbiteration", "NormalizeSPM_nbiteration")
        self.export_parameter("NormalizeSPM", "ConvertSPMnormalizationToAIMS_target", "NormalizeSPM_ConvertSPMnormalizationToAIMS_target")
        self.export_parameter("NormalizeSPM", "ConvertSPMnormalizationToAIMS_normalized_volume", "NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume")
        self.export_parameter("NormalizeSPM", "ConvertSPMnormalizationToAIMS_removeSource", "NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource")
        self.export_parameter("NormalizeBaladin", "template", "NormalizeBaladin_template")
        self.export_parameter("NormalizeBaladin", "set_transformation_in_source_volume", "NormalizeBaladin_set_transformation_in_source_volume")
        self.export_parameter("Normalization_AimsMIRegister", "anatomical_template", "Normalization_AimsMIRegister_anatomical_template")
        self.export_parameter("Normalization_AimsMIRegister", "mni_to_acpc", "Normalization_AimsMIRegister_mni_to_acpc")
        self.export_parameter("Normalization_AimsMIRegister", "smoothing", "Normalization_AimsMIRegister_smoothing")
        self.add_link("NormalizeFSL.transformation->select_Normalization_pipeline.NormalizeFSL_switch_transformation")
        self.add_link("NormalizeFSL.reoriented_t1mri->select_Normalization_pipeline.NormalizeFSL_switch_reoriented_t1mri")
        self.export_parameter("NormalizeFSL", "NormalizeFSL_transformation_matrix", "NormalizeFSL_NormalizeFSL_transformation_matrix", weak_link=True)
        self.add_link("NormalizeFSL.NormalizeFSL_normalized_anatomy_data->select_Normalization_pipeline.NormalizeFSL_switch_normalized")
        self.export_parameter("NormalizeFSL", "ReorientAnatomy_output_commissures_coordinates", "output_commissures_coordinates")
        self.add_link("NormalizeSPM.transformation->select_Normalization_pipeline.NormalizeSPM_switch_transformation")
        self.export_parameter("NormalizeSPM", "spm_transformation", "NormalizeSPM_spm_transformation", weak_link=True)
        self.add_link("NormalizeSPM.normalized_t1mri->select_Normalization_pipeline.NormalizeSPM_switch_normalized")
        self.add_link("NormalizeSPM.reoriented_t1mri->select_Normalization_pipeline.NormalizeSPM_switch_reoriented_t1mri")
        self.add_link("NormalizeSPM.ReorientAnatomy_output_commissures_coordinates->output_commissures_coordinates")
        self.add_link("NormalizeBaladin.transformation->select_Normalization_pipeline.NormalizeBaladin_switch_transformation")
        self.add_link("NormalizeBaladin.reoriented_t1mri->select_Normalization_pipeline.NormalizeBaladin_switch_reoriented_t1mri")
        self.export_parameter("NormalizeBaladin", "NormalizeBaladin_transformation_matrix", "NormalizeBaladin_NormalizeBaladin_transformation_matrix", weak_link=True)
        self.add_link("NormalizeBaladin.NormalizeBaladin_normalized_anatomy_data->select_Normalization_pipeline.NormalizeBaladin_switch_normalized")
        self.add_link("NormalizeBaladin.ReorientAnatomy_output_commissures_coordinates->output_commissures_coordinates")
        self.export_parameter("Normalization_AimsMIRegister", "transformation_to_template", "Normalization_AimsMIRegister_transformation_to_template", weak_link=True)
        self.add_link("Normalization_AimsMIRegister.normalized_anatomy_data->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_normalized")
        self.add_link("Normalization_AimsMIRegister.transformation_to_MNI->select_Normalization_pipeline.Normalization_AimsMIRegister_switch_transformation")
        self.export_parameter("Normalization_AimsMIRegister", "transformation_to_ACPC", "Normalization_AimsMIRegister_transformation_to_ACPC", weak_link=True)
        self.export_parameter("select_Normalization_pipeline", "transformation")
        self.export_parameter("select_Normalization_pipeline", "normalized")
        self.export_parameter("select_Normalization_pipeline", "reoriented_t1mri")

        # default and initial values
        self.allow_flip_initial_MRI = False
        self.init_translation_origin = 0
        self.NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.NormalizeFSL_set_transformation_in_source_volume = True
        self.NormalizeFSL_allow_retry_initialization = True
        self.NormalizeFSL_NormalizeFSL_cost_function = 'corratio'
        self.NormalizeFSL_NormalizeFSL_search_cost_function = 'corratio'
        self.NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template = 0
        self.NormalizeSPM_template = '/host/usr/local/spm12-standalone/spm12_mcr/spm12/toolbox/OldNorm/T1.nii'
        self.NormalizeSPM_allow_retry_initialization = True
        self.NormalizeSPM_voxel_size = '[1 1 1]'
        self.NormalizeSPM_cutoff_option = 25
        self.NormalizeSPM_nbiteration = 16
        self.NormalizeSPM_ConvertSPMnormalizationToAIMS_target = 'MNI template'
        self.NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource = False
        self.NormalizeBaladin_set_transformation_in_source_volume = True
        self.Normalization_AimsMIRegister_mni_to_acpc = '/casa/host/build/share/brainvisa-share-5.1/transformation/talairach_TO_spm_template_novoxels.trm'
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
