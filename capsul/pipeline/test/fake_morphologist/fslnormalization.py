# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class FSLNormalization(Pipeline):
    def pipeline_definition(self):
        # nodes
        self.add_process(
            "NormalizeFSL",
            "capsul.pipeline.test.fake_morphologist.normalization_fsl_reinit.Normalization_FSL_reinit",
        )
        self.add_process(
            "ConvertFSLnormalizationToAIMS",
            "capsul.pipeline.test.fake_morphologist.fslnormalizationtoaims.FSLnormalizationToAims",
        )
        self.add_process(
            "ReorientAnatomy",
            "capsul.pipeline.test.fake_morphologist.reorientanatomy.ReorientAnatomy",
        )
        self.add_process(
            "converter",
            "capsul.pipeline.test.fake_morphologist.aimsconverter.AimsConverter",
        )

        # links
        self.export_parameter("converter", "read", "t1mri", is_optional=False)
        self.add_link("t1mri->ConvertFSLnormalizationToAIMS.source_volume")
        self.add_link("t1mri->ReorientAnatomy.t1mri")
        self.export_parameter(
            "NormalizeFSL", "anatomical_template", "template", is_optional=False
        )
        self.add_link("template->ConvertFSLnormalizationToAIMS.registered_volume")
        self.export_parameter(
            "NormalizeFSL", "Alignment", "alignment", is_optional=False
        )
        self.export_parameter(
            "ConvertFSLnormalizationToAIMS",
            "set_transformation_in_source_volume",
            is_optional=False,
        )
        self.export_parameter(
            "ReorientAnatomy", "allow_flip_initial_MRI", is_optional=False
        )
        self.export_parameter(
            "NormalizeFSL", "allow_retry_initialization", is_optional=False
        )
        self.export_parameter(
            "NormalizeFSL",
            "cost_function",
            "NormalizeFSL_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "search_cost_function",
            "NormalizeFSL_search_cost_function",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "init_translation_origin",
            "NormalizeFSL_init_translation_origin",
            is_optional=True,
        )
        self.export_parameter(
            "ConvertFSLnormalizationToAIMS",
            "standard_template",
            "ConvertFSLnormalizationToAIMS_standard_template",
            is_optional=True,
        )
        self.export_parameter(
            "ReorientAnatomy",
            "commissures_coordinates",
            "ReorientAnatomy_commissures_coordinates",
            is_optional=True,
        )
        self.add_link(
            "NormalizeFSL.transformation_matrix->ConvertFSLnormalizationToAIMS.read"
        )
        self.export_parameter(
            "NormalizeFSL",
            "transformation_matrix",
            "NormalizeFSL_transformation_matrix",
            is_optional=True,
        )
        self.export_parameter(
            "NormalizeFSL",
            "normalized_anatomy_data",
            "NormalizeFSL_normalized_anatomy_data",
            is_optional=True,
        )
        self.add_link(
            "ConvertFSLnormalizationToAIMS.write->ReorientAnatomy.transformation"
        )
        self.export_parameter(
            "ConvertFSLnormalizationToAIMS",
            "write",
            "ConvertFSLnormalizationToAIMS_write",
            is_optional=True,
        )
        self.export_parameter(
            "ReorientAnatomy", "output_t1mri", "reoriented_t1mri", is_optional=False
        )
        self.export_parameter(
            "ReorientAnatomy",
            "output_transformation",
            "transformation",
            is_optional=False,
        )
        self.export_parameter(
            "ReorientAnatomy",
            "output_commissures_coordinates",
            "ReorientAnatomy_output_commissures_coordinates",
            is_optional=True,
        )
        self.add_link("converter.write->NormalizeFSL.anatomy_data")

        # parameters order

        self.reorder_fields(
            (
                "t1mri",
                "transformation",
                "template",
                "alignment",
                "set_transformation_in_source_volume",
                "allow_flip_initial_MRI",
                "allow_retry_initialization",
                "reoriented_t1mri",
                "NormalizeFSL_transformation_matrix",
                "NormalizeFSL_normalized_anatomy_data",
                "NormalizeFSL_cost_function",
                "NormalizeFSL_search_cost_function",
                "NormalizeFSL_init_translation_origin",
                "ConvertFSLnormalizationToAIMS_write",
                "ConvertFSLnormalizationToAIMS_standard_template",
                "ReorientAnatomy_commissures_coordinates",
                "ReorientAnatomy_output_commissures_coordinates",
            )
        )

        # default and initial values
        self.alignment = "Not Aligned but Same Orientation"
        self.set_transformation_in_source_volume = True
        self.allow_flip_initial_MRI = False
        self.allow_retry_initialization = True
        self.NormalizeFSL_cost_function = "corratio"
        self.NormalizeFSL_search_cost_function = "corratio"
        self.NormalizeFSL_init_translation_origin = 0
        self.ConvertFSLnormalizationToAIMS_standard_template = 0

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
