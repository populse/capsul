# -*- coding: utf-8 -*-

from capsul.api import Pipeline
import traits.api as traits


class SulciLabelling(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("recognition2000", "capsul.pipeline.test.fake_morphologist.sulcilabellingann.SulciLabellingANN")
        self.nodes["recognition2000"].set_plug_value("data_graph", traits.Undefined)
        self.add_process("SPAM_recognition09", "capsul.pipeline.test.fake_morphologist.sulcilabellingspam.SulciLabellingSPAM")
        self.nodes["SPAM_recognition09"].process.nodes_activation = {'global_recognition': True, 'local_recognition': True, 'markovian_recognition': True}
        self.add_process("CNN_recognition19", "capsul.pipeline.test.fake_morphologist.sulcideeplabeling.SulciDeepLabeling", skip_invalid=True)
        self.nodes["CNN_recognition19"].set_plug_value("graph", traits.Undefined)
        self.nodes["CNN_recognition19"].set_plug_value("roots", traits.Undefined)
        self.nodes["CNN_recognition19"].set_plug_value("model_file", traits.Undefined)
        self.nodes["CNN_recognition19"].set_plug_value("param_file", traits.Undefined)
        self.nodes["CNN_recognition19"].set_plug_value("skeleton", traits.Undefined)
        self.add_switch("select_Sulci_Recognition", ['recognition2000', 'SPAM_recognition09', 'CNN_recognition19'], ['output_graph'], output_types=[traits.File(output=True, optional=False)], switch_value='CNN_recognition19', opt_nodes=True, export_switch=False)

        # links
        self.export_parameter("select_Sulci_Recognition", "switch", "select_Sulci_Recognition", is_optional=False)
        self.export_parameter("SPAM_recognition09", "data_graph", is_optional=False)
        self.add_link("data_graph->recognition2000.data_graph")
        self.add_link("data_graph->CNN_recognition19.graph")
        self.export_parameter("recognition2000", "fix_random_seed", is_optional=False)
        self.add_link("fix_random_seed->CNN_recognition19.fix_random_seed")
        self.add_link("fix_random_seed->SPAM_recognition09.fix_random_seed")
        self.export_parameter("recognition2000", "model", "recognition2000_model", is_optional=True)
        self.export_parameter("recognition2000", "model_hint", "recognition2000_model_hint", is_optional=True)
        self.export_parameter("recognition2000", "rate", "recognition2000_rate", is_optional=True)
        self.export_parameter("recognition2000", "stopRate", "recognition2000_stopRate", is_optional=True)
        self.export_parameter("recognition2000", "niterBelowStopProp", "recognition2000_niterBelowStopProp", is_optional=True)
        self.export_parameter("recognition2000", "forbid_unknown_label", "recognition2000_forbid_unknown_label", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_or_markovian", "SPAM_recognition09_local_or_markovian", is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_labels_translation_map", "SPAM_recognition09_global_recognition_labels_translation_map", is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_initial_transformation", "SPAM_recognition09_global_recognition_initial_transformation", is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_labels_priors", "SPAM_recognition09_global_recognition_labels_priors", is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_model_type", "SPAM_recognition09_global_recognition_model_type", is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_model", "SPAM_recognition09_global_recognition_model", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_model", "SPAM_recognition09_local_recognition_model", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_local_referentials", "SPAM_recognition09_local_recognition_local_referentials", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_direction_priors", "SPAM_recognition09_local_recognition_direction_priors", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_angle_priors", "SPAM_recognition09_local_recognition_angle_priors", is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_translation_priors", "SPAM_recognition09_local_recognition_translation_priors", is_optional=True)
        self.export_parameter("SPAM_recognition09", "markovian_recognition_model", "SPAM_recognition09_markovian_recognition_model", is_optional=True)
        self.export_parameter("SPAM_recognition09", "markovian_recognition_segments_relations_model", "SPAM_recognition09_markovian_recognition_segments_relations_model", is_optional=True)
        self.export_parameter("CNN_recognition19", "roots", "CNN_recognition19_roots", is_optional=True)
        self.export_parameter("CNN_recognition19", "model_file", "CNN_recognition19_model_file", is_optional=True)
        self.export_parameter("CNN_recognition19", "param_file", "CNN_recognition19_param_file", is_optional=True)
        self.export_parameter("CNN_recognition19", "rebuild_attributes", "CNN_recognition19_rebuild_attributes", is_optional=True)
        self.export_parameter("CNN_recognition19", "skeleton", "CNN_recognition19_skeleton", is_optional=True)
        self.export_parameter("CNN_recognition19", "allow_multithreading", "CNN_recognition19_allow_multithreading", is_optional=True)
        self.export_parameter("CNN_recognition19", "cuda", "CNN_recognition19_cuda", is_optional=True)
        self.add_link("recognition2000.output_graph->select_Sulci_Recognition.recognition2000_switch_output_graph")
        self.export_parameter("recognition2000", "energy_plot_file", "recognition2000_energy_plot_file", weak_link=True, is_optional=True)
        self.add_link("SPAM_recognition09.output_graph->select_Sulci_Recognition.SPAM_recognition09_switch_output_graph")
        self.export_parameter("SPAM_recognition09", "global_recognition_posterior_probabilities", "SPAM_recognition09_global_recognition_posterior_probabilities", weak_link=True, is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_output_transformation", "SPAM_recognition09_global_recognition_output_transformation", weak_link=True, is_optional=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_output_t1_to_global_transformation", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", weak_link=True, is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_posterior_probabilities", "SPAM_recognition09_local_recognition_posterior_probabilities", weak_link=True, is_optional=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_output_local_transformations", "SPAM_recognition09_local_recognition_output_local_transformations", weak_link=True, is_optional=True)
        self.export_parameter("SPAM_recognition09", "markovian_recognition_posterior_probabilities", "SPAM_recognition09_markovian_recognition_posterior_probabilities", weak_link=True, is_optional=True)
        self.add_link("CNN_recognition19.labeled_graph->select_Sulci_Recognition.CNN_recognition19_switch_output_graph")
        self.export_parameter("select_Sulci_Recognition", "output_graph", is_optional=False)

        # parameters order

        self.reorder_traits(("select_Sulci_Recognition", "data_graph", "output_graph", "fix_random_seed", "recognition2000_model", "recognition2000_model_hint", "recognition2000_rate", "recognition2000_stopRate", "recognition2000_niterBelowStopProp", "recognition2000_forbid_unknown_label", "recognition2000_energy_plot_file", "SPAM_recognition09_local_or_markovian", "SPAM_recognition09_global_recognition_labels_translation_map", "SPAM_recognition09_global_recognition_initial_transformation", "SPAM_recognition09_global_recognition_labels_priors", "SPAM_recognition09_global_recognition_model_type", "SPAM_recognition09_global_recognition_model", "SPAM_recognition09_global_recognition_posterior_probabilities", "SPAM_recognition09_global_recognition_output_transformation", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", "SPAM_recognition09_local_recognition_model", "SPAM_recognition09_local_recognition_local_referentials", "SPAM_recognition09_local_recognition_direction_priors", "SPAM_recognition09_local_recognition_angle_priors", "SPAM_recognition09_local_recognition_translation_priors", "SPAM_recognition09_local_recognition_posterior_probabilities", "SPAM_recognition09_local_recognition_output_local_transformations", "SPAM_recognition09_markovian_recognition_model", "SPAM_recognition09_markovian_recognition_segments_relations_model", "SPAM_recognition09_markovian_recognition_posterior_probabilities", "CNN_recognition19_roots", "CNN_recognition19_model_file", "CNN_recognition19_param_file", "CNN_recognition19_rebuild_attributes", "CNN_recognition19_skeleton", "CNN_recognition19_allow_multithreading", "CNN_recognition19_cuda"))

        # default and initial values
        self.select_Sulci_Recognition = 'CNN_recognition19'
        self.recognition2000_model = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/models/models_2008/discriminative_models/3.0/Rfolds_noroots/Rfolds_noroots.arg'
        self.recognition2000_rate = 0.98
        self.recognition2000_stopRate = 0.05
        self.recognition2000_niterBelowStopProp = 1
        self.SPAM_recognition09_global_recognition_labels_translation_map = '/volatile/riviere/brainvisa/build-stable-qt5/share/brainvisa-share-4.6/nomenclature/translation/sulci_model_2008.trl'
        self.SPAM_recognition09_global_recognition_model_type = 'Global registration'

        # nodes positions
        self.node_position = {
            "SPAM_recognition09": (95.0, 340.0),
            "outputs": (756.0, 429.0),
            "recognition2000": (182.0, -5.0),
            "inputs": (-508.0, 245.0),
            "select_Sulci_Recognition": (497.0, 197.0),
        }

        self.do_autoexport_nodes_parameters = False
