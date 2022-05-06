# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class Morphologist(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("importation", "capsul.pipeline.test.fake_morphologist.importt1mri.ImportT1MRI")
        self.add_process("PrepareSubject", "capsul.pipeline.test.fake_morphologist.brainorientation.BrainOrientation", make_optional=['StandardACPC_Normalised', 'StandardACPC_remove_older_MNI_normalization', 'Normalization_select_Normalization_pipeline', 'TalairachFromNormalization_source_referential', 'TalairachFromNormalization_normalized_referential', 'TalairachFromNormalization_transform_chain_ACPC_to_Normalized', 'normalization_transformation', 'Normalization_normalized'])
        self.add_process("BiasCorrection", "capsul.pipeline.test.fake_morphologist.t1biascorrection.T1BiasCorrection")
        self.add_process("HistoAnalysis", "capsul.pipeline.test.fake_morphologist.histoanalysis.HistoAnalysis")
        self.add_process("BrainSegmentation", "capsul.pipeline.test.fake_morphologist.brainsegmentation.BrainSegmentation")
        self.add_process("Renorm", "capsul.pipeline.test.fake_morphologist.normalizationskullstripped.NormalizationSkullStripped", make_optional=['Normalization_select_Normalization_pipeline', 'Normalization_allow_flip_initial_MRI', 'TalairachFromNormalization_source_referential', 'TalairachFromNormalization_normalized_referential', 'TalairachFromNormalization_transform_chain_ACPC_to_Normalized', 'transformation', 'Normalization_normalized', 'commissure_coordinates'])
        self.nodes["Renorm"].activated = False
        self.add_process("SplitBrain", "capsul.pipeline.test.fake_morphologist.splitbrain.SplitBrain")
        self.add_process("TalairachTransformation", "capsul.pipeline.test.fake_morphologist.talairachtransformation.TalairachTransformation")
        self.add_process("HeadMesh", "capsul.pipeline.test.fake_morphologist.scalpmesh.ScalpMesh")
        self.add_process("SulcalMorphometry", "capsul.pipeline.test.fake_morphologist.sulcigraphmorphometrybysubject.sulcigraphmorphometrybysubject")
        self.add_process("GreyWhiteClassification", "capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi.GreyWhiteClassificationHemi")
        self.add_process("GreyWhiteTopology", "capsul.pipeline.test.fake_morphologist.greywhitetopology.GreyWhiteTopology")
        self.add_process("GreyWhiteMesh", "capsul.pipeline.test.fake_morphologist.greywhitemesh.GreyWhiteMesh")
        self.add_process("SulciSkeleton", "capsul.pipeline.test.fake_morphologist.sulciskeleton.SulciSkeleton")
        self.add_process("PialMesh", "capsul.pipeline.test.fake_morphologist.pialmesh.PialMesh")
        self.add_process("CorticalFoldsGraph", "capsul.pipeline.test.fake_morphologist.sulcigraph.SulciGraph")
        self.add_process("SulciRecognition", "capsul.pipeline.test.fake_morphologist.sulcilabelling.SulciLabelling", make_optional=['recognition2000_model', 'recognition2000_model_hint', 'recognition2000_rate', 'recognition2000_stopRate', 'recognition2000_niterBelowStopProp', 'recognition2000_forbid_unknown_label', 'SPAM_recognition09_local_or_markovian', 'SPAM_recognition09_global_recognition_labels_translation_map', 'SPAM_recognition09_global_recognition_labels_priors', 'CNN_recognition19_roots', 'CNN_recognition19_model_file', 'CNN_recognition19_param_file', 'CNN_recognition19_rebuild_attributes', 'CNN_recognition19_skeleton', 'CNN_recognition19_allow_multithreading', 'CNN_recognition19_cuda', 'recognition2000_energy_plot_file'])
        self.add_process("GreyWhiteClassification_1", "capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi.GreyWhiteClassificationHemi")
        self.add_process("GreyWhiteTopology_1", "capsul.pipeline.test.fake_morphologist.greywhitetopology.GreyWhiteTopology")
        self.add_process("GreyWhiteMesh_1", "capsul.pipeline.test.fake_morphologist.greywhitemesh.GreyWhiteMesh")
        self.add_process("SulciSkeleton_1", "capsul.pipeline.test.fake_morphologist.sulciskeleton.SulciSkeleton")
        self.add_process("PialMesh_1", "capsul.pipeline.test.fake_morphologist.pialmesh.PialMesh")
        self.add_process("CorticalFoldsGraph_1", "capsul.pipeline.test.fake_morphologist.sulcigraph.SulciGraph")
        self.add_process("SulciRecognition_1", "capsul.pipeline.test.fake_morphologist.sulcilabelling.SulciLabelling", make_optional=['recognition2000_model', 'recognition2000_model_hint', 'recognition2000_rate', 'recognition2000_stopRate', 'recognition2000_niterBelowStopProp', 'recognition2000_forbid_unknown_label', 'SPAM_recognition09_local_or_markovian', 'SPAM_recognition09_global_recognition_labels_translation_map', 'SPAM_recognition09_global_recognition_labels_priors', 'CNN_recognition19_roots', 'CNN_recognition19_model_file', 'CNN_recognition19_param_file', 'CNN_recognition19_rebuild_attributes', 'CNN_recognition19_skeleton', 'CNN_recognition19_allow_multithreading', 'CNN_recognition19_cuda', 'recognition2000_energy_plot_file'])
        self.add_switch("select_Talairach", ['Normalization', 'StandardACPC'], ['Talairach_transform'], switch_value='StandardACPC', export_switch=False)
        self.add_switch("select_renormalization_commissures", ['initial', 'skull_stripped'], ['commissure_coordinates'], export_switch=False)
        self.add_switch("select_renormalization_transform", ['initial', 'skull_stripped'], ['Talairach_transform', 'MNI_transform'], export_switch=False)

        # links
        self.export_parameter("importation", "input", "t1mri")
        self.export_parameter("PrepareSubject", "StandardACPC_Anterior_Commissure", "anterior_commissure")
        self.export_parameter("PrepareSubject", "StandardACPC_Posterior_Commissure", "posterior_commissure")
        self.export_parameter("PrepareSubject", "StandardACPC_Interhemispheric_Point", "interhemispheric_point")
        self.export_parameter("PrepareSubject", "StandardACPC_Left_Hemisphere_Point", "left_hemisphere_point")
        self.export_parameter("CorticalFoldsGraph", "graph_version", "CorticalFoldsGraph_graph_version")
        self.add_link("CorticalFoldsGraph_graph_version->CorticalFoldsGraph_1.graph_version")
        self.export_parameter("PrepareSubject", "select_AC_PC_Or_Normalization", "select_Talairach")
        self.add_link("select_Talairach->select_Talairach.switch")
        self.export_parameter("Renorm", "Normalization_allow_flip_initial_MRI", "allow_flip_initial_MRI")
        self.add_link("allow_flip_initial_MRI->PrepareSubject.allow_flip_initial_MRI")
        self.export_parameter("Renorm", "Normalization_select_Normalization_pipeline")
        self.add_link("Normalization_select_Normalization_pipeline->PrepareSubject.Normalization_select_Normalization_pipeline")
        self.export_parameter("Renorm", "TalairachFromNormalization_normalized_referential", "PrepareSubject_TalairachFromNormalization_normalized_referential")
        self.add_link("PrepareSubject_TalairachFromNormalization_normalized_referential->PrepareSubject.TalairachFromNormalization_normalized_referential")
        self.export_parameter("Renorm", "TalairachFromNormalization_acpc_referential", "PrepareSubject_TalairachFromNormalization_acpc_referential")
        self.add_link("PrepareSubject_TalairachFromNormalization_acpc_referential->PrepareSubject.TalairachFromNormalization_acpc_referential")
        self.export_parameter("PrepareSubject", "TalairachFromNormalization_transform_chain_ACPC_to_Normalized", "PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized")
        self.add_link("PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized->Renorm.TalairachFromNormalization_transform_chain_ACPC_to_Normalized")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_allow_retry_initialization", "normalization_allow_retry_initialization")
        self.add_link("normalization_allow_retry_initialization->PrepareSubject.Normalization_NormalizeSPM_allow_retry_initialization")
        self.add_link("normalization_allow_retry_initialization->Renorm.Normalization_NormalizeFSL_allow_retry_initialization")
        self.add_link("normalization_allow_retry_initialization->Renorm.Normalization_NormalizeSPM_allow_retry_initialization")
        self.export_parameter("select_renormalization_commissures", "switch", "perform_skull_stripped_renormalization")
        self.add_link("perform_skull_stripped_renormalization->select_renormalization_transform.switch")
        self.export_parameter("GreyWhiteTopology_1", "fix_random_seed")
        self.add_link("fix_random_seed->PialMesh_1.fix_random_seed")
        self.add_link("fix_random_seed->SulciRecognition_1.fix_random_seed")
        self.add_link("fix_random_seed->SulciSkeleton.fix_random_seed")
        self.add_link("fix_random_seed->SulciSkeleton_1.fix_random_seed")
        self.add_link("fix_random_seed->GreyWhiteTopology.fix_random_seed")
        self.add_link("fix_random_seed->SplitBrain.fix_random_seed")
        self.add_link("fix_random_seed->BiasCorrection.fix_random_seed")
        self.add_link("fix_random_seed->BrainSegmentation.fix_random_seed")
        self.add_link("fix_random_seed->SulciRecognition.fix_random_seed")
        self.add_link("fix_random_seed->HistoAnalysis.fix_random_seed")
        self.add_link("fix_random_seed->GreyWhiteClassification_1.fix_random_seed")
        self.add_link("fix_random_seed->PialMesh.fix_random_seed")
        self.add_link("fix_random_seed->GreyWhiteClassification.fix_random_seed")
        self.export_parameter("GreyWhiteTopology_1", "version", "grey_white_topology_version")
        self.add_link("grey_white_topology_version->GreyWhiteTopology.version")
        self.export_parameter("PialMesh", "version", "pial_mesh_version")
        self.add_link("pial_mesh_version->PialMesh_1.version")
        self.export_parameter("SulciSkeleton", "version", "sulci_skeleton_version")
        self.add_link("sulci_skeleton_version->SulciSkeleton_1.version")
        self.export_parameter("CorticalFoldsGraph", "compute_fold_meshes")
        self.add_link("compute_fold_meshes->CorticalFoldsGraph_1.compute_fold_meshes")
        self.export_parameter("SulciRecognition", "CNN_recognition19_allow_multithreading", "allow_multithreading")
        self.add_link("allow_multithreading->CorticalFoldsGraph_1.allow_multithreading")
        self.add_link("allow_multithreading->CorticalFoldsGraph.allow_multithreading")
        self.add_link("allow_multithreading->SulciRecognition_1.CNN_recognition19_allow_multithreading")
        self.export_parameter("CorticalFoldsGraph_1", "write_cortex_mid_interface", "CorticalFoldsGraph_write_cortex_mid_interface")
        self.add_link("CorticalFoldsGraph_write_cortex_mid_interface->CorticalFoldsGraph.write_cortex_mid_interface")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_labels_translation_map", "SPAM_recognition_labels_translation_map")
        self.add_link("SPAM_recognition_labels_translation_map->SulciRecognition_1.SPAM_recognition09_global_recognition_labels_translation_map")
        self.export_parameter("SulciRecognition_1", "select_Sulci_Recognition", "select_sulci_recognition")
        self.add_link("select_sulci_recognition->SulciRecognition.select_Sulci_Recognition")
        self.export_parameter("SulciRecognition", "recognition2000_forbid_unknown_label", "sulci_recognition2000_forbid_unknown_label")
        self.add_link("sulci_recognition2000_forbid_unknown_label->SulciRecognition_1.recognition2000_forbid_unknown_label")
        self.export_parameter("SulciRecognition_1", "recognition2000_model_hint", "sulci_recognition2000_model_hint")
        self.add_link("sulci_recognition2000_model_hint->SulciRecognition.recognition2000_model_hint")
        self.export_parameter("SulciRecognition", "recognition2000_rate", "sulci_recognition2000_rate")
        self.add_link("sulci_recognition2000_rate->SulciRecognition_1.recognition2000_rate")
        self.export_parameter("SulciRecognition_1", "recognition2000_stopRate", "sulci_recognition2000_stop_rate")
        self.add_link("sulci_recognition2000_stop_rate->SulciRecognition.recognition2000_stopRate")
        self.export_parameter("SulciRecognition_1", "recognition2000_niterBelowStopProp", "sulci_recognition2000_niter_below_stop_prop")
        self.add_link("sulci_recognition2000_niter_below_stop_prop->SulciRecognition.recognition2000_niterBelowStopProp")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_or_markovian", "sulci_recognition_spam_local_or_markovian")
        self.add_link("sulci_recognition_spam_local_or_markovian->SulciRecognition_1.SPAM_recognition09_local_or_markovian")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_model_type", "sulci_recognition_spam_global_model_type")
        self.add_link("sulci_recognition_spam_global_model_type->SulciRecognition_1.SPAM_recognition09_global_recognition_model_type")
        self.export_parameter("SulciRecognition", "CNN_recognition19_rebuild_attributes", "rebuild_graph_attributes_after_split")
        self.add_link("rebuild_graph_attributes_after_split->SulciRecognition_1.CNN_recognition19_rebuild_attributes")
        self.export_parameter("SulcalMorphometry", "sulci_file", "sulcal_morphometry_sulci_file")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_NormalizeSPM", "spm_normalization_version")
        self.add_link("spm_normalization_version->PrepareSubject.Normalization_NormalizeSPM_NormalizeSPM")
        self.export_parameter("importation", "output_database", "importation_output_database")
        self.export_parameter("importation", "attributes_merging", "importation_attributes_merging")
        self.export_parameter("importation", "selected_attributes_from_header", "importation_selected_attributes_from_header")
        self.export_parameter("PrepareSubject", "StandardACPC_Normalised", "PrepareSubject_StandardACPC_Normalised")
        self.export_parameter("PrepareSubject", "StandardACPC_remove_older_MNI_normalization", "PrepareSubject_StandardACPC_remove_older_MNI_normalization")
        self.export_parameter("PrepareSubject", "StandardACPC_older_MNI_normalization", "PrepareSubject_StandardACPC_older_MNI_normalization")
        self.export_parameter("PrepareSubject", "Normalization_commissures_coordinates", "PrepareSubject_Normalization_commissures_coordinates")
        self.export_parameter("PrepareSubject", "Normalization_init_translation_origin", "PrepareSubject_Normalization_init_translation_origin")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_template", "PrepareSubject_Normalization_NormalizeFSL_template")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_alignment", "PrepareSubject_Normalization_NormalizeFSL_alignment")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_set_transformation_in_source_volume", "PrepareSubject_Normalization_NormalizeFSL_set_transformation_in_source_volume")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_cost_function")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "PrepareSubject_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_template", "PrepareSubject_Normalization_NormalizeSPM_template")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_voxel_size", "PrepareSubject_Normalization_NormalizeSPM_voxel_size")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_cutoff_option", "PrepareSubject_Normalization_NormalizeSPM_cutoff_option")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_nbiteration", "PrepareSubject_Normalization_NormalizeSPM_nbiteration")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_template", "PrepareSubject_Normalization_NormalizeBaladin_template")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", "PrepareSubject_Normalization_NormalizeBaladin_set_transformation_in_source_volume")
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_anatomical_template", "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template")
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", "PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc")
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_smoothing", "PrepareSubject_Normalization_Normalization_AimsMIRegister_smoothing")
        self.export_parameter("BiasCorrection", "sampling", "BiasCorrection_sampling")
        self.export_parameter("BiasCorrection", "field_rigidity", "BiasCorrection_field_rigidity")
        self.export_parameter("BiasCorrection", "zdir_multiply_regul", "BiasCorrection_zdir_multiply_regul")
        self.export_parameter("BiasCorrection", "wridges_weight", "BiasCorrection_wridges_weight")
        self.export_parameter("BiasCorrection", "ngrid", "BiasCorrection_ngrid")
        self.export_parameter("BiasCorrection", "background_threshold_auto", "BiasCorrection_background_threshold_auto")
        self.export_parameter("BiasCorrection", "delete_last_n_slices", "BiasCorrection_delete_last_n_slices")
        self.export_parameter("BiasCorrection", "mode", "BiasCorrection_mode")
        self.export_parameter("BiasCorrection", "write_field", "BiasCorrection_write_field")
        self.export_parameter("BiasCorrection", "write_hfiltered", "BiasCorrection_write_hfiltered")
        self.export_parameter("BiasCorrection", "write_wridges", "BiasCorrection_write_wridges")
        self.export_parameter("BiasCorrection", "variance_fraction", "BiasCorrection_variance_fraction")
        self.export_parameter("BiasCorrection", "write_variance", "BiasCorrection_write_variance")
        self.export_parameter("BiasCorrection", "edge_mask", "BiasCorrection_edge_mask")
        self.export_parameter("BiasCorrection", "write_edges", "BiasCorrection_write_edges")
        self.export_parameter("BiasCorrection", "write_meancurvature", "BiasCorrection_write_meancurvature")
        self.export_parameter("BiasCorrection", "modality", "BiasCorrection_modality")
        self.export_parameter("BiasCorrection", "use_existing_ridges", "BiasCorrection_use_existing_ridges")
        self.export_parameter("HistoAnalysis", "use_hfiltered", "HistoAnalysis_use_hfiltered")
        self.export_parameter("HistoAnalysis", "use_wridges", "HistoAnalysis_use_wridges")
        self.export_parameter("HistoAnalysis", "undersampling", "HistoAnalysis_undersampling")
        self.export_parameter("BrainSegmentation", "lesion_mask", "BrainSegmentation_lesion_mask")
        self.export_parameter("BrainSegmentation", "lesion_mask_mode", "BrainSegmentation_lesion_mask_mode")
        self.export_parameter("BrainSegmentation", "variant", "BrainSegmentation_variant")
        self.export_parameter("BrainSegmentation", "erosion_size", "BrainSegmentation_erosion_size")
        self.export_parameter("BrainSegmentation", "visu", "BrainSegmentation_visu")
        self.export_parameter("BrainSegmentation", "layer", "BrainSegmentation_layer")
        self.export_parameter("BrainSegmentation", "first_slice", "BrainSegmentation_first_slice")
        self.export_parameter("BrainSegmentation", "last_slice", "BrainSegmentation_last_slice")
        self.export_parameter("Renorm", "template", "Renorm_template")
        self.export_parameter("Renorm", "Normalization_init_translation_origin", "Renorm_Normalization_init_translation_origin")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_alignment", "Renorm_Normalization_NormalizeFSL_alignment")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_set_transformation_in_source_volume", "Renorm_Normalization_NormalizeFSL_set_transformation_in_source_volume")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_cost_function")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "Renorm_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_voxel_size", "Renorm_Normalization_NormalizeSPM_voxel_size")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_cutoff_option", "Renorm_Normalization_NormalizeSPM_cutoff_option")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_nbiteration", "Renorm_Normalization_NormalizeSPM_nbiteration")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource")
        self.export_parameter("Renorm", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", "Renorm_Normalization_NormalizeBaladin_set_transformation_in_source_volume")
        self.export_parameter("Renorm", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", "Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc")
        self.export_parameter("Renorm", "Normalization_Normalization_AimsMIRegister_smoothing", "Renorm_Normalization_Normalization_AimsMIRegister_smoothing")
        self.export_parameter("SplitBrain", "use_ridges", "SplitBrain_use_ridges")
        self.export_parameter("SplitBrain", "use_template", "SplitBrain_use_template")
        self.export_parameter("SplitBrain", "split_template", "SplitBrain_split_template")
        self.export_parameter("SplitBrain", "mode", "SplitBrain_mode")
        self.export_parameter("SplitBrain", "variant", "SplitBrain_variant")
        self.export_parameter("SplitBrain", "bary_factor", "SplitBrain_bary_factor")
        self.export_parameter("SplitBrain", "mult_factor", "SplitBrain_mult_factor")
        self.export_parameter("SplitBrain", "initial_erosion", "SplitBrain_initial_erosion")
        self.export_parameter("SplitBrain", "cc_min_size", "SplitBrain_cc_min_size")
        self.export_parameter("HeadMesh", "keep_head_mask", "HeadMesh_keep_head_mask")
        self.export_parameter("HeadMesh", "remove_mask", "HeadMesh_remove_mask")
        self.export_parameter("HeadMesh", "first_slice", "HeadMesh_first_slice")
        self.export_parameter("HeadMesh", "threshold", "HeadMesh_threshold")
        self.export_parameter("HeadMesh", "closing", "HeadMesh_closing")
        self.export_parameter("HeadMesh", "threshold_mode", "HeadMesh_threshold_mode")
        self.export_parameter("SulcalMorphometry", "use_attribute", "SulcalMorphometry_use_attribute")
        self.export_parameter("GreyWhiteClassification", "lesion_mask", "GreyWhiteClassification_lesion_mask")
        self.export_parameter("GreyWhiteClassification", "lesion_mask_mode", "GreyWhiteClassification_lesion_mask_mode")
        self.export_parameter("SulciRecognition", "recognition2000_model", "SulciRecognition_recognition2000_model")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_SPAM_recognition09_global_recognition_labels_priors")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_initial_transformation")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_model", "SulciRecognition_SPAM_recognition09_global_recognition_model")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_model", "SulciRecognition_SPAM_recognition09_local_recognition_model")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_SPAM_recognition09_local_recognition_local_referentials")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_SPAM_recognition09_local_recognition_direction_priors")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_SPAM_recognition09_local_recognition_angle_priors")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_SPAM_recognition09_local_recognition_translation_priors")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_model")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model")
        self.export_parameter("SulciRecognition", "CNN_recognition19_model_file", "SulciRecognition_CNN_recognition19_model_file")
        self.export_parameter("SulciRecognition", "CNN_recognition19_param_file", "SulciRecognition_CNN_recognition19_param_file")
        self.export_parameter("SulciRecognition", "CNN_recognition19_cuda", "SulciRecognition_CNN_recognition19_cuda")
        self.export_parameter("GreyWhiteClassification_1", "lesion_mask", "GreyWhiteClassification_1_lesion_mask")
        self.export_parameter("GreyWhiteClassification_1", "lesion_mask_mode", "GreyWhiteClassification_1_lesion_mask_mode")
        self.export_parameter("SulciRecognition_1", "recognition2000_model", "SulciRecognition_1_recognition2000_model")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_initial_transformation")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_model", "SulciRecognition_1_SPAM_recognition09_global_recognition_model")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_model", "SulciRecognition_1_SPAM_recognition09_local_recognition_model")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_model")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model")
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_model_file", "SulciRecognition_1_CNN_recognition19_model_file")
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_param_file", "SulciRecognition_1_CNN_recognition19_param_file")
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_cuda", "SulciRecognition_1_CNN_recognition19_cuda")
        self.add_link("importation.output->PrepareSubject.T1mri")
        self.export_parameter("importation", "output", "imported_t1mri")
        self.export_parameter("importation", "referential", "t1mri_referential")
        self.add_link("importation.referential->PrepareSubject.TalairachFromNormalization_source_referential")
        self.add_link("importation.referential->Renorm.TalairachFromNormalization_source_referential")
        self.add_link("PrepareSubject.commissure_coordinates->TalairachTransformation.commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->select_renormalization_commissures.initial_switch_commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->BiasCorrection.commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->Renorm.Normalization_commissures_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->BrainSegmentation.commissure_coordinates")
        self.export_parameter("PrepareSubject", "reoriented_t1mri")
        self.add_link("PrepareSubject.reoriented_t1mri->BiasCorrection.t1mri")
        self.add_link("PrepareSubject.reoriented_t1mri->Renorm.t1mri")
        self.add_link("PrepareSubject.talairach_transformation->select_Talairach.Normalization_switch_Talairach_transform")
        self.export_parameter("Renorm", "Normalization_normalized", "normalized_t1mri", weak_link=True)
        self.add_link("PrepareSubject.Normalization_normalized->normalized_t1mri", weak_link=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", "normalization_fsl_native_transformation_pass1")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_spm_transformation", "normalization_spm_native_transformation_pass1")
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", "normalization_baladin_native_transformation_pass1")
        self.add_link("PrepareSubject.normalization_transformation->select_renormalization_transform.initial_switch_MNI_transform")
        self.add_link("BiasCorrection.t1mri_nobias->HistoAnalysis.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->PialMesh_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SulciSkeleton_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteTopology.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->PialMesh.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->HeadMesh.t1mri_nobias")
        self.export_parameter("BiasCorrection", "t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteClassification.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteClassification_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SulciSkeleton.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteTopology_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->BrainSegmentation.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SplitBrain.t1mri_nobias")
        self.export_parameter("BiasCorrection", "b_field", "BiasCorrection_b_field")
        self.add_link("BiasCorrection.hfiltered->HistoAnalysis.hfiltered")
        self.export_parameter("BiasCorrection", "hfiltered", "BiasCorrection_hfiltered")
        self.add_link("BiasCorrection.white_ridges->BrainSegmentation.white_ridges")
        self.add_link("BiasCorrection.white_ridges->SplitBrain.white_ridges")
        self.add_link("BiasCorrection.white_ridges->HistoAnalysis.white_ridges")
        self.export_parameter("BiasCorrection", "white_ridges", "BiasCorrection_white_ridges")
        self.add_link("BiasCorrection.variance->BrainSegmentation.variance")
        self.export_parameter("BiasCorrection", "variance", "BiasCorrection_variance")
        self.export_parameter("BiasCorrection", "edges", "BiasCorrection_edges")
        self.add_link("BiasCorrection.edges->GreyWhiteClassification.edges")
        self.add_link("BiasCorrection.edges->GreyWhiteClassification_1.edges")
        self.add_link("BiasCorrection.edges->BrainSegmentation.edges")
        self.export_parameter("BiasCorrection", "meancurvature", "BiasCorrection_meancurvature")
        self.add_link("HistoAnalysis.histo_analysis->HeadMesh.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteClassification.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteClassification_1.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteTopology.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->SplitBrain.histo_analysis")
        self.export_parameter("HistoAnalysis", "histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->BrainSegmentation.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteTopology_1.histo_analysis")
        self.export_parameter("HistoAnalysis", "histo", "HistoAnalysis_histo")
        self.add_link("BrainSegmentation.brain_mask->SplitBrain.brain_mask")
        self.export_parameter("BrainSegmentation", "brain_mask", "BrainSegmentation_brain_mask")
        self.add_link("BrainSegmentation.brain_mask->Renorm.brain_mask")
        self.export_parameter("Renorm", "skull_stripped", "Renorm_skull_stripped")
        self.add_link("Renorm.transformation->select_renormalization_transform.skull_stripped_switch_MNI_transform")
        self.add_link("Renorm.talairach_transformation->select_renormalization_transform.skull_stripped_switch_Talairach_transform")
        self.add_link("Renorm.commissure_coordinates->select_renormalization_commissures.skull_stripped_switch_commissure_coordinates")
        self.add_link("Renorm.Normalization_normalized->normalized_t1mri", weak_link=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", "normalization_fsl_native_transformation")
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_spm_transformation", "normalization_spm_native_transformation")
        self.export_parameter("Renorm", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", "normalization_baladin_native_transformation")
        self.add_link("SplitBrain.split_brain->GreyWhiteClassification_1.split_brain")
        self.add_link("SplitBrain.split_brain->CorticalFoldsGraph.split_brain")
        self.add_link("SplitBrain.split_brain->CorticalFoldsGraph_1.split_brain")
        self.add_link("SplitBrain.split_brain->GreyWhiteClassification.split_brain")
        self.add_link("SplitBrain.split_brain->TalairachTransformation.split_mask")
        self.export_parameter("SplitBrain", "split_brain")
        self.add_link("TalairachTransformation.Talairach_transform->select_Talairach.StandardACPC_switch_Talairach_transform")
        self.export_parameter("HeadMesh", "head_mesh", "HeadMesh_head_mesh")
        self.export_parameter("HeadMesh", "head_mask", "HeadMesh_head_mask")
        self.export_parameter("SulcalMorphometry", "sulcal_morpho_measures")
        self.export_parameter("GreyWhiteClassification", "grey_white", "GreyWhiteClassification_grey_white")
        self.add_link("GreyWhiteClassification.grey_white->SulciSkeleton.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->PialMesh.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->GreyWhiteTopology.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->CorticalFoldsGraph.grey_white")
        self.add_link("GreyWhiteTopology.hemi_cortex->GreyWhiteMesh.hemi_cortex")
        self.add_link("GreyWhiteTopology.hemi_cortex->PialMesh.hemi_cortex")
        self.export_parameter("GreyWhiteTopology", "hemi_cortex", "GreyWhiteTopology_hemi_cortex")
        self.add_link("GreyWhiteTopology.hemi_cortex->CorticalFoldsGraph.hemi_cortex")
        self.add_link("GreyWhiteTopology.hemi_cortex->SulciSkeleton.hemi_cortex")
        self.export_parameter("GreyWhiteMesh", "white_mesh", "GreyWhiteMesh_white_mesh")
        self.add_link("GreyWhiteMesh.white_mesh->CorticalFoldsGraph.white_mesh")
        self.add_link("SulciSkeleton.skeleton->CorticalFoldsGraph.skeleton")
        self.add_link("SulciSkeleton.skeleton->SulciRecognition.CNN_recognition19_skeleton")
        self.add_link("SulciSkeleton.skeleton->PialMesh.skeleton")
        self.export_parameter("SulciSkeleton", "skeleton", "SulciSkeleton_skeleton")
        self.add_link("SulciSkeleton.roots->CorticalFoldsGraph.roots")
        self.export_parameter("SulciSkeleton", "roots", "SulciSkeleton_roots")
        self.add_link("SulciSkeleton.roots->SulciRecognition.CNN_recognition19_roots")
        self.add_link("PialMesh.pial_mesh->CorticalFoldsGraph.pial_mesh")
        self.export_parameter("PialMesh", "pial_mesh", "PialMesh_pial_mesh")
        self.export_parameter("CorticalFoldsGraph", "graph", "left_graph")
        self.add_link("CorticalFoldsGraph.graph->SulciRecognition.data_graph")
        self.export_parameter("CorticalFoldsGraph", "sulci_voronoi", "CorticalFoldsGraph_sulci_voronoi")
        self.export_parameter("CorticalFoldsGraph", "cortex_mid_interface", "CorticalFoldsGraph_cortex_mid_interface")
        self.add_link("SulciRecognition.output_graph->SulcalMorphometry.left_sulci_graph")
        self.export_parameter("SulciRecognition", "output_graph", "left_labelled_graph")
        self.export_parameter("SulciRecognition", "recognition2000_energy_plot_file", "SulciRecognition_recognition2000_energy_plot_file")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_global_recognition_posterior_probabilities")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_output_transformation")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_output_t1_to_global_transformation")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_local_recognition_posterior_probabilities")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_SPAM_recognition09_local_recognition_output_local_transformations")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_markovian_recognition_posterior_probabilities")
        self.add_link("GreyWhiteClassification_1.grey_white->PialMesh_1.grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->GreyWhiteTopology_1.grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->CorticalFoldsGraph_1.grey_white")
        self.export_parameter("GreyWhiteClassification_1", "grey_white", "GreyWhiteClassification_1_grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->SulciSkeleton_1.grey_white")
        self.export_parameter("GreyWhiteTopology_1", "hemi_cortex", "GreyWhiteTopology_1_hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->SulciSkeleton_1.hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->GreyWhiteMesh_1.hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->CorticalFoldsGraph_1.hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->PialMesh_1.hemi_cortex")
        self.export_parameter("GreyWhiteMesh_1", "white_mesh", "GreyWhiteMesh_1_white_mesh")
        self.add_link("GreyWhiteMesh_1.white_mesh->CorticalFoldsGraph_1.white_mesh")
        self.export_parameter("SulciSkeleton_1", "skeleton", "SulciSkeleton_1_skeleton")
        self.add_link("SulciSkeleton_1.skeleton->SulciRecognition_1.CNN_recognition19_skeleton")
        self.add_link("SulciSkeleton_1.skeleton->CorticalFoldsGraph_1.skeleton")
        self.add_link("SulciSkeleton_1.skeleton->PialMesh_1.skeleton")
        self.export_parameter("SulciSkeleton_1", "roots", "SulciSkeleton_1_roots")
        self.add_link("SulciSkeleton_1.roots->CorticalFoldsGraph_1.roots")
        self.add_link("SulciSkeleton_1.roots->SulciRecognition_1.CNN_recognition19_roots")
        self.export_parameter("PialMesh_1", "pial_mesh", "PialMesh_1_pial_mesh")
        self.add_link("PialMesh_1.pial_mesh->CorticalFoldsGraph_1.pial_mesh")
        self.add_link("CorticalFoldsGraph_1.graph->SulciRecognition_1.data_graph")
        self.export_parameter("CorticalFoldsGraph_1", "graph", "right_graph")
        self.export_parameter("CorticalFoldsGraph_1", "sulci_voronoi", "CorticalFoldsGraph_1_sulci_voronoi")
        self.export_parameter("CorticalFoldsGraph_1", "cortex_mid_interface", "CorticalFoldsGraph_1_cortex_mid_interface")
        self.add_link("SulciRecognition_1.output_graph->SulcalMorphometry.right_sulci_graph")
        self.export_parameter("SulciRecognition_1", "output_graph", "right_labelled_graph")
        self.export_parameter("SulciRecognition_1", "recognition2000_energy_plot_file", "SulciRecognition_1_recognition2000_energy_plot_file")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_global_recognition_posterior_probabilities")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_transformation")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_t1_to_global_transformation")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_local_recognition_posterior_probabilities")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_1_SPAM_recognition09_local_recognition_output_local_transformations")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_posterior_probabilities")
        self.add_link("select_Talairach.Talairach_transform->select_renormalization_transform.initial_switch_Talairach_transform")
        self.export_parameter("select_renormalization_commissures", "commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->SplitBrain.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->GreyWhiteClassification_1.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->CorticalFoldsGraph_1.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->CorticalFoldsGraph.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->GreyWhiteClassification.commissure_coordinates")
        self.add_link("select_renormalization_transform.Talairach_transform->CorticalFoldsGraph_1.talairach_transform")
        self.add_link("select_renormalization_transform.Talairach_transform->CorticalFoldsGraph.talairach_transform")
        self.export_parameter("select_renormalization_transform", "Talairach_transform")
        self.export_parameter("select_renormalization_transform", "MNI_transform")

        # pipeline steps
        self.add_pipeline_step("importation", ['importation'])
        self.add_pipeline_step("orientation", ['PrepareSubject', 'TalairachTransformation'])
        self.add_pipeline_step("bias_correction", ['BiasCorrection'])
        self.add_pipeline_step("histogram_analysis", ['HistoAnalysis'])
        self.add_pipeline_step("brain_extraction", ['BrainSegmentation'])
        self.add_pipeline_step("renormalization", ['Renorm'])
        self.add_pipeline_step("hemispheres_split", ['SplitBrain'])
        self.add_pipeline_step("head_mesh", ['HeadMesh'])
        self.add_pipeline_step("grey_white_segmentation", ['GreyWhiteClassification', 'GreyWhiteTopology', 'GreyWhiteClassification_1', 'GreyWhiteTopology_1'])
        self.add_pipeline_step("white_mesh", ['GreyWhiteMesh', 'GreyWhiteMesh_1'])
        self.add_pipeline_step("pial_mesh", ['PialMesh', 'PialMesh_1'])
        self.add_pipeline_step("sulci", ['SulciSkeleton', 'CorticalFoldsGraph', 'SulciSkeleton_1', 'CorticalFoldsGraph_1'])
        self.add_pipeline_step("sulci_labelling", ['SulciRecognition', 'SulciRecognition_1'])
        self.add_pipeline_step("sulcal_morphometry", ['SulcalMorphometry'])

        # default and initial values
        self.select_Talairach = 'Normalization'
        self.importation_output_database = '/home/dr144257/data/baseessai'
        self.importation_attributes_merging = 'BrainVisa'
        self.importation_selected_attributes_from_header = []
        self.PrepareSubject_StandardACPC_Normalised = 'No'
        self.allow_flip_initial_MRI = False
        self.PrepareSubject_StandardACPC_remove_older_MNI_normalization = True
        self.PrepareSubject_Normalization_NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_cost_function = 'corratio'
        self.PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function = 'corratio'
        self.PrepareSubject_Normalization_init_translation_origin = 0
        self.PrepareSubject_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template = 0
        self.PrepareSubject_Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target = 'MNI template'
        self.PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource = False
        self.PrepareSubject_Normalization_NormalizeSPM_template = '/host/usr/local/spm12-standalone/spm12_mcr/spm12/toolbox/OldNorm/T1.nii'
        self.PrepareSubject_Normalization_NormalizeSPM_voxel_size = '[1 1 1]'
        self.PrepareSubject_Normalization_NormalizeSPM_cutoff_option = 25
        self.PrepareSubject_Normalization_NormalizeSPM_nbiteration = 16
        self.PrepareSubject_Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc = '/casa/host/build/share/brainvisa-share-5.1/transformation/talairach_TO_spm_template_novoxels.trm'
        self.PrepareSubject_Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.PrepareSubject_TalairachFromNormalization_acpc_referential = '/casa/host/build/share/brainvisa-share-5.1/registration/Talairach-AC_PC-Anatomist.referential'
        self.BiasCorrection_sampling = 16.0
        self.BiasCorrection_field_rigidity = 20.0
        self.BiasCorrection_zdir_multiply_regul = 0.5
        self.BiasCorrection_wridges_weight = 20.0
        self.BiasCorrection_ngrid = 2
        self.BiasCorrection_background_threshold_auto = 'corners'
        self.BiasCorrection_delete_last_n_slices = 'auto (AC/PC Points needed)'
        self.BiasCorrection_mode = 'write_minimal'
        self.BiasCorrection_write_field = 'no'
        self.BiasCorrection_write_hfiltered = 'yes'
        self.BiasCorrection_write_wridges = 'yes'
        self.BiasCorrection_variance_fraction = 75
        self.BiasCorrection_write_variance = 'yes'
        self.BiasCorrection_edge_mask = 'yes'
        self.BiasCorrection_write_edges = 'yes'
        self.BiasCorrection_write_meancurvature = 'no'
        self.fix_random_seed = False
        self.BiasCorrection_modality = 'T1'
        self.BiasCorrection_use_existing_ridges = False
        self.HistoAnalysis_use_hfiltered = True
        self.HistoAnalysis_use_wridges = True
        self.HistoAnalysis_undersampling = 'iteration'
        self.BrainSegmentation_lesion_mask_mode = 'e'
        self.BrainSegmentation_variant = '2010'
        self.BrainSegmentation_erosion_size = 1.8
        self.BrainSegmentation_visu = 'No'
        self.BrainSegmentation_layer = 0
        self.BrainSegmentation_first_slice = 0
        self.BrainSegmentation_last_slice = 0
        self.Renorm_Normalization_NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.Renorm_Normalization_NormalizeFSL_NormalizeFSL_cost_function = 'corratio'
        self.Renorm_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function = 'corratio'
        self.Renorm_Normalization_init_translation_origin = 0
        self.Renorm_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template = 0
        self.Renorm_Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target = 'MNI template'
        self.Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource = False
        self.Renorm_Normalization_NormalizeSPM_voxel_size = '[1 1 1]'
        self.Renorm_Normalization_NormalizeSPM_cutoff_option = 25
        self.Renorm_Normalization_NormalizeSPM_nbiteration = 16
        self.Renorm_Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc = '/casa/host/build/share/brainvisa-share-5.1/transformation/talairach_TO_spm_template_novoxels.trm'
        self.Renorm_Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.SplitBrain_use_ridges = True
        self.SplitBrain_use_template = True
        self.SplitBrain_split_template = '/casa/host/build/share/brainvisa-share-5.1/hemitemplate/closedvoronoi.ima'
        self.SplitBrain_mode = 'Watershed (2011)'
        self.SplitBrain_variant = 'GW Barycentre'
        self.SplitBrain_bary_factor = 0.6
        self.SplitBrain_mult_factor = 2
        self.SplitBrain_initial_erosion = 2.0
        self.SplitBrain_cc_min_size = 500
        self.HeadMesh_keep_head_mask = False
        self.HeadMesh_threshold_mode = 'auto'
        self.sulcal_morphometry_sulci_file = '/casa/host/build/share/brainvisa-share-5.1/nomenclature/translation/sulci_default_list.json'
        self.SulcalMorphometry_use_attribute = 'label'
        self.GreyWhiteClassification_lesion_mask_mode = 'e'
        self.grey_white_topology_version = '2'
        self.sulci_skeleton_version = '2'
        self.pial_mesh_version = '2'
        self.compute_fold_meshes = True
        self.allow_multithreading = True
        self.CorticalFoldsGraph_graph_version = '3.1'
        self.CorticalFoldsGraph_write_cortex_mid_interface = False
        self.SulciRecognition_recognition2000_model = '/casa/host/build/share/brainvisa-share-5.1/models/models_2008/discriminative_models/3.0/Lfolds_noroots/Lfolds_noroots.arg'
        self.sulci_recognition2000_model_hint = 0
        self.sulci_recognition2000_rate = 0.98
        self.sulci_recognition2000_stop_rate = 0.05
        self.sulci_recognition2000_niter_below_stop_prop = 1
        self.sulci_recognition2000_forbid_unknown_label = False
        self.sulci_recognition_spam_global_model_type = 'Global registration'
        self.SPAM_recognition_labels_translation_map = '/casa/host/build/share/brainvisa-share-5.1/nomenclature/translation/sulci_model_2008.trl'
        self.select_sulci_recognition = 'CNN_recognition19'
        self.GreyWhiteClassification_1_lesion_mask_mode = 'e'
        self.SulciRecognition_1_recognition2000_model = '/casa/host/build/share/brainvisa-share-5.1/models/models_2008/discriminative_models/3.0/Lfolds_noroots/Lfolds_noroots.arg'
        self.perform_skull_stripped_renormalization = 'skull_stripped'
        self.normalization_allow_retry_initialization = True

        # nodes positions
        self.node_position = {
            "BiasCorrection": (2149.0, 1157.0),
            "BrainSegmentation": (2746.0, 2089.0),
            "CorticalFoldsGraph": (6470.0, 2061.0),
            "CorticalFoldsGraph_1": (6470.0, 608.0),
            "GreyWhiteClassification": (4973.0, 1982.0),
            "GreyWhiteClassification_1": (4973.0, 1012.0),
            "GreyWhiteMesh": (6234.0, 1785.0),
            "GreyWhiteMesh_1": (6234.0, 530.0),
            "GreyWhiteTopology": (5397.0, 1911.0),
            "GreyWhiteTopology_1": (5397.0, 573.0),
            "HeadMesh": (2767.0, 565.0),
            "HistoAnalysis": (2472.0, 1040.0),
            "PialMesh": (6222.0, 1910.0),
            "PialMesh_1": (6222.0, 690.0),
            "PrepareSubject": (1062.0, 2159.0),
            "Renorm": (3048.0, 2368.0),
            "SplitBrain": (4649.0, 1261.0),
            "SulcalMorphometry": (7843.0, 2278.0),
            "SulciRecognition": (6854.0, 1954.0),
            "SulciRecognition_1": (6854.0, 636.0),
            "SulciSkeleton": (5873.0, 2387.0),
            "SulciSkeleton_1": (5873.0, 875.0),
            "TalairachTransformation": (4943.0, 3313.0),
            "importation": (703.0, 2820.0),
            "inputs": (0.0, 0.0),
            "outputs": (8179.0, 700.0),
            "select_Talairach": (5297.0, 3419.0),
            "select_renormalization_commissures": (4134.0, 2217.0),
            "select_renormalization_transform": (5762.0, 3201.0),
        }

        self.do_autoexport_nodes_parameters = False
