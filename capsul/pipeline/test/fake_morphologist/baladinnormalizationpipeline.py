# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class BaladinNormalizationPipeline(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("NormalizeBaladin", "capsul.pipeline.test.fake_morphologist.normalization_baladin.Normalization_Baladin")
        self.nodes["NormalizeBaladin"].set_plug_value("anatomy_data", traits.Undefined)
        self.add_process("ConvertBaladinNormalizationToAIMS", "capsul.pipeline.test.fake_morphologist.baladinnormalizationtoaims.BaladinNormalizationToAims")
        self.nodes["ConvertBaladinNormalizationToAIMS"].set_plug_value("read", traits.Undefined)
        self.nodes["ConvertBaladinNormalizationToAIMS"].set_plug_value("source_volume", traits.Undefined)
        self.add_process("ReorientAnatomy", "capsul.pipeline.test.fake_morphologist.reorientanatomy.ReorientAnatomy")
        self.nodes["ReorientAnatomy"].enabled = False
        self.nodes["ReorientAnatomy"].set_plug_value("t1mri", traits.Undefined)
        self.nodes["ReorientAnatomy"].set_plug_value("transformation", traits.Undefined)
        self.nodes["ReorientAnatomy"].set_plug_value("commissures_coordinates", traits.Undefined)

        # links
        self.export_parameter("ConvertBaladinNormalizationToAIMS", "source_volume", "t1mri", is_optional=False)
        self.add_link("t1mri->ReorientAnatomy.t1mri")
        self.add_link("t1mri->NormalizeBaladin.anatomy_data")
        self.export_parameter("NormalizeBaladin", "anatomical_template", "template", is_optional=False)
        self.add_link("template->ConvertBaladinNormalizationToAIMS.registered_volume")
        self.export_parameter("ConvertBaladinNormalizationToAIMS", "set_transformation_in_source_volume", is_optional=False)
        self.export_parameter("ReorientAnatomy", "allow_flip_initial_MRI", is_optional=False)
        self.export_parameter("ReorientAnatomy", "commissures_coordinates", "ReorientAnatomy_commissures_coordinates", is_optional=True)
        self.add_link("NormalizeBaladin.transformation_matrix->ConvertBaladinNormalizationToAIMS.read")
        self.export_parameter("NormalizeBaladin", "transformation_matrix", "NormalizeBaladin_transformation_matrix", is_optional=True)
        self.export_parameter("NormalizeBaladin", "normalized_anatomy_data", "NormalizeBaladin_normalized_anatomy_data", is_optional=True)
        self.add_link("ConvertBaladinNormalizationToAIMS.write->ReorientAnatomy.transformation")
        self.export_parameter("ConvertBaladinNormalizationToAIMS", "write", "ConvertBaladinNormalizationToAIMS_write", is_optional=True)
        self.export_parameter("ReorientAnatomy", "output_t1mri", "reoriented_t1mri", is_optional=False)
        self.export_parameter("ReorientAnatomy", "output_transformation", "transformation", is_optional=False)
        self.export_parameter("ReorientAnatomy", "output_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates", is_optional=True)

        # parameters order

        self.reorder_traits(("t1mri", "transformation", "template", "set_transformation_in_source_volume", "allow_flip_initial_MRI", "reoriented_t1mri", "NormalizeBaladin_transformation_matrix", "NormalizeBaladin_normalized_anatomy_data", "ConvertBaladinNormalizationToAIMS_write", "ReorientAnatomy_commissures_coordinates", "ReorientAnatomy_output_commissures_coordinates"))

        # default and initial values
        self.template = '/usr/share/fsl/data/standard/MNI152_T1_1mm.nii.gz'
        self.set_transformation_in_source_volume = True

        # nodes positions
        self.node_position = {
            "ConvertBaladinNormalizationToAIMS": (318.0, 104.0),
            "NormalizeBaladin": (108.0, 393.0),
            "ReorientAnatomy": (435.0, 299.0),
            "inputs": (-208.0, 127.0),
            "outputs": (699.0, 241.0),
        }

        self.do_autoexport_nodes_parameters = False
