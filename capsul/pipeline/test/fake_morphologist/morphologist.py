# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class Morphologist(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("importation", "capsul.pipeline.test.fake_morphologist.importt1mri.ImportT1MRI")
        self.nodes["importation"].set_plug_value("input", traits.Undefined)
        self.add_process("PrepareSubject", "capsul.pipeline.test.fake_morphologist.brainorientation.BrainOrientation")
        self.nodes["PrepareSubject"].process.nodes["Normalization"].process.nodes["NormalizeBaladin"].enabled = False
        self.nodes["PrepareSubject"].process.nodes["Normalization"].process.nodes["NormalizeSPM"].process.nodes["normalization_t1_spm8_reinit"].enabled = False
        self.nodes["PrepareSubject"].process.nodes["Normalization"].process.nodes["NormalizeBaladin"].process.nodes["ReorientAnatomy"].enabled = False
        self.nodes["PrepareSubject"].process.nodes_activation = {'StandardACPC': True, 'Normalization': True, 'TalairachFromNormalization': True}
        self.add_process("BiasCorrection", "capsul.pipeline.test.fake_morphologist.t1biascorrection.T1BiasCorrection")
        self.nodes["BiasCorrection"].set_plug_value("t1mri", traits.Undefined)
        self.nodes["BiasCorrection"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.add_process("HistoAnalysis", "capsul.pipeline.test.fake_morphologist.histoanalysis.HistoAnalysis")
        self.nodes["HistoAnalysis"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["HistoAnalysis"].set_plug_value("hfiltered", traits.Undefined)
        self.nodes["HistoAnalysis"].set_plug_value("white_ridges", traits.Undefined)
        self.add_process("BrainSegmentation", "capsul.pipeline.test.fake_morphologist.brainsegmentation.BrainSegmentation")
        self.nodes["BrainSegmentation"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("histo_analysis", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("variance", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("edges", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("white_ridges", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["BrainSegmentation"].set_plug_value("lesion_mask", traits.Undefined)
        self.add_process("Renorm", "capsul.pipeline.test.fake_morphologist.normalizationskullstripped.NormalizationSkullStripped")
        self.nodes["Renorm"].process.nodes["Normalization"].process.nodes["select_Normalization_pipeline"].plugs["reoriented_t1mri"].optional = True

        self.nodes["Renorm"].process.nodes["Normalization"].process.nodes["NormalizeSPM"].process.nodes["normalization_t1_spm8_reinit"].enabled = False
        self.nodes["Renorm"].process.nodes["Normalization"].process.nodes["NormalizeBaladin"].process.nodes["ReorientAnatomy"].enabled = False
        self.nodes["Renorm"].process.nodes_activation = {'SkullStripping': True, 'Normalization': True, 'TalairachFromNormalization': True}
        self.add_process("SplitBrain", "capsul.pipeline.test.fake_morphologist.splitbrain.SplitBrain")
        self.nodes["SplitBrain"].set_plug_value("brain_mask", traits.Undefined)
        self.nodes["SplitBrain"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["SplitBrain"].set_plug_value("histo_analysis", traits.Undefined)
        self.nodes["SplitBrain"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["SplitBrain"].set_plug_value("white_ridges", traits.Undefined)
        self.add_process("TalairachTransformation", "capsul.pipeline.test.fake_morphologist.talairachtransformation.TalairachTransformation")
        self.nodes["TalairachTransformation"].set_plug_value("split_mask", traits.Undefined)
        self.nodes["TalairachTransformation"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.add_process("HeadMesh", "capsul.pipeline.test.fake_morphologist.scalpmesh.ScalpMesh")
        self.nodes["HeadMesh"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["HeadMesh"].set_plug_value("histo_analysis", traits.Undefined)
        self.nodes["HeadMesh"].set_plug_value("remove_mask", traits.Undefined)
        self.nodes["HeadMesh"].set_plug_value("first_slice", traits.Undefined)
        self.nodes["HeadMesh"].set_plug_value("threshold", traits.Undefined)
        self.nodes["HeadMesh"].set_plug_value("closing", traits.Undefined)
        self.nodes["HeadMesh"].process.first_slice = traits.Undefined
        self.nodes["HeadMesh"].process.threshold = traits.Undefined
        self.nodes["HeadMesh"].process.closing = traits.Undefined
        self.add_process("SulcalMorphometry", "capsul.pipeline.test.fake_morphologist.sulcigraphmorphometrybysubject.sulcigraphmorphometrybysubject")
        self.nodes["SulcalMorphometry"].set_plug_value("left_sulci_graph", traits.Undefined)
        self.nodes["SulcalMorphometry"].set_plug_value("right_sulci_graph", traits.Undefined)
        self.add_process("GreyWhiteClassification", "capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi.GreyWhiteClassificationHemi")
        self.nodes["GreyWhiteClassification"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["GreyWhiteClassification"].set_plug_value("histo_analysis", traits.Undefined)
        self.nodes["GreyWhiteClassification"].set_plug_value("split_brain", traits.Undefined)
        self.nodes["GreyWhiteClassification"].set_plug_value("edges", traits.Undefined)
        self.nodes["GreyWhiteClassification"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["GreyWhiteClassification"].set_plug_value("lesion_mask", traits.Undefined)
        self.add_process("GreyWhiteTopology", "capsul.pipeline.test.fake_morphologist.greywhitetopology.GreyWhiteTopology")
        self.nodes["GreyWhiteTopology"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["GreyWhiteTopology"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["GreyWhiteTopology"].set_plug_value("histo_analysis", traits.Undefined)
        self.add_process("GreyWhiteMesh", "capsul.pipeline.test.fake_morphologist.greywhitemesh.GreyWhiteMesh")
        self.nodes["GreyWhiteMesh"].set_plug_value("hemi_cortex", traits.Undefined)
        self.add_process("SulciSkeleton", "capsul.pipeline.test.fake_morphologist.sulciskeleton.SulciSkeleton")
        self.nodes["SulciSkeleton"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["SulciSkeleton"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["SulciSkeleton"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.add_process("PialMesh", "capsul.pipeline.test.fake_morphologist.pialmesh.PialMesh")
        self.nodes["PialMesh"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["PialMesh"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["PialMesh"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["PialMesh"].set_plug_value("skeleton", traits.Undefined)
        self.add_process("CorticalFoldsGraph", "capsul.pipeline.test.fake_morphologist.sulcigraph.SulciGraph")
        self.nodes["CorticalFoldsGraph"].set_plug_value("skeleton", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("roots", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("split_brain", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("white_mesh", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("pial_mesh", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["CorticalFoldsGraph"].set_plug_value("talairach_transform", traits.Undefined)
        self.add_process("SulciRecognition", "capsul.pipeline.test.fake_morphologist.sulcilabelling.SulciLabelling")
        self.nodes["SulciRecognition"].process.nodes_activation = {'recognition2000': True, 'SPAM_recognition09': True, 'CNN_recognition19': True}
        self.add_process("GreyWhiteClassification_1", "capsul.pipeline.test.fake_morphologist.greywhiteclassificationhemi.GreyWhiteClassificationHemi")
        self.nodes["GreyWhiteClassification_1"].set_plug_value("side", 'right')
        self.nodes["GreyWhiteClassification_1"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].set_plug_value("histo_analysis", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].set_plug_value("split_brain", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].set_plug_value("edges", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].set_plug_value("lesion_mask", traits.Undefined)
        self.nodes["GreyWhiteClassification_1"].process.side = 'right'
        self.add_process("GreyWhiteTopology_1", "capsul.pipeline.test.fake_morphologist.greywhitetopology.GreyWhiteTopology")
        self.nodes["GreyWhiteTopology_1"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["GreyWhiteTopology_1"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["GreyWhiteTopology_1"].set_plug_value("histo_analysis", traits.Undefined)
        self.add_process("GreyWhiteMesh_1", "capsul.pipeline.test.fake_morphologist.greywhitemesh.GreyWhiteMesh")
        self.nodes["GreyWhiteMesh_1"].set_plug_value("hemi_cortex", traits.Undefined)
        self.add_process("SulciSkeleton_1", "capsul.pipeline.test.fake_morphologist.sulciskeleton.SulciSkeleton")
        self.nodes["SulciSkeleton_1"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["SulciSkeleton_1"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["SulciSkeleton_1"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.add_process("PialMesh_1", "capsul.pipeline.test.fake_morphologist.pialmesh.PialMesh")
        self.nodes["PialMesh_1"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["PialMesh_1"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["PialMesh_1"].set_plug_value("t1mri_nobias", traits.Undefined)
        self.nodes["PialMesh_1"].set_plug_value("skeleton", traits.Undefined)
        self.add_process("CorticalFoldsGraph_1", "capsul.pipeline.test.fake_morphologist.sulcigraph.SulciGraph")
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("skeleton", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("roots", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("grey_white", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("hemi_cortex", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("split_brain", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("white_mesh", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("pial_mesh", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("commissure_coordinates", traits.Undefined)
        self.nodes["CorticalFoldsGraph_1"].set_plug_value("talairach_transform", traits.Undefined)
        self.add_process("SulciRecognition_1", "capsul.pipeline.test.fake_morphologist.sulcilabelling.SulciLabelling")
        self.nodes["SulciRecognition_1"].process.nodes_activation = {'recognition2000': True, 'SPAM_recognition09': True, 'CNN_recognition19': True}
        self.add_switch("select_Talairach", ['StandardACPC', 'Normalization'], ['Talairach_transform'], output_types=[traits.File(output=True, optional=False)], switch_value='Normalization', export_switch=False)
        self.add_switch("select_renormalization_commissures", ['initial', 'skull_stripped'], ['commissure_coordinates'], output_types=[traits.File(output=True, optional=False)], switch_value='skull_stripped', export_switch=False)
        self.add_switch("select_renormalization_transform", ['initial', 'skull_stripped'], ['Talairach_transform', 'MNI_transform'], output_types=[traits.File(output=True, optional=False), traits.File(output=True, optional=False)], switch_value='skull_stripped', export_switch=False)

        # links
        self.export_parameter("importation", "input", "t1mri", is_optional=False)
        self.export_parameter("select_Talairach", "switch", "select_Talairach", is_optional=False)
        self.add_link("select_Talairach->PrepareSubject.select_AC_PC_Or_Normalization")
        self.export_parameter("PrepareSubject", "Normalization_select_Normalization_pipeline", is_optional=True)
        self.add_link("Normalization_select_Normalization_pipeline->Renorm.Normalization_select_Normalization_pipeline")
        self.export_parameter("PrepareSubject", "StandardACPC_Anterior_Commissure", "anterior_commissure", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_Posterior_Commissure", "posterior_commissure", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_Interhemispheric_Point", "interhemispheric_point", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_Left_Hemisphere_Point", "left_hemisphere_point", is_optional=True)
        self.export_parameter("CorticalFoldsGraph_1", "graph_version", "CorticalFoldsGraph_graph_version", is_optional=False)
        self.add_link("CorticalFoldsGraph_graph_version->CorticalFoldsGraph.graph_version")
        self.export_parameter("PrepareSubject", "allow_flip_initial_MRI", is_optional=False)
        self.add_link("allow_flip_initial_MRI->Renorm.Normalization_allow_flip_initial_MRI")
        self.export_parameter("PrepareSubject", "TalairachFromNormalization_normalized_referential", "PrepareSubject_TalairachFromNormalization_normalized_referential", is_optional=True)
        self.add_link("PrepareSubject_TalairachFromNormalization_normalized_referential->Renorm.TalairachFromNormalization_normalized_referential")
        self.export_parameter("Renorm", "TalairachFromNormalization_acpc_referential", "PrepareSubject_TalairachFromNormalization_acpc_referential", is_optional=True)
        self.add_link("PrepareSubject_TalairachFromNormalization_acpc_referential->PrepareSubject.TalairachFromNormalization_acpc_referential")
        self.export_parameter("Renorm", "TalairachFromNormalization_transform_chain_ACPC_to_Normalized", "PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized", is_optional=True)
        self.add_link("PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized->PrepareSubject.TalairachFromNormalization_transform_chain_ACPC_to_Normalized")
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_allow_retry_initialization", "normalization_allow_retry_initialization", is_optional=False)
        self.add_link("normalization_allow_retry_initialization->Renorm.Normalization_NormalizeSPM_allow_retry_initialization")
        self.add_link("normalization_allow_retry_initialization->PrepareSubject.Normalization_NormalizeFSL_allow_retry_initialization")
        self.add_link("normalization_allow_retry_initialization->PrepareSubject.Normalization_NormalizeSPM_allow_retry_initialization")
        self.export_parameter("select_renormalization_transform", "switch", "perform_skull_stripped_renormalization", is_optional=False)
        self.add_link("perform_skull_stripped_renormalization->select_renormalization_commissures.switch")
        self.export_parameter("GreyWhiteTopology_1", "fix_random_seed", is_optional=False)
        self.add_link("fix_random_seed->GreyWhiteClassification.fix_random_seed")
        self.add_link("fix_random_seed->HistoAnalysis.fix_random_seed")
        self.add_link("fix_random_seed->SulciSkeleton_1.fix_random_seed")
        self.add_link("fix_random_seed->SulciRecognition.fix_random_seed")
        self.add_link("fix_random_seed->SulciRecognition_1.fix_random_seed")
        self.add_link("fix_random_seed->BiasCorrection.fix_random_seed")
        self.add_link("fix_random_seed->PialMesh_1.fix_random_seed")
        self.add_link("fix_random_seed->SulciSkeleton.fix_random_seed")
        self.add_link("fix_random_seed->BrainSegmentation.fix_random_seed")
        self.add_link("fix_random_seed->PialMesh.fix_random_seed")
        self.add_link("fix_random_seed->GreyWhiteClassification_1.fix_random_seed")
        self.add_link("fix_random_seed->SplitBrain.fix_random_seed")
        self.add_link("fix_random_seed->GreyWhiteTopology.fix_random_seed")
        self.export_parameter("GreyWhiteTopology", "version", "grey_white_topology_version", is_optional=False)
        self.add_link("grey_white_topology_version->GreyWhiteTopology_1.version")
        self.export_parameter("PialMesh_1", "version", "pial_mesh_version", is_optional=False)
        self.add_link("pial_mesh_version->PialMesh.version")
        self.export_parameter("SulciSkeleton", "version", "sulci_skeleton_version", is_optional=False)
        self.add_link("sulci_skeleton_version->SulciSkeleton_1.version")
        self.export_parameter("CorticalFoldsGraph", "compute_fold_meshes", is_optional=False)
        self.add_link("compute_fold_meshes->CorticalFoldsGraph_1.compute_fold_meshes")
        self.export_parameter("SulciRecognition", "CNN_recognition19_allow_multithreading", "allow_multithreading", is_optional=False)
        self.add_link("allow_multithreading->CorticalFoldsGraph.allow_multithreading")
        self.add_link("allow_multithreading->SulciRecognition_1.CNN_recognition19_allow_multithreading")
        self.add_link("allow_multithreading->CorticalFoldsGraph_1.allow_multithreading")
        self.export_parameter("CorticalFoldsGraph_1", "write_cortex_mid_interface", "CorticalFoldsGraph_write_cortex_mid_interface", is_optional=False)
        self.add_link("CorticalFoldsGraph_write_cortex_mid_interface->CorticalFoldsGraph.write_cortex_mid_interface")
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_labels_translation_map", "SPAM_recognition_labels_translation_map", is_optional=True)
        self.add_link("SPAM_recognition_labels_translation_map->SulciRecognition_1.SPAM_recognition09_global_recognition_labels_translation_map")
        self.export_parameter("SulciRecognition", "select_Sulci_Recognition", "select_sulci_recognition", is_optional=False)
        self.add_link("select_sulci_recognition->SulciRecognition_1.select_Sulci_Recognition")
        self.export_parameter("SulciRecognition", "recognition2000_forbid_unknown_label", "sulci_recognition2000_forbid_unknown_label", is_optional=True)
        self.add_link("sulci_recognition2000_forbid_unknown_label->SulciRecognition_1.recognition2000_forbid_unknown_label")
        self.export_parameter("SulciRecognition", "recognition2000_model_hint", "sulci_recognition2000_model_hint", is_optional=True)
        self.add_link("sulci_recognition2000_model_hint->SulciRecognition_1.recognition2000_model_hint")
        self.export_parameter("SulciRecognition_1", "recognition2000_rate", "sulci_recognition2000_rate", is_optional=True)
        self.add_link("sulci_recognition2000_rate->SulciRecognition.recognition2000_rate")
        self.export_parameter("SulciRecognition", "recognition2000_stopRate", "sulci_recognition2000_stop_rate", is_optional=True)
        self.add_link("sulci_recognition2000_stop_rate->SulciRecognition_1.recognition2000_stopRate")
        self.export_parameter("SulciRecognition", "recognition2000_niterBelowStopProp", "sulci_recognition2000_niter_below_stop_prop", is_optional=True)
        self.add_link("sulci_recognition2000_niter_below_stop_prop->SulciRecognition_1.recognition2000_niterBelowStopProp")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_or_markovian", "sulci_recognition_spam_local_or_markovian", is_optional=True)
        self.add_link("sulci_recognition_spam_local_or_markovian->SulciRecognition.SPAM_recognition09_local_or_markovian")
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_model_type", "sulci_recognition_spam_global_model_type", is_optional=True)
        self.add_link("sulci_recognition_spam_global_model_type->SulciRecognition.SPAM_recognition09_global_recognition_model_type")
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_rebuild_attributes", "rebuild_graph_attributes_after_split", is_optional=True)
        self.add_link("rebuild_graph_attributes_after_split->SulciRecognition.CNN_recognition19_rebuild_attributes")
        self.export_parameter("SulcalMorphometry", "sulci_file", "sulcal_morphometry_sulci_file", is_optional=False)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_NormalizeSPM", "spm_normalization_version", is_optional=True)
        self.add_link("spm_normalization_version->PrepareSubject.Normalization_NormalizeSPM_NormalizeSPM")
        self.export_parameter("importation", "output_database", "importation_output_database", is_optional=True)
        self.export_parameter("importation", "attributes_merging", "importation_attributes_merging", is_optional=True)
        self.export_parameter("importation", "selected_attributes_from_header", "importation_selected_attributes_from_header", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_Normalised", "PrepareSubject_StandardACPC_Normalised", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_remove_older_MNI_normalization", "PrepareSubject_StandardACPC_remove_older_MNI_normalization", is_optional=True)
        self.export_parameter("PrepareSubject", "StandardACPC_older_MNI_normalization", "PrepareSubject_StandardACPC_older_MNI_normalization", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_commissures_coordinates", "PrepareSubject_Normalization_commissures_coordinates", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_init_translation_origin", "PrepareSubject_Normalization_init_translation_origin", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_template", "PrepareSubject_Normalization_NormalizeFSL_template", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_alignment", "PrepareSubject_Normalization_NormalizeFSL_alignment", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_set_transformation_in_source_volume", "PrepareSubject_Normalization_NormalizeFSL_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_cost_function", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "PrepareSubject_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_template", "PrepareSubject_Normalization_NormalizeSPM_template", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_voxel_size", "PrepareSubject_Normalization_NormalizeSPM_voxel_size", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_cutoff_option", "PrepareSubject_Normalization_NormalizeSPM_cutoff_option", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_nbiteration", "PrepareSubject_Normalization_NormalizeSPM_nbiteration", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_template", "PrepareSubject_Normalization_NormalizeBaladin_template", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", "PrepareSubject_Normalization_NormalizeBaladin_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_anatomical_template", "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", "PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_Normalization_AimsMIRegister_smoothing", "PrepareSubject_Normalization_Normalization_AimsMIRegister_smoothing", is_optional=True)
        self.export_parameter("BiasCorrection", "sampling", "BiasCorrection_sampling", is_optional=True)
        self.export_parameter("BiasCorrection", "field_rigidity", "BiasCorrection_field_rigidity", is_optional=True)
        self.export_parameter("BiasCorrection", "zdir_multiply_regul", "BiasCorrection_zdir_multiply_regul", is_optional=True)
        self.export_parameter("BiasCorrection", "wridges_weight", "BiasCorrection_wridges_weight", is_optional=True)
        self.export_parameter("BiasCorrection", "ngrid", "BiasCorrection_ngrid", is_optional=True)
        self.export_parameter("BiasCorrection", "delete_last_n_slices", "BiasCorrection_delete_last_n_slices", is_optional=True)
        self.export_parameter("BiasCorrection", "mode", "BiasCorrection_mode", is_optional=True)
        self.export_parameter("BiasCorrection", "write_field", "BiasCorrection_write_field", is_optional=True)
        self.export_parameter("BiasCorrection", "write_hfiltered", "BiasCorrection_write_hfiltered", is_optional=True)
        self.export_parameter("BiasCorrection", "write_wridges", "BiasCorrection_write_wridges", is_optional=True)
        self.export_parameter("BiasCorrection", "variance_fraction", "BiasCorrection_variance_fraction", is_optional=True)
        self.export_parameter("BiasCorrection", "write_variance", "BiasCorrection_write_variance", is_optional=True)
        self.export_parameter("BiasCorrection", "edge_mask", "BiasCorrection_edge_mask", is_optional=True)
        self.export_parameter("BiasCorrection", "write_edges", "BiasCorrection_write_edges", is_optional=True)
        self.export_parameter("BiasCorrection", "write_meancurvature", "BiasCorrection_write_meancurvature", is_optional=True)
        self.export_parameter("BiasCorrection", "modality", "BiasCorrection_modality", is_optional=True)
        self.export_parameter("BiasCorrection", "use_existing_ridges", "BiasCorrection_use_existing_ridges", is_optional=True)
        self.export_parameter("HistoAnalysis", "use_hfiltered", "HistoAnalysis_use_hfiltered", is_optional=True)
        self.export_parameter("HistoAnalysis", "use_wridges", "HistoAnalysis_use_wridges", is_optional=True)
        self.export_parameter("HistoAnalysis", "undersampling", "HistoAnalysis_undersampling", is_optional=True)
        self.export_parameter("BrainSegmentation", "lesion_mask", "BrainSegmentation_lesion_mask", is_optional=True)
        self.export_parameter("BrainSegmentation", "lesion_mask_mode", "BrainSegmentation_lesion_mask_mode", is_optional=True)
        self.export_parameter("BrainSegmentation", "variant", "BrainSegmentation_variant", is_optional=True)
        self.export_parameter("BrainSegmentation", "erosion_size", "BrainSegmentation_erosion_size", is_optional=True)
        self.export_parameter("BrainSegmentation", "visu", "BrainSegmentation_visu", is_optional=True)
        self.export_parameter("BrainSegmentation", "layer", "BrainSegmentation_layer", is_optional=True)
        self.export_parameter("BrainSegmentation", "first_slice", "BrainSegmentation_first_slice", is_optional=True)
        self.export_parameter("BrainSegmentation", "last_slice", "BrainSegmentation_last_slice", is_optional=True)
        self.export_parameter("Renorm", "template", "Renorm_template", is_optional=True)
        self.export_parameter("Renorm", "Normalization_init_translation_origin", "Renorm_Normalization_init_translation_origin", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_alignment", "Renorm_Normalization_NormalizeFSL_alignment", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_set_transformation_in_source_volume", "Renorm_Normalization_NormalizeFSL_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_cost_function", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_cost_function", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "Renorm_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_voxel_size", "Renorm_Normalization_NormalizeSPM_voxel_size", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_cutoff_option", "Renorm_Normalization_NormalizeSPM_cutoff_option", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_nbiteration", "Renorm_Normalization_NormalizeSPM_nbiteration", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeBaladin_set_transformation_in_source_volume", "Renorm_Normalization_NormalizeBaladin_set_transformation_in_source_volume", is_optional=True)
        self.export_parameter("Renorm", "Normalization_Normalization_AimsMIRegister_mni_to_acpc", "Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc", is_optional=True)
        self.export_parameter("Renorm", "Normalization_Normalization_AimsMIRegister_smoothing", "Renorm_Normalization_Normalization_AimsMIRegister_smoothing", is_optional=True)
        self.export_parameter("SplitBrain", "use_ridges", "SplitBrain_use_ridges", is_optional=True)
        self.export_parameter("SplitBrain", "use_template", "SplitBrain_use_template", is_optional=True)
        self.export_parameter("SplitBrain", "split_template", "SplitBrain_split_template", is_optional=True)
        self.export_parameter("SplitBrain", "mode", "SplitBrain_mode", is_optional=True)
        self.export_parameter("SplitBrain", "variant", "SplitBrain_variant", is_optional=True)
        self.export_parameter("SplitBrain", "bary_factor", "SplitBrain_bary_factor", is_optional=True)
        self.export_parameter("SplitBrain", "mult_factor", "SplitBrain_mult_factor", is_optional=True)
        self.export_parameter("SplitBrain", "initial_erosion", "SplitBrain_initial_erosion", is_optional=True)
        self.export_parameter("SplitBrain", "cc_min_size", "SplitBrain_cc_min_size", is_optional=True)
        self.export_parameter("HeadMesh", "keep_head_mask", "HeadMesh_keep_head_mask", is_optional=True)
        self.export_parameter("HeadMesh", "remove_mask", "HeadMesh_remove_mask", is_optional=True)
        self.export_parameter("HeadMesh", "first_slice", "HeadMesh_first_slice", is_optional=True)
        self.export_parameter("HeadMesh", "threshold", "HeadMesh_threshold", is_optional=True)
        self.export_parameter("HeadMesh", "closing", "HeadMesh_closing", is_optional=True)
        self.export_parameter("HeadMesh", "threshold_mode", "HeadMesh_threshold_mode", is_optional=True)
        self.export_parameter("SulcalMorphometry", "use_attribute", "SulcalMorphometry_use_attribute", is_optional=True)
        self.export_parameter("GreyWhiteClassification", "lesion_mask", "GreyWhiteClassification_lesion_mask", is_optional=True)
        self.export_parameter("GreyWhiteClassification", "lesion_mask_mode", "GreyWhiteClassification_lesion_mask_mode", is_optional=True)
        self.export_parameter("SulciRecognition", "recognition2000_model", "SulciRecognition_recognition2000_model", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_initial_transformation", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_SPAM_recognition09_global_recognition_labels_priors", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_model", "SulciRecognition_SPAM_recognition09_global_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_model", "SulciRecognition_SPAM_recognition09_local_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_SPAM_recognition09_local_recognition_local_referentials", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_SPAM_recognition09_local_recognition_direction_priors", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_SPAM_recognition09_local_recognition_angle_priors", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_SPAM_recognition09_local_recognition_translation_priors", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model", is_optional=True)
        self.export_parameter("SulciRecognition", "CNN_recognition19_model_file", "SulciRecognition_CNN_recognition19_model_file", is_optional=True)
        self.export_parameter("SulciRecognition", "CNN_recognition19_param_file", "SulciRecognition_CNN_recognition19_param_file", is_optional=True)
        self.export_parameter("SulciRecognition", "CNN_recognition19_cuda", "SulciRecognition_CNN_recognition19_cuda", is_optional=True)
        self.export_parameter("GreyWhiteClassification_1", "lesion_mask", "GreyWhiteClassification_1_lesion_mask", is_optional=True)
        self.export_parameter("GreyWhiteClassification_1", "lesion_mask_mode", "GreyWhiteClassification_1_lesion_mask_mode", is_optional=True)
        self.export_parameter("SulciRecognition_1", "recognition2000_model", "SulciRecognition_1_recognition2000_model", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_initial_transformation", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_model", "SulciRecognition_1_SPAM_recognition09_global_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_model", "SulciRecognition_1_SPAM_recognition09_local_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_model", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model", is_optional=True)
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_model_file", "SulciRecognition_1_CNN_recognition19_model_file", is_optional=True)
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_param_file", "SulciRecognition_1_CNN_recognition19_param_file", is_optional=True)
        self.export_parameter("SulciRecognition_1", "CNN_recognition19_cuda", "SulciRecognition_1_CNN_recognition19_cuda", is_optional=True)
        self.add_link("importation.output->PrepareSubject.T1mri")
        self.export_parameter("importation", "output", "imported_t1mri", is_optional=False)
        self.add_link("importation.referential->Renorm.TalairachFromNormalization_source_referential")
        self.add_link("importation.referential->PrepareSubject.TalairachFromNormalization_source_referential")
        self.export_parameter("importation", "referential", "t1mri_referential", is_optional=True)
        self.add_link("PrepareSubject.commissure_coordinates->Renorm.Normalization_commissures_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->select_renormalization_commissures.initial_switch_commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->BrainSegmentation.commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->BiasCorrection.commissure_coordinates")
        self.add_link("PrepareSubject.commissure_coordinates->TalairachTransformation.commissure_coordinates")
        self.add_link("PrepareSubject.reoriented_t1mri->Renorm.t1mri")
        self.add_link("PrepareSubject.reoriented_t1mri->BiasCorrection.t1mri")
        self.export_parameter("PrepareSubject", "reoriented_t1mri", is_optional=True)
        self.add_link("PrepareSubject.talairach_transformation->select_Talairach.Normalization_switch_Talairach_transform")
        self.export_parameter("PrepareSubject", "Normalization_normalized", "normalized_t1mri", weak_link=True, is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", "normalization_fsl_native_transformation_pass1", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeSPM_spm_transformation", "normalization_spm_native_transformation_pass1", is_optional=True)
        self.export_parameter("PrepareSubject", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", "normalization_baladin_native_transformation_pass1", is_optional=True)
        self.add_link("PrepareSubject.normalization_transformation->select_renormalization_transform.initial_switch_MNI_transform")
        self.add_link("BiasCorrection.t1mri_nobias->BrainSegmentation.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SulciSkeleton.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->HistoAnalysis.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->PialMesh.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteTopology_1.t1mri_nobias")
        self.export_parameter("BiasCorrection", "t1mri_nobias", is_optional=False)
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteClassification.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SplitBrain.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->SulciSkeleton_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteTopology.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->HeadMesh.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->PialMesh_1.t1mri_nobias")
        self.add_link("BiasCorrection.t1mri_nobias->GreyWhiteClassification_1.t1mri_nobias")
        self.export_parameter("BiasCorrection", "field", "BiasCorrection_field", is_optional=True)
        self.export_parameter("BiasCorrection", "hfiltered", "BiasCorrection_hfiltered", is_optional=True)
        self.add_link("BiasCorrection.hfiltered->HistoAnalysis.hfiltered")
        self.export_parameter("BiasCorrection", "white_ridges", "BiasCorrection_white_ridges", is_optional=True)
        self.add_link("BiasCorrection.white_ridges->HistoAnalysis.white_ridges")
        self.add_link("BiasCorrection.white_ridges->BrainSegmentation.white_ridges")
        self.add_link("BiasCorrection.white_ridges->SplitBrain.white_ridges")
        self.export_parameter("BiasCorrection", "variance", "BiasCorrection_variance", is_optional=True)
        self.add_link("BiasCorrection.variance->BrainSegmentation.variance")
        self.add_link("BiasCorrection.edges->GreyWhiteClassification_1.edges")
        self.export_parameter("BiasCorrection", "edges", "BiasCorrection_edges", is_optional=True)
        self.add_link("BiasCorrection.edges->BrainSegmentation.edges")
        self.add_link("BiasCorrection.edges->GreyWhiteClassification.edges")
        self.export_parameter("BiasCorrection", "meancurvature", "BiasCorrection_meancurvature", is_optional=True)
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteClassification_1.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->SplitBrain.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->BrainSegmentation.histo_analysis")
        self.export_parameter("HistoAnalysis", "histo_analysis", is_optional=False)
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteTopology_1.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteTopology.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->GreyWhiteClassification.histo_analysis")
        self.add_link("HistoAnalysis.histo_analysis->HeadMesh.histo_analysis")
        self.export_parameter("HistoAnalysis", "histo", "HistoAnalysis_histo", is_optional=True)
        self.add_link("BrainSegmentation.brain_mask->SplitBrain.brain_mask")
        self.export_parameter("BrainSegmentation", "brain_mask", "BrainSegmentation_brain_mask", is_optional=True)
        self.add_link("BrainSegmentation.brain_mask->Renorm.brain_mask")
        self.export_parameter("Renorm", "skull_stripped", "Renorm_skull_stripped", is_optional=True)
        self.add_link("Renorm.transformation->select_renormalization_transform.skull_stripped_switch_MNI_transform")
        self.add_link("Renorm.talairach_transformation->select_renormalization_transform.skull_stripped_switch_Talairach_transform")
        self.add_link("Renorm.commissure_coordinates->select_renormalization_commissures.skull_stripped_switch_commissure_coordinates")
        self.add_link("Renorm.Normalization_normalized->normalized_t1mri", weak_link=True)
        self.export_parameter("Renorm", "Normalization_NormalizeFSL_NormalizeFSL_transformation_matrix", "normalization_fsl_native_transformation", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeSPM_spm_transformation", "normalization_spm_native_transformation", is_optional=True)
        self.export_parameter("Renorm", "Normalization_NormalizeBaladin_NormalizeBaladin_transformation_matrix", "normalization_baladin_native_transformation", is_optional=True)
        self.add_link("SplitBrain.split_brain->GreyWhiteClassification.split_brain")
        self.add_link("SplitBrain.split_brain->CorticalFoldsGraph.split_brain")
        self.export_parameter("SplitBrain", "split_brain", is_optional=False)
        self.add_link("SplitBrain.split_brain->CorticalFoldsGraph_1.split_brain")
        self.add_link("SplitBrain.split_brain->GreyWhiteClassification_1.split_brain")
        self.add_link("SplitBrain.split_brain->TalairachTransformation.split_mask")
        self.add_link("TalairachTransformation.Talairach_transform->select_Talairach.StandardACPC_switch_Talairach_transform")
        self.export_parameter("HeadMesh", "head_mesh", "HeadMesh_head_mesh", is_optional=True)
        self.export_parameter("HeadMesh", "head_mask", "HeadMesh_head_mask", is_optional=True)
        self.export_parameter("SulcalMorphometry", "sulcal_morpho_measures", is_optional=False)
        self.export_parameter("GreyWhiteClassification", "grey_white", "GreyWhiteClassification_grey_white", is_optional=True)
        self.add_link("GreyWhiteClassification.grey_white->GreyWhiteTopology.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->PialMesh.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->SulciSkeleton.grey_white")
        self.add_link("GreyWhiteClassification.grey_white->CorticalFoldsGraph.grey_white")
        self.add_link("GreyWhiteTopology.hemi_cortex->SulciSkeleton.hemi_cortex")
        self.add_link("GreyWhiteTopology.hemi_cortex->GreyWhiteMesh.hemi_cortex")
        self.add_link("GreyWhiteTopology.hemi_cortex->PialMesh.hemi_cortex")
        self.export_parameter("GreyWhiteTopology", "hemi_cortex", "GreyWhiteTopology_hemi_cortex", is_optional=True)
        self.add_link("GreyWhiteTopology.hemi_cortex->CorticalFoldsGraph.hemi_cortex")
        self.export_parameter("GreyWhiteMesh", "white_mesh", "GreyWhiteMesh_white_mesh", is_optional=True)
        self.add_link("GreyWhiteMesh.white_mesh->CorticalFoldsGraph.white_mesh")
        self.add_link("SulciSkeleton.skeleton->SulciRecognition.CNN_recognition19_skeleton")
        self.add_link("SulciSkeleton.skeleton->PialMesh.skeleton")
        self.export_parameter("SulciSkeleton", "skeleton", "SulciSkeleton_skeleton", is_optional=True)
        self.add_link("SulciSkeleton.skeleton->CorticalFoldsGraph.skeleton")
        self.export_parameter("SulciSkeleton", "roots", "SulciSkeleton_roots", is_optional=True)
        self.add_link("SulciSkeleton.roots->SulciRecognition.CNN_recognition19_roots")
        self.add_link("SulciSkeleton.roots->CorticalFoldsGraph.roots")
        self.add_link("PialMesh.pial_mesh->CorticalFoldsGraph.pial_mesh")
        self.export_parameter("PialMesh", "pial_mesh", "PialMesh_pial_mesh", is_optional=True)
        self.export_parameter("CorticalFoldsGraph", "graph", "left_graph", is_optional=False)
        self.add_link("CorticalFoldsGraph.graph->SulciRecognition.data_graph")
        self.export_parameter("CorticalFoldsGraph", "sulci_voronoi", "CorticalFoldsGraph_sulci_voronoi", is_optional=True)
        self.export_parameter("CorticalFoldsGraph", "cortex_mid_interface", "CorticalFoldsGraph_cortex_mid_interface", is_optional=True)
        self.add_link("SulciRecognition.output_graph->SulcalMorphometry.left_sulci_graph")
        self.export_parameter("SulciRecognition", "output_graph", "left_labelled_graph", is_optional=False)
        self.export_parameter("SulciRecognition", "recognition2000_energy_plot_file", "SulciRecognition_recognition2000_energy_plot_file", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_global_recognition_posterior_probabilities", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_output_transformation", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_output_t1_to_global_transformation", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_local_recognition_posterior_probabilities", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_SPAM_recognition09_local_recognition_output_local_transformations", is_optional=True)
        self.export_parameter("SulciRecognition", "SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_markovian_recognition_posterior_probabilities", is_optional=True)
        self.add_link("GreyWhiteClassification_1.grey_white->GreyWhiteTopology_1.grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->SulciSkeleton_1.grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->CorticalFoldsGraph_1.grey_white")
        self.add_link("GreyWhiteClassification_1.grey_white->PialMesh_1.grey_white")
        self.export_parameter("GreyWhiteClassification_1", "grey_white", "GreyWhiteClassification_1_grey_white", is_optional=True)
        self.add_link("GreyWhiteTopology_1.hemi_cortex->GreyWhiteMesh_1.hemi_cortex")
        self.export_parameter("GreyWhiteTopology_1", "hemi_cortex", "GreyWhiteTopology_1_hemi_cortex", is_optional=True)
        self.add_link("GreyWhiteTopology_1.hemi_cortex->SulciSkeleton_1.hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->PialMesh_1.hemi_cortex")
        self.add_link("GreyWhiteTopology_1.hemi_cortex->CorticalFoldsGraph_1.hemi_cortex")
        self.export_parameter("GreyWhiteMesh_1", "white_mesh", "GreyWhiteMesh_1_white_mesh", is_optional=True)
        self.add_link("GreyWhiteMesh_1.white_mesh->CorticalFoldsGraph_1.white_mesh")
        self.export_parameter("SulciSkeleton_1", "skeleton", "SulciSkeleton_1_skeleton", is_optional=True)
        self.add_link("SulciSkeleton_1.skeleton->SulciRecognition_1.CNN_recognition19_skeleton")
        self.add_link("SulciSkeleton_1.skeleton->PialMesh_1.skeleton")
        self.add_link("SulciSkeleton_1.skeleton->CorticalFoldsGraph_1.skeleton")
        self.export_parameter("SulciSkeleton_1", "roots", "SulciSkeleton_1_roots", is_optional=True)
        self.add_link("SulciSkeleton_1.roots->CorticalFoldsGraph_1.roots")
        self.add_link("SulciSkeleton_1.roots->SulciRecognition_1.CNN_recognition19_roots")
        self.add_link("PialMesh_1.pial_mesh->CorticalFoldsGraph_1.pial_mesh")
        self.export_parameter("PialMesh_1", "pial_mesh", "PialMesh_1_pial_mesh", is_optional=True)
        self.add_link("CorticalFoldsGraph_1.graph->SulciRecognition_1.data_graph")
        self.export_parameter("CorticalFoldsGraph_1", "graph", "right_graph", is_optional=False)
        self.export_parameter("CorticalFoldsGraph_1", "sulci_voronoi", "CorticalFoldsGraph_1_sulci_voronoi", is_optional=True)
        self.export_parameter("CorticalFoldsGraph_1", "cortex_mid_interface", "CorticalFoldsGraph_1_cortex_mid_interface", is_optional=True)
        self.export_parameter("SulciRecognition_1", "output_graph", "right_labelled_graph", is_optional=False)
        self.add_link("SulciRecognition_1.output_graph->SulcalMorphometry.right_sulci_graph")
        self.export_parameter("SulciRecognition_1", "recognition2000_energy_plot_file", "SulciRecognition_1_recognition2000_energy_plot_file", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_global_recognition_posterior_probabilities", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_transformation", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_t1_to_global_transformation", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_local_recognition_posterior_probabilities", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_1_SPAM_recognition09_local_recognition_output_local_transformations", is_optional=True)
        self.export_parameter("SulciRecognition_1", "SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_posterior_probabilities", is_optional=True)
        self.add_link("select_Talairach.Talairach_transform->select_renormalization_transform.initial_switch_Talairach_transform")
        self.add_link("select_renormalization_commissures.commissure_coordinates->SplitBrain.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->GreyWhiteClassification.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->CorticalFoldsGraph.commissure_coordinates")
        self.export_parameter("select_renormalization_commissures", "commissure_coordinates", is_optional=False)
        self.add_link("select_renormalization_commissures.commissure_coordinates->CorticalFoldsGraph_1.commissure_coordinates")
        self.add_link("select_renormalization_commissures.commissure_coordinates->GreyWhiteClassification_1.commissure_coordinates")
        self.add_link("select_renormalization_transform.Talairach_transform->CorticalFoldsGraph_1.talairach_transform")
        self.export_parameter("select_renormalization_transform", "Talairach_transform", is_optional=False)
        self.add_link("select_renormalization_transform.Talairach_transform->CorticalFoldsGraph.talairach_transform")
        self.export_parameter("select_renormalization_transform", "MNI_transform", is_optional=False)

        # parameters order

        self.reorder_traits(("t1mri", "imported_t1mri", "select_Talairach", "Normalization_select_Normalization_pipeline", "commissure_coordinates", "anterior_commissure", "posterior_commissure", "interhemispheric_point", "left_hemisphere_point", "normalized_t1mri", "Talairach_transform", "t1mri_nobias", "histo_analysis", "BrainSegmentation_brain_mask", "split_brain", "HeadMesh_head_mesh", "GreyWhiteClassification_grey_white", "GreyWhiteClassification_1_grey_white", "GreyWhiteTopology_hemi_cortex", "GreyWhiteTopology_1_hemi_cortex", "GreyWhiteMesh_white_mesh", "GreyWhiteMesh_1_white_mesh", "SulciSkeleton_skeleton", "SulciSkeleton_1_skeleton", "PialMesh_pial_mesh", "PialMesh_1_pial_mesh", "left_graph", "right_graph", "left_labelled_graph", "right_labelled_graph", "sulcal_morpho_measures", "CorticalFoldsGraph_graph_version", "t1mri_referential", "allow_flip_initial_MRI", "PrepareSubject_TalairachFromNormalization_normalized_referential", "PrepareSubject_TalairachFromNormalization_acpc_referential", "PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized", "normalization_allow_retry_initialization", "perform_skull_stripped_renormalization", "MNI_transform", "fix_random_seed", "grey_white_topology_version", "pial_mesh_version", "sulci_skeleton_version", "compute_fold_meshes", "allow_multithreading", "CorticalFoldsGraph_write_cortex_mid_interface", "SPAM_recognition_labels_translation_map", "select_sulci_recognition", "sulci_recognition2000_forbid_unknown_label", "sulci_recognition2000_model_hint", "sulci_recognition2000_rate", "sulci_recognition2000_stop_rate", "sulci_recognition2000_niter_below_stop_prop", "sulci_recognition_spam_local_or_markovian", "sulci_recognition_spam_global_model_type", "rebuild_graph_attributes_after_split", "sulcal_morphometry_sulci_file", "reoriented_t1mri", "normalization_spm_native_transformation_pass1", "normalization_spm_native_transformation", "spm_normalization_version", "normalization_fsl_native_transformation_pass1", "normalization_fsl_native_transformation", "normalization_baladin_native_transformation_pass1", "normalization_baladin_native_transformation", "importation_output_database", "importation_attributes_merging", "importation_selected_attributes_from_header", "PrepareSubject_StandardACPC_Normalised", "PrepareSubject_StandardACPC_remove_older_MNI_normalization", "PrepareSubject_StandardACPC_older_MNI_normalization", "PrepareSubject_Normalization_commissures_coordinates", "PrepareSubject_Normalization_init_translation_origin", "PrepareSubject_Normalization_NormalizeFSL_template", "PrepareSubject_Normalization_NormalizeFSL_alignment", "PrepareSubject_Normalization_NormalizeFSL_set_transformation_in_source_volume", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_cost_function", "PrepareSubject_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "PrepareSubject_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "PrepareSubject_Normalization_NormalizeSPM_template", "PrepareSubject_Normalization_NormalizeSPM_voxel_size", "PrepareSubject_Normalization_NormalizeSPM_cutoff_option", "PrepareSubject_Normalization_NormalizeSPM_nbiteration", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "PrepareSubject_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "PrepareSubject_Normalization_NormalizeBaladin_template", "PrepareSubject_Normalization_NormalizeBaladin_set_transformation_in_source_volume", "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template", "PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc", "PrepareSubject_Normalization_Normalization_AimsMIRegister_smoothing", "BiasCorrection_sampling", "BiasCorrection_field_rigidity", "BiasCorrection_zdir_multiply_regul", "BiasCorrection_wridges_weight", "BiasCorrection_ngrid", "BiasCorrection_delete_last_n_slices", "BiasCorrection_mode", "BiasCorrection_write_field", "BiasCorrection_write_hfiltered", "BiasCorrection_write_wridges", "BiasCorrection_variance_fraction", "BiasCorrection_write_variance", "BiasCorrection_edge_mask", "BiasCorrection_write_edges", "BiasCorrection_write_meancurvature", "BiasCorrection_modality", "BiasCorrection_use_existing_ridges", "BiasCorrection_field", "BiasCorrection_hfiltered", "BiasCorrection_white_ridges", "BiasCorrection_variance", "BiasCorrection_edges", "BiasCorrection_meancurvature", "HistoAnalysis_use_hfiltered", "HistoAnalysis_use_wridges", "HistoAnalysis_undersampling", "HistoAnalysis_histo", "BrainSegmentation_lesion_mask", "BrainSegmentation_lesion_mask_mode", "BrainSegmentation_variant", "BrainSegmentation_erosion_size", "BrainSegmentation_visu", "BrainSegmentation_layer", "BrainSegmentation_first_slice", "BrainSegmentation_last_slice", "Renorm_template", "Renorm_skull_stripped", "Renorm_Normalization_init_translation_origin", "Renorm_Normalization_NormalizeFSL_alignment", "Renorm_Normalization_NormalizeFSL_set_transformation_in_source_volume", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_cost_function", "Renorm_Normalization_NormalizeFSL_NormalizeFSL_search_cost_function", "Renorm_Normalization_NormalizeFSL_ConvertFSLnormalizationToAIMS_standard_template", "Renorm_Normalization_NormalizeSPM_voxel_size", "Renorm_Normalization_NormalizeSPM_cutoff_option", "Renorm_Normalization_NormalizeSPM_nbiteration", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_target", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_normalized_volume", "Renorm_Normalization_NormalizeSPM_ConvertSPMnormalizationToAIMS_removeSource", "Renorm_Normalization_NormalizeBaladin_set_transformation_in_source_volume", "Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc", "Renorm_Normalization_Normalization_AimsMIRegister_smoothing", "SplitBrain_use_ridges", "SplitBrain_use_template", "SplitBrain_split_template", "SplitBrain_mode", "SplitBrain_variant", "SplitBrain_bary_factor", "SplitBrain_mult_factor", "SplitBrain_initial_erosion", "SplitBrain_cc_min_size", "HeadMesh_keep_head_mask", "HeadMesh_remove_mask", "HeadMesh_first_slice", "HeadMesh_threshold", "HeadMesh_closing", "HeadMesh_threshold_mode", "HeadMesh_head_mask", "SulcalMorphometry_use_attribute", "GreyWhiteClassification_lesion_mask", "GreyWhiteClassification_lesion_mask_mode", "SulciSkeleton_roots", "CorticalFoldsGraph_sulci_voronoi", "CorticalFoldsGraph_cortex_mid_interface", "SulciRecognition_recognition2000_model", "SulciRecognition_recognition2000_energy_plot_file", "SulciRecognition_SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_SPAM_recognition09_global_recognition_model", "SulciRecognition_SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_SPAM_recognition09_local_recognition_model", "SulciRecognition_SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_SPAM_recognition09_markovian_recognition_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_CNN_recognition19_model_file", "SulciRecognition_CNN_recognition19_param_file", "SulciRecognition_CNN_recognition19_cuda", "GreyWhiteClassification_1_lesion_mask", "GreyWhiteClassification_1_lesion_mask_mode", "SulciSkeleton_1_roots", "CorticalFoldsGraph_1_sulci_voronoi", "CorticalFoldsGraph_1_cortex_mid_interface", "SulciRecognition_1_recognition2000_model", "SulciRecognition_1_recognition2000_energy_plot_file", "SulciRecognition_1_SPAM_recognition09_global_recognition_initial_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors", "SulciRecognition_1_SPAM_recognition09_global_recognition_model", "SulciRecognition_1_SPAM_recognition09_global_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_transformation", "SulciRecognition_1_SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SulciRecognition_1_SPAM_recognition09_local_recognition_model", "SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials", "SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors", "SulciRecognition_1_SPAM_recognition09_local_recognition_posterior_probabilities", "SulciRecognition_1_SPAM_recognition09_local_recognition_output_local_transformations", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model", "SulciRecognition_1_SPAM_recognition09_markovian_recognition_posterior_probabilities", "SulciRecognition_1_CNN_recognition19_model_file", "SulciRecognition_1_CNN_recognition19_param_file", "SulciRecognition_1_CNN_recognition19_cuda"))

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
        self.Normalization_select_Normalization_pipeline = 'NormalizeSPM'
        self.CorticalFoldsGraph_graph_version = '3.1'
        self.PrepareSubject_TalairachFromNormalization_acpc_referential = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/registration/Talairach-AC_PC-Anatomist.referential'
        self.normalization_allow_retry_initialization = True
        self.perform_skull_stripped_renormalization = 'skull_stripped'
        self.grey_white_topology_version = '2'
        self.pial_mesh_version = '2'
        self.sulci_skeleton_version = '2'
        self.compute_fold_meshes = True
        self.allow_multithreading = True
        self.SPAM_recognition_labels_translation_map = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_model_2008.trl'
        self.select_sulci_recognition = 'CNN_recognition19'
        self.sulci_recognition2000_rate = 0.98
        self.sulci_recognition2000_stop_rate = 0.05
        self.sulci_recognition2000_niter_below_stop_prop = 1
        self.sulci_recognition_spam_global_model_type = 'Global registration'
        self.sulcal_morphometry_sulci_file = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_default_list.json'
        self.PrepareSubject_StandardACPC_remove_older_MNI_normalization = True
        self.PrepareSubject_Normalization_NormalizeFSL_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.PrepareSubject_Normalization_NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.PrepareSubject_Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.PrepareSubject_Normalization_NormalizeSPM_template = '/i2bm/local/spm8/templates/T1.nii'
        self.PrepareSubject_Normalization_NormalizeSPM_cutoff_option = 25
        self.PrepareSubject_Normalization_NormalizeSPM_nbiteration = 16
        self.PrepareSubject_Normalization_NormalizeBaladin_template = '/usr/share/fsl/data/standard/MNI152_T1_1mm.nii.gz'
        self.PrepareSubject_Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/transformation/talairach_TO_spm_template_novoxels.trm'
        self.PrepareSubject_Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.BiasCorrection_sampling = 16.0
        self.BiasCorrection_field_rigidity = 20.0
        self.BiasCorrection_zdir_multiply_regul = 0.5
        self.BiasCorrection_wridges_weight = 20.0
        self.BiasCorrection_ngrid = 2
        self.BiasCorrection_write_field = 'no'
        self.BiasCorrection_variance_fraction = 75
        self.BiasCorrection_write_meancurvature = 'no'
        self.HistoAnalysis_use_hfiltered = True
        self.HistoAnalysis_use_wridges = True
        self.HistoAnalysis_undersampling = 'iteration'
        self.BrainSegmentation_erosion_size = 1.8
        self.Renorm_template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.Renorm_Normalization_NormalizeFSL_alignment = 'Not Aligned but Same Orientation'
        self.Renorm_Normalization_NormalizeFSL_set_transformation_in_source_volume = True
        self.Renorm_Normalization_NormalizeSPM_cutoff_option = 25
        self.Renorm_Normalization_NormalizeSPM_nbiteration = 16
        self.Renorm_Normalization_NormalizeBaladin_set_transformation_in_source_volume = True
        self.Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/transformation/talairach_TO_spm_template_novoxels.trm'
        self.Renorm_Normalization_Normalization_AimsMIRegister_smoothing = 1.0
        self.SplitBrain_use_ridges = True
        self.SplitBrain_use_template = True
        self.SplitBrain_split_template = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/hemitemplate/closedvoronoi.ima'
        self.SplitBrain_variant = 'GW Barycentre'
        self.SplitBrain_bary_factor = 0.6
        self.SplitBrain_mult_factor = 2
        self.SplitBrain_initial_erosion = 2.0
        self.SplitBrain_cc_min_size = 500
        self.SulciRecognition_recognition2000_model = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/models/models_2008/discriminative_models/3.0/Rfolds_noroots/Rfolds_noroots.arg'
        self.SulciRecognition_1_recognition2000_model = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/models/models_2008/discriminative_models/3.0/Rfolds_noroots/Rfolds_noroots.arg'

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
