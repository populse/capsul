# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class SPMNormalization(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("ConvertSPMnormalizationToAIMS", "capsul.pipeline.test.fake_morphologist.spmsn3dtoaims.SPMsn3dToAims")
        self.add_process("ReorientAnatomy", "capsul.pipeline.test.fake_morphologist.reorientanatomy.ReorientAnatomy")
        self.add_process("normalization_t1_spm12_reinit", "capsul.pipeline.test.fake_morphologist.normalization_t1_spm12_reinit.normalization_t1_spm12_reinit")
        self.add_process("normalization_t1_spm8_reinit", "capsul.pipeline.test.fake_morphologist.normalization_t1_spm8_reinit.normalization_t1_spm8_reinit")
        self.add_process("converter", "capsul.pipeline.test.fake_morphologist.aimsconverter.AimsConverter")
        self.add_switch("NormalizeSPM", ['normalization_t1_spm12_reinit', 'normalization_t1_spm8_reinit'], ['spm_transformation', 'normalized_t1mri'], export_switch=False)

        # links
        self.export_parameter("NormalizeSPM", "switch", "NormalizeSPM", is_optional=True)
        self.export_parameter("ReorientAnatomy", "t1mri", is_optional=False)
        self.add_link("t1mri->converter.read")
        self.add_link("t1mri->ConvertSPMnormalizationToAIMS.source_volume")
        self.export_parameter("normalization_t1_spm8_reinit", "anatomical_template", "template", is_optional=True)
        self.add_link("template->normalization_t1_spm12_reinit.anatomical_template")
        self.export_parameter("ReorientAnatomy", "allow_flip_initial_MRI", is_optional=False)
        self.export_parameter("normalization_t1_spm8_reinit", "allow_retry_initialization", is_optional=False)
        self.add_link("allow_retry_initialization->normalization_t1_spm12_reinit.allow_retry_initialization")
        self.export_parameter("normalization_t1_spm8_reinit", "init_translation_origin", is_optional=False)
        self.add_link("init_translation_origin->normalization_t1_spm12_reinit.init_translation_origin")
        self.export_parameter("normalization_t1_spm8_reinit", "voxel_size", is_optional=False)
        self.add_link("voxel_size->normalization_t1_spm12_reinit.voxel_size")
        self.export_parameter("normalization_t1_spm12_reinit", "cutoff_option", is_optional=False)
        self.add_link("cutoff_option->normalization_t1_spm8_reinit.cutoff_option")
        self.export_parameter("normalization_t1_spm12_reinit", "nbiteration", is_optional=False)
        self.add_link("nbiteration->normalization_t1_spm8_reinit.nbiteration")
        self.export_parameter("ConvertSPMnormalizationToAIMS", "target", "ConvertSPMnormalizationToAIMS_target", is_optional=True)
        self.export_parameter("ConvertSPMnormalizationToAIMS", "normalized_volume", "ConvertSPMnormalizationToAIMS_normalized_volume", is_optional=True)
        self.export_parameter("ConvertSPMnormalizationToAIMS", "removeSource", "ConvertSPMnormalizationToAIMS_removeSource", is_optional=True)
        self.export_parameter("ReorientAnatomy", "commissures_coordinates", "ReorientAnatomy_commissures_coordinates", is_optional=True)
        self.export_parameter("ReorientAnatomy", "output_transformation", "transformation", is_optional=False)
        self.add_link("ConvertSPMnormalizationToAIMS.write->transformation")
        self.add_link("ConvertSPMnormalizationToAIMS.write->ReorientAnatomy.transformation")
        self.export_parameter("ReorientAnatomy", "output_t1mri", "reoriented_t1mri", is_optional=False)
        self.add_link("ReorientAnatomy.output_transformation->transformation")
        self.export_parameter("ReorientAnatomy", "output_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates", is_optional=True)
        self.add_link("normalization_t1_spm12_reinit.transformations_informations->NormalizeSPM.normalization_t1_spm12_reinit_switch_spm_transformation")
        self.add_link("normalization_t1_spm12_reinit.normalized_anatomy_data->NormalizeSPM.normalization_t1_spm12_reinit_switch_normalized_t1mri")
        self.add_link("normalization_t1_spm8_reinit.transformations_informations->NormalizeSPM.normalization_t1_spm8_reinit_switch_spm_transformation")
        self.add_link("normalization_t1_spm8_reinit.normalized_anatomy_data->NormalizeSPM.normalization_t1_spm8_reinit_switch_normalized_t1mri")
        self.add_link("NormalizeSPM.spm_transformation->ConvertSPMnormalizationToAIMS.read")
        self.export_parameter("NormalizeSPM", "spm_transformation", is_optional=False)
        self.export_parameter("NormalizeSPM", "normalized_t1mri", is_optional=False)
        self.add_link("converter.write->normalization_t1_spm12_reinit.anatomy_data")
        self.add_link("converter.write->normalization_t1_spm8_reinit.anatomy_data")

        # parameters order

        self.reorder_fields(("NormalizeSPM", "t1mri", "transformation", "spm_transformation", "normalized_t1mri", "template", "allow_flip_initial_MRI", "allow_retry_initialization", "reoriented_t1mri", "init_translation_origin", "voxel_size", "cutoff_option", "nbiteration", "ConvertSPMnormalizationToAIMS_target", "ConvertSPMnormalizationToAIMS_normalized_volume", "ConvertSPMnormalizationToAIMS_removeSource", "ReorientAnatomy_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates"))

        # default and initial values
        self.template = '/host/usr/local/spm12-standalone/spm12_mcr/spm12/toolbox/OldNorm/T1.nii'
        self.allow_flip_initial_MRI = False
        self.allow_retry_initialization = True
        self.init_translation_origin = 0
        self.voxel_size = '[1 1 1]'
        self.cutoff_option = 25
        self.nbiteration = 16
        self.ConvertSPMnormalizationToAIMS_target = 'MNI template'
        self.ConvertSPMnormalizationToAIMS_removeSource = False

        # nodes positions
        self.node_position = {
            "ConvertSPMnormalizationToAIMS": (1179.07095, 117.05630000000008),
            "NormalizeSPM": (789.94195, 219.44370000000004),
            "ReorientAnatomy": (1441.4117, 20.306299999999965),
            "converter": (377.5439, 228.88740000000007),
            "inputs": (0.0, 0.0),
            "normalization_t1_spm12_reinit": (549.6002, 193.44370000000004),
            "normalization_t1_spm8_reinit": (549.6002, 475.3998),
            "outputs": (1703.7257, 179.375),
        }

        self.do_autoexport_nodes_parameters = False
