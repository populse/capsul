# -*- coding: utf-8 -*-

from capsul.api import Pipeline
from soma.controller import undefined


class SulciLabelling(Pipeline):

    def pipeline_definition(self):
        # nodes
        self.add_process("recognition2000", "capsul.pipeline.test.fake_morphologist.sulcilabellingann.SulciLabellingANN")
        self.add_process("SPAM_recognition09", "capsul.pipeline.test.fake_morphologist.sulcilabellingspam.SulciLabellingSPAM", make_optional=['global_recognition_model_type', 'global_recognition_model', 'local_recognition_model', 'local_recognition_local_referentials', 'local_recognition_direction_priors', 'local_recognition_angle_priors', 'local_recognition_translation_priors', 'markovian_recognition_model', 'markovian_recognition_segments_relations_model', 'global_recognition_posterior_probabilities', 'local_recognition_posterior_probabilities', 'markovian_recognition_posterior_probabilities'])
        self.nodes["SPAM_recognition09"].activated = False
        self.add_process("CNN_recognition19", "capsul.pipeline.test.fake_morphologist.sulcideeplabeling.SulciDeepLabeling", skip_invalid=True)
        self.add_switch("select_Sulci_Recognition", ['SPAM_recognition09', 'CNN_recognition19', 'recognition2000'], ['output_graph'], switch_value='recognition2000', opt_nodes=['recognition2000', 'SPAM_recognition09', 'CNN_recognition19'], export_switch=False)

        # links
        self.export_parameter("select_Sulci_Recognition", "switch", "select_Sulci_Recognition")
        self.export_parameter("CNN_recognition19", "graph", "data_graph")
        self.add_link("data_graph->SPAM_recognition09.data_graph")
        self.add_link("data_graph->recognition2000.data_graph")
        self.export_parameter("recognition2000", "fix_random_seed")
        self.add_link("fix_random_seed->CNN_recognition19.fix_random_seed")
        self.add_link("fix_random_seed->SPAM_recognition09.fix_random_seed")
        self.export_parameter("recognition2000", "model", "recognition2000_model")
        self.export_parameter("recognition2000", "model_hint", "recognition2000_model_hint")
        self.export_parameter("recognition2000", "rate", "recognition2000_rate")
        self.export_parameter("recognition2000", "stopRate", "recognition2000_stopRate")
        self.export_parameter("recognition2000", "niterBelowStopProp", "recognition2000_niterBelowStopProp")
        self.export_parameter("recognition2000", "forbid_unknown_label", "recognition2000_forbid_unknown_label")
        self.export_parameter("SPAM_recognition09", "local_or_markovian", "SPAM_recognition09_local_or_markovian")
        self.export_parameter("SPAM_recognition09", "global_recognition_labels_translation_map", "SPAM_recognition09_global_recognition_labels_translation_map")
        self.export_parameter("SPAM_recognition09", "global_recognition_labels_priors", "SPAM_recognition09_global_recognition_labels_priors")
        self.export_parameter("SPAM_recognition09", "global_recognition_initial_transformation", "SPAM_recognition09_global_recognition_initial_transformation")
        self.export_parameter("SPAM_recognition09", "global_recognition_model_type", "SPAM_recognition09_global_recognition_model_type")
        self.export_parameter("SPAM_recognition09", "global_recognition_model", "SPAM_recognition09_global_recognition_model")
        self.export_parameter("SPAM_recognition09", "local_recognition_model", "SPAM_recognition09_local_recognition_model")
        self.export_parameter("SPAM_recognition09", "local_recognition_local_referentials", "SPAM_recognition09_local_recognition_local_referentials")
        self.export_parameter("SPAM_recognition09", "local_recognition_direction_priors", "SPAM_recognition09_local_recognition_direction_priors")
        self.export_parameter("SPAM_recognition09", "local_recognition_angle_priors", "SPAM_recognition09_local_recognition_angle_priors")
        self.export_parameter("SPAM_recognition09", "local_recognition_translation_priors", "SPAM_recognition09_local_recognition_translation_priors")
        self.export_parameter("SPAM_recognition09", "markovian_recognition_model", "SPAM_recognition09_markovian_recognition_model")
        self.export_parameter("SPAM_recognition09", "markovian_recognition_segments_relations_model", "SPAM_recognition09_markovian_recognition_segments_relations_model")
        self.export_parameter("CNN_recognition19", "roots", "CNN_recognition19_roots")
        self.export_parameter("CNN_recognition19", "model_file", "CNN_recognition19_model_file")
        self.export_parameter("CNN_recognition19", "param_file", "CNN_recognition19_param_file")
        self.export_parameter("CNN_recognition19", "rebuild_attributes", "CNN_recognition19_rebuild_attributes")
        self.export_parameter("CNN_recognition19", "skeleton", "CNN_recognition19_skeleton")
        self.export_parameter("CNN_recognition19", "allow_multithreading", "CNN_recognition19_allow_multithreading")
        self.export_parameter("CNN_recognition19", "cuda", "CNN_recognition19_cuda")
        self.add_link("recognition2000.output_graph->select_Sulci_Recognition.recognition2000_switch_output_graph")
        self.export_parameter("recognition2000", "energy_plot_file", "recognition2000_energy_plot_file", weak_link=True)
        self.add_link("SPAM_recognition09.output_graph->select_Sulci_Recognition.SPAM_recognition09_switch_output_graph")
        self.export_parameter("SPAM_recognition09", "global_recognition_posterior_probabilities", "SPAM_recognition09_global_recognition_posterior_probabilities", weak_link=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_output_transformation", "SPAM_recognition09_global_recognition_output_transformation", weak_link=True)
        self.export_parameter("SPAM_recognition09", "global_recognition_output_t1_to_global_transformation", "SPAM_recognition09_global_recognition_output_t1_to_global_transformation", weak_link=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_posterior_probabilities", "SPAM_recognition09_local_recognition_posterior_probabilities", weak_link=True)
        self.export_parameter("SPAM_recognition09", "local_recognition_output_local_transformations", "SPAM_recognition09_local_recognition_output_local_transformations", weak_link=True)
        self.export_parameter("SPAM_recognition09", "markovian_recognition_posterior_probabilities", "SPAM_recognition09_markovian_recognition_posterior_probabilities", weak_link=True)
        self.add_link("CNN_recognition19.labeled_graph->select_Sulci_Recognition.CNN_recognition19_switch_output_graph")
        self.export_parameter("select_Sulci_Recognition", "output_graph")

        # default and initial values
        self.fix_random_seed = False
        self.recognition2000_model = '/casa/host/build/share/brainvisa-share-5.1/models/models_2008/discriminative_models/3.0/Lfolds_noroots/Lfolds_noroots.arg'
        self.recognition2000_model_hint = 0
        self.recognition2000_rate = 0.98
        self.recognition2000_stopRate = 0.05
        self.recognition2000_niterBelowStopProp = 1
        self.recognition2000_forbid_unknown_label = False
        self.SPAM_recognition09_global_recognition_labels_translation_map = '/casa/host/build/share/brainvisa-share-5.1/nomenclature/translation/sulci_model_2008.trl'
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
