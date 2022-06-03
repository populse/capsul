# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class FSLNormalization(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("NormalizeFSL", "capsul.pipeline.test.fake_morphologist.normalization_fsl_reinit.Normalization_FSL_reinit")
        self.nodes["NormalizeFSL"].set_plug_value("anatomy_data", traits.Undefined)
        self.add_process("ConvertFSLnormalizationToAIMS", "capsul.pipeline.test.fake_morphologist.fslnormalizationtoaims.FSLnormalizationToAims")
        self.nodes["ConvertFSLnormalizationToAIMS"].set_plug_value("read", traits.Undefined)
        self.nodes["ConvertFSLnormalizationToAIMS"].set_plug_value("source_volume", traits.Undefined)
        self.add_process("ReorientAnatomy", "capsul.pipeline.test.fake_morphologist.reorientanatomy.ReorientAnatomy")
        self.nodes["ReorientAnatomy"].set_plug_value("t1mri", traits.Undefined)
        self.nodes["ReorientAnatomy"].set_plug_value("transformation", traits.Undefined)
        self.nodes["ReorientAnatomy"].set_plug_value("commissures_coordinates", traits.Undefined)
        self.add_process("converter", "capsul.pipeline.test.fake_morphologist.aimsconverter.AimsConverter")
        self.nodes["converter"].set_plug_value("read", traits.Undefined)
        self.nodes["converter"].set_plug_value("inputDynamicMin", traits.Undefined)
        self.nodes["converter"].set_plug_value("inputDynamicMax", traits.Undefined)
        self.nodes["converter"].set_plug_value("outputDynamicMin", traits.Undefined)
        self.nodes["converter"].set_plug_value("outputDynamicMax", traits.Undefined)
        self.nodes["converter"].process.inputDynamicMin = traits.Undefined
        self.nodes["converter"].process.inputDynamicMax = traits.Undefined
        self.nodes["converter"].process.outputDynamicMin = traits.Undefined
        self.nodes["converter"].process.outputDynamicMax = traits.Undefined

        # links
        self.export_parameter("ReorientAnatomy", "t1mri", is_optional=False)
        self.add_link("t1mri->converter.read")
        self.add_link("t1mri->ConvertFSLnormalizationToAIMS.source_volume")
        self.export_parameter("ConvertFSLnormalizationToAIMS", "registered_volume", "template", is_optional=False)
        self.add_link("template->NormalizeFSL.anatomical_template")
        self.export_parameter("NormalizeFSL", "Alignment", "alignment", is_optional=False)
        self.export_parameter("ConvertFSLnormalizationToAIMS", "set_transformation_in_source_volume", is_optional=False)
        self.export_parameter("ReorientAnatomy", "allow_flip_initial_MRI", is_optional=False)
        self.export_parameter("NormalizeFSL", "allow_retry_initialization", is_optional=False)
        self.export_parameter("NormalizeFSL", "cost_function", "NormalizeFSL_cost_function", is_optional=True)
        self.export_parameter("NormalizeFSL", "search_cost_function", "NormalizeFSL_search_cost_function", is_optional=True)
        self.export_parameter("NormalizeFSL", "init_translation_origin", "NormalizeFSL_init_translation_origin", is_optional=True)
        self.export_parameter("ConvertFSLnormalizationToAIMS", "standard_template", "ConvertFSLnormalizationToAIMS_standard_template", is_optional=True)
        self.export_parameter("ReorientAnatomy", "commissures_coordinates", "ReorientAnatomy_commissures_coordinates", is_optional=True)
        self.add_link("NormalizeFSL.transformation_matrix->ConvertFSLnormalizationToAIMS.read")
        self.export_parameter("NormalizeFSL", "transformation_matrix", "NormalizeFSL_transformation_matrix", is_optional=True)
        self.export_parameter("NormalizeFSL", "normalized_anatomy_data", "NormalizeFSL_normalized_anatomy_data", is_optional=True)
        self.add_link("ConvertFSLnormalizationToAIMS.write->ReorientAnatomy.transformation")
        self.export_parameter("ConvertFSLnormalizationToAIMS", "write", "ConvertFSLnormalizationToAIMS_write", is_optional=True)
        self.export_parameter("ReorientAnatomy", "output_t1mri", "reoriented_t1mri", is_optional=False)
        self.export_parameter("ReorientAnatomy", "output_transformation", "transformation", is_optional=False)
        self.export_parameter("ReorientAnatomy", "output_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates", is_optional=True)
        self.add_link("converter.write->NormalizeFSL.anatomy_data")

        # parameters order

        self.reorder_traits(("t1mri", "transformation", "template", "alignment", "set_transformation_in_source_volume", "allow_flip_initial_MRI", "allow_retry_initialization", "reoriented_t1mri", "NormalizeFSL_cost_function", "NormalizeFSL_search_cost_function", "NormalizeFSL_init_translation_origin", "NormalizeFSL_transformation_matrix", "NormalizeFSL_normalized_anatomy_data", "ConvertFSLnormalizationToAIMS_standard_template", "ConvertFSLnormalizationToAIMS_write", "ReorientAnatomy_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates"))

        # default and initial values
        self.template = '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'
        self.alignment = 'Not Aligned but Same Orientation'
        self.set_transformation_in_source_volume = True
        self.allow_retry_initialization = True

        # nodes positions
        self.node_position = {
            "ConvertFSLnormalizationToAIMS": (781.0, 193.0),
            "NormalizeFSL": (560.0, 36.0),
            "ReorientAnatomy": (1063.0, 264.0),
            "converter": (387.5, 0.0),
            "inputs": (0.0, 112.0),
            "outputs": (1326.0, 144.0),
        }

        self.do_autoexport_nodes_parameters = False
