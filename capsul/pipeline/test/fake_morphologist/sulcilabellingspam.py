# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class SulciLabellingSPAM(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("global_recognition", "capsul.pipeline.test.fake_morphologist.sulcilabellingspamglobal.SulciLabellingSPAMGlobal")
        self.nodes["global_recognition"].set_plug_value("data_graph", traits.Undefined)
        self.nodes["global_recognition"].set_plug_value("model", traits.Undefined)
        self.nodes["global_recognition"].set_plug_value("labels_priors", traits.Undefined)
        self.nodes["global_recognition"].set_plug_value("initial_transformation", traits.Undefined)
        self.add_process("local_recognition", "capsul.pipeline.test.fake_morphologist.sulcilabellingspamlocal.SulciLabellingSPAMLocal")
        self.nodes["local_recognition"].set_plug_value("data_graph", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("model", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("labels_priors", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("local_referentials", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("direction_priors", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("angle_priors", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("translation_priors", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("initial_transformation", traits.Undefined)
        self.nodes["local_recognition"].set_plug_value("global_transformation", traits.Undefined)
        self.add_process("markovian_recognition", "capsul.pipeline.test.fake_morphologist.sulcilabellingspammarkov.SulciLabellingSPAMMarkov")
        self.nodes["markovian_recognition"].set_plug_value("data_graph", traits.Undefined)
        self.nodes["markovian_recognition"].set_plug_value("model", traits.Undefined)
        self.nodes["markovian_recognition"].set_plug_value("labels_priors", traits.Undefined)
        self.nodes["markovian_recognition"].set_plug_value("segments_relations_model", traits.Undefined)
        self.nodes["markovian_recognition"].set_plug_value("initial_transformation", traits.Undefined)
        self.nodes["markovian_recognition"].set_plug_value("global_transformation", traits.Undefined)
        self.add_switch("local_or_markovian", ['local_recognition', 'markovian_recognition'], ['output_graph'], output_types=[traits.File(output=True, optional=False)], export_switch=False)

        # links
        self.export_parameter("local_or_markovian", "switch", "local_or_markovian", is_optional=False)
        self.export_parameter("global_recognition", "data_graph", is_optional=False)
        self.export_parameter("markovian_recognition", "fix_random_seed", is_optional=False)
        self.export_parameter("markovian_recognition", "labels_translation_map", "global_recognition_labels_translation_map", is_optional=False)
        self.add_link("global_recognition_labels_translation_map->global_recognition.labels_translation_map")
        self.add_link("global_recognition_labels_translation_map->local_recognition.labels_translation_map")
        self.export_parameter("markovian_recognition", "initial_transformation", "global_recognition_initial_transformation", is_optional=True)
        self.add_link("global_recognition_initial_transformation->global_recognition.initial_transformation")
        self.add_link("global_recognition_initial_transformation->local_recognition.initial_transformation")
        self.export_parameter("local_recognition", "labels_priors", "global_recognition_labels_priors", is_optional=False)
        self.add_link("global_recognition_labels_priors->markovian_recognition.labels_priors")
        self.add_link("global_recognition_labels_priors->global_recognition.labels_priors")
        self.export_parameter("global_recognition", "model_type", "global_recognition_model_type", is_optional=True)
        self.export_parameter("global_recognition", "model", "global_recognition_model", is_optional=True)
        self.export_parameter("local_recognition", "model", "local_recognition_model", is_optional=True)
        self.export_parameter("local_recognition", "local_referentials", "local_recognition_local_referentials", is_optional=True)
        self.export_parameter("local_recognition", "direction_priors", "local_recognition_direction_priors", is_optional=True)
        self.export_parameter("local_recognition", "angle_priors", "local_recognition_angle_priors", is_optional=True)
        self.export_parameter("local_recognition", "translation_priors", "local_recognition_translation_priors", is_optional=True)
        self.export_parameter("markovian_recognition", "model", "markovian_recognition_model", is_optional=True)
        self.export_parameter("markovian_recognition", "segments_relations_model", "markovian_recognition_segments_relations_model", is_optional=True)
        self.add_link("global_recognition.output_graph->markovian_recognition.data_graph")
        self.export_parameter("global_recognition", "output_graph", is_optional=False)
        self.add_link("global_recognition.output_graph->local_recognition.data_graph")
        self.export_parameter("global_recognition", "posterior_probabilities", "global_recognition_posterior_probabilities", is_optional=True)
        self.add_link("global_recognition.output_transformation->local_recognition.global_transformation")
        self.add_link("global_recognition.output_transformation->markovian_recognition.global_transformation")
        self.export_parameter("global_recognition", "output_transformation", "global_recognition_output_transformation", is_optional=True)
        self.export_parameter("global_recognition", "output_t1_to_global_transformation", "global_recognition_output_t1_to_global_transformation", is_optional=True)
        self.add_link("local_recognition.output_graph->local_or_markovian.local_recognition_switch_output_graph")
        self.export_parameter("local_recognition", "posterior_probabilities", "local_recognition_posterior_probabilities", weak_link=True, is_optional=True)
        self.export_parameter("local_recognition", "output_local_transformations", "local_recognition_output_local_transformations", weak_link=True, is_optional=True)
        self.add_link("markovian_recognition.output_graph->local_or_markovian.markovian_recognition_switch_output_graph")
        self.export_parameter("markovian_recognition", "posterior_probabilities", "markovian_recognition_posterior_probabilities", weak_link=True, is_optional=True)
        self.add_link("local_or_markovian.output_graph->output_graph")

        # parameters order

        self.reorder_traits(("local_or_markovian", "data_graph", "output_graph", "fix_random_seed", "global_recognition_labels_translation_map", "global_recognition_initial_transformation", "global_recognition_labels_priors", "global_recognition_model_type", "global_recognition_model", "global_recognition_posterior_probabilities", "global_recognition_output_transformation", "global_recognition_output_t1_to_global_transformation", "local_recognition_model", "local_recognition_local_referentials", "local_recognition_direction_priors", "local_recognition_angle_priors", "local_recognition_translation_priors", "local_recognition_posterior_probabilities", "local_recognition_output_local_transformations", "markovian_recognition_model", "markovian_recognition_segments_relations_model", "markovian_recognition_posterior_probabilities"))

        # default and initial values
        self.global_recognition_labels_translation_map = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_model_2008.trl'
        self.global_recognition_model_type = 'Global registration'

        # nodes positions
        self.node_position = {
            "inputs": (-517.0, 255.0),
            "markovian_recognition": (238.0, 72.0),
            "outputs": (652.0, 510.0),
            "global_recognition": (-101.0, 60.0),
            "local_or_markovian": (456.0, 341.0),
            "local_recognition": (155.0, 404.0),
        }

        self.do_autoexport_nodes_parameters = False
