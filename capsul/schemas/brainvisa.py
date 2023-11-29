from capsul.dataset import MetadataSchema, SchemaMapping, process_schema
from soma.controller import undefined
import importlib
import copy


class BrainVISASharedSchema(MetadataSchema):
    """Metadata schema for BrainVISA shared dataset"""

    schema_name = "brainvisa_shared"
    data_id: str = ""
    side: str = None
    graph_version: str = None
    model_version: str = None

    def _path_list(self, unused_meta=None):
        """
        The path has the following pattern:
        <something>
        """

        full_side = {"L": "left", "R": "right"}
        path_list = []
        filename = ""
        if self.data_id == "normalization_template":
            path_list = ["anatomical_templates"]
            filename = "MNI152_T1_2mm.nii.gz"
        elif self.data_id == "normalization_template_brain":
            path_list = ["anatomical_templates"]
            filename = "MNI152_T1_2mm_brain.nii"
        elif self.data_id == "trans_mni_to_acpc":
            path_list = ["transformation"]
            filename = "spm_template_novoxels_TO_talairach.trm"
        elif self.data_id == "acpc_ref":
            path_list = ["registration"]
            filename = "Talairach-AC_PC-Anatomist.referential"
        elif self.data_id == "trans_acpc_to_mni":
            path_list = ["transformation"]
            filename = "talairach_TO_spm_template_novoxels.trm"
        elif self.data_id == "icbm152_ref":
            path_list = ["registration"]
            filename = "Talairach-MNI_template-SPM.referential"
        elif self.data_id == "hemi_split_template":
            path_list = ["hemitemplate"]
            filename = "closedvoronoi.ima"
        elif self.data_id == "sulcal_morphometry_sulci_file":
            path_list = ["nomenclature", "translation"]
            filename = "sulci_default_list.json"
        elif self.data_id == "sulci_spam_recognition_labels_trans":
            path_list = ["nomenclature", "translation"]
            filename = f"sulci_model_20{self.model_version}.trl"
        elif self.data_id == "sulci_ann_recognition_model":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "discriminative_models",
                self.graph_version,
                f"{self.side}folds_noroots",
            ]
            filename = f"{self.side}folds_noroots.arg"
        elif self.data_id == "sulci_spam_recognition_global_model":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"global_registered_spam_{full_side[self.side]}",
            ]
            filename = "spam_distribs.dat"
        elif self.data_id == "sulci_spam_recognition_local_model":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"locally_from_global_registred_spam_{full_side[self.side]}",
            ]
            filename = "spam_distribs.dat"
        elif self.data_id == "sulci_spam_recognition_global_labels_priors":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "labels_priors",
                f"frequency_segments_priors_{full_side[self.side]}",
            ]
            filename = "frequency_segments_priors.dat"
        elif self.data_id == "sulci_spam_recognition_local_refs":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"locally_from_global_registred_spam_{full_side[self.side]}",
            ]
            filename = "local_referentials.dat"
        elif self.data_id == "sulci_spam_recognition_local_dir_priors":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"locally_from_global_registred_spam_{full_side[self.side]}",
            ]
            filename = "bingham_direction_trm_priors.dat"
        elif self.data_id == "sulci_spam_recognition_local_angle_priors":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"locally_from_global_registred_spam_{full_side[self.side]}",
            ]
            filename = "vonmises_angle_trm_priors.dat"
        elif self.data_id == "sulci_spam_recognition_local_trans_priors":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments",
                f"locally_from_global_registred_spam_{full_side[self.side]}",
            ]
            filename = "gaussian_translation_trm_priors.dat"
        elif self.data_id == "sulci_spam_recognition_markov_rels":
            path_list = [
                "models",
                f"models_20{self.model_version}",
                "descriptive_models",
                "segments_relations",
                f"mindist_relations_{full_side[self.side]}",
            ]
            filename = "gamma_exponential_mixture_distribs.dat"
        elif self.data_id == "sulci_cnn_recognition_model":
            path_list = ["models", f"models_20{self.model_version}", "cnn_models"]
            filename = f"sulci_unet_model_{full_side[self.side]}.mdsm"
        elif self.data_id == "sulci_cnn_recognition_param":
            path_list = ["models", f"models_20{self.model_version}", "cnn_models"]
            filename = f"sulci_unet_model_params_{full_side[self.side]}.json"
        else:
            filename = self.data_id

        path_list.append(filename)
        return path_list


class BrainVISAToShared(SchemaMapping):
    source_schema = "brainvisa"
    dest_schema = "brainvisa_shared"

    @staticmethod
    def map_schemas(source, dest):
        dest.side = source.side
        dest.graph_version = source.sulci_graph_version


class MorphoBIDSToShared(SchemaMapping):
    source_schema = "morphologist_bids"
    dest_schema = "brainvisa_shared"

    @staticmethod
    def map_schemas(source, dest):
        BrainVISAToShared.map_schemas(source, dest)


def declare_morpho_schemas(morpho_module):
    """Declares Morphologist and sub-processes completion schemas for
    BIDS, BrainVisa and shared organizations.

    It may apply to the "real" Morphologist pipeline (morphologist.capsul
    parent module), or to the "fake" morphologist test replica
    (capsul.pipeline.test.fake_morphologist parent module)
    """

    axon_module = morpho_module
    cnn_module = f"{morpho_module}.sulcideeplabeling"
    if morpho_module.startswith("morphologist."):
        axon_module = f"{morpho_module}.axon"
        cnn_module = "deepsulci.sulci_labeling.capsul.labeling"

    morphologist = importlib.import_module(f"{morpho_module}.morphologist")
    normalization_t1_spm12_reinit = importlib.import_module(
        f"{axon_module}.normalization_t1_spm12_reinit"
    )
    normalization_t1_spm8_reinit = importlib.import_module(
        f"{axon_module}.normalization_t1_spm8_reinit"
    )
    normalization_aimsmiregister = importlib.import_module(
        f"{axon_module}.normalization_aimsmiregister"
    )
    normalization_fsl_reinit = importlib.import_module(
        f"{axon_module}.normalization_fsl_reinit"
    )
    t1biascorrection = importlib.import_module(f"{axon_module}.t1biascorrection")
    histoanalysis = importlib.import_module(f"{axon_module}.histoanalysis")
    brainsegmentation = importlib.import_module(f"{axon_module}.brainsegmentation")
    skullstripping = importlib.import_module(f"{axon_module}.skullstripping")
    scalpmesh = importlib.import_module(f"{axon_module}.scalpmesh")
    splitbrain = importlib.import_module(f"{axon_module}.splitbrain")
    greywhiteclassificationhemi = importlib.import_module(
        f"{axon_module}.greywhiteclassificationhemi"
    )
    greywhitetopology = importlib.import_module(f"{axon_module}.greywhitetopology")
    greywhitemesh = importlib.import_module(f"{axon_module}.greywhitemesh")
    pialmesh = importlib.import_module(f"{axon_module}.pialmesh")
    sulciskeleton = importlib.import_module(f"{axon_module}.sulciskeleton")
    sulcigraph = importlib.import_module(f"{axon_module}.sulcigraph")
    sulcilabellingann = importlib.import_module(f"{axon_module}.sulcilabellingann")
    sulcilabellingspamglobal = importlib.import_module(
        f"{axon_module}.sulcilabellingspamglobal"
    )
    sulcilabellingspamlocal = importlib.import_module(
        f"{axon_module}.sulcilabellingspamlocal"
    )
    sulcilabellingspammarkov = importlib.import_module(
        f"{axon_module}.sulcilabellingspammarkov"
    )
    try:
        sulcideeplabeling = importlib.import_module(cnn_module)
    except Exception:
        if cnn_module.startswith("deepsulci"):
            # fallback to fake
            cnn_module = "capsul.pipeline.test.fake_morphologist.sulcideeplabeling"
            sulcideeplabeling = importlib.import_module(cnn_module)
        else:
            raise
    brainvolumes = importlib.import_module(f"{axon_module}.brainvolumes")
    morpho_report = importlib.import_module(f"{axon_module}.morpho_report")
    sulcigraphmorphometrybysubject = importlib.import_module(
        f"{axon_module}.sulcigraphmorphometrybysubject"
    )

    # patch processes to setup their requirements and schemas

    Morphologist = morphologist.Morphologist
    normalization_t1_spm12_reinit = (
        normalization_t1_spm12_reinit.normalization_t1_spm12_reinit
    )
    normalization_t1_spm8_reinit = (
        normalization_t1_spm8_reinit.normalization_t1_spm8_reinit
    )
    normalization_aimsmiregister = (
        normalization_aimsmiregister.normalization_aimsmiregister
    )
    Normalization_FSL_reinit = normalization_fsl_reinit.Normalization_FSL_reinit
    T1BiasCorrection = t1biascorrection.T1BiasCorrection
    HistoAnalysis = histoanalysis.HistoAnalysis
    BrainSegmentation = brainsegmentation.BrainSegmentation
    skullstripping = skullstripping.skullstripping
    ScalpMesh = scalpmesh.ScalpMesh
    SplitBrain = splitbrain.SplitBrain
    GreyWhiteClassificationHemi = (
        greywhiteclassificationhemi.GreyWhiteClassificationHemi
    )
    GreyWhiteTopology = greywhitetopology.GreyWhiteTopology
    GreyWhiteMesh = greywhitemesh.GreyWhiteMesh
    PialMesh = pialmesh.PialMesh
    SulciSkeleton = sulciskeleton.SulciSkeleton
    SulciGraph = sulcigraph.SulciGraph
    SulciLabellingANN = sulcilabellingann.SulciLabellingANN
    SulciLabellingSPAMGlobal = sulcilabellingspamglobal.SulciLabellingSPAMGlobal
    SulciLabellingSPAMLocal = sulcilabellingspamlocal.SulciLabellingSPAMLocal
    SulciLabellingSPAMMarkov = sulcilabellingspammarkov.SulciLabellingSPAMMarkov
    SulciDeepLabeling = sulcideeplabeling.SulciDeepLabeling
    morpho_report = morpho_report.morpho_report
    brainvolumes = brainvolumes.brainvolumes
    sulcigraphmorphometrybysubject = (
        sulcigraphmorphometrybysubject.sulcigraphmorphometrybysubject
    )

    bv_acq_unused = [
        "subject_only",
        "analysis",
        "seg_directory",
        "side",
        "sidebis",
        "sulci_graph_version",
        "sulci_recognition_session",
    ]
    bv_t1_unused = bv_acq_unused + ["suffix"]
    bv_ref_unused = list(bv_acq_unused)
    bv_ref_unused.remove("seg_directory")

    def updated(d, *args):
        res = copy.deepcopy(d)
        for d2 in args:
            res.update(d2)
        return res

    @process_schema("brainvisa", Morphologist)
    def brainvisa_Morphologist(metadata):
        metadata["*"].process = None
        metadata["*"].modality = "t1mri"
        metadata["*_pass1"].suffix.append("pass1")
        metadata["*_labelled_graph"].suffix.append(
            metadata["left_labelled_graph"].sulci_recognition_session
        )
        metadata["*_labelled_graph"].suffix.append(
            metadata["left_labelled_graph"].sulci_recognition_type
        )
        metadata["left_*"].side = "L"
        metadata["right_*"].side = "R"
        #     _nodes = {
        #         "GreyWhiteClassification": {"*": {"side": "L"}},
        #         "GreyWhiteTopology": {"*": {"side": "L"}},
        #         "GreyWhiteMesh": {"*": {"sidebis": "L"}},
        #         "PialMesh": {"*": {"sidebis": "L"}},
        #         "SulciSkeleton": {"*": {"side": "L"}},
        #         "CorticalFoldsGraph": {"*": {"side": "L"}},
        #         "SulciRecognition": {"*": {"side": "L"}},
        #         "*_1": {"*": {"side": "R"}},
        #         "GreyWhiteMesh_1": {"*": {"sidebis": "R", "side": None}},
        #         "PialMesh_1": {"*": {"sidebis": "R", "side": None}},
        #         "SulciRecognition*": {
        #             "*": {
        #                 "sulci_graph_version": lambda **kwargs: f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
        #                 "prefix": None,
        #                 "sidebis": None,
        #             }
        #         },
        #         "*.ReorientAnatomy": {
        #             "_meta_links": {
        #                 "transformation": {
        #                     "*": [],
        #                 },
        #             },
        #         },
        #         "*.Convert*normalizationToAIMS": {
        #             "_meta_links": {
        #                 "*": {
        #                     "*": [],
        #                 },
        #             },
        #         },
        #     }

        # metadata["*"][
        #     "subject_only", "sulci_graph_version", "sulci_recognition_session"
        # ].unused()
        metadata["*_graph"]["sulci_graph_version"].used()
        metadata["*_graph"]["sulci_graph_version", "sulci_recognition_session"].used()

        metadata[
            "t1mri", "imported_t1mri", "reoriented_t1mri", "commissure_coordinates"
        ][bv_t1_unused].unused()
        metadata[
            "normalized_t1mri",
            "normalization_spm_native_transformation",
        ][bv_acq_unused].unused()
        metadata[
            "t1mri_referential",
            "Talairach_transform",
            "MNI_transform",
        ][bv_ref_unused].unused()
        metadata["subject"]["subject_only", "subject"].used()
        metadata["sulcal_morpho_measures"]["subject_only"].unused()

        metadata.normalization_spm_native_transformation.prefix = None
        metadata.commissure_coordinates.extension = "APC"

        metadata.t1mri_referential.seg_directory = "registration"
        metadata.t1mri_referential.short_prefix = "RawT1-"
        metadata.t1mri_referential.suffix = (
            metadata.t1mri_referential.acquisition.value()
        )
        metadata.t1mri_referential.extension = "referential"

        metadata.Talairach_transform.seg_directory = "registration"
        metadata.Talairach_transform.prefix = ""
        metadata.Talairach_transform.short_prefix = "RawT1-"
        metadata.Talairach_transform.suffix = (
            f"{metadata.Talairach_transform.acquisition.value()}_TO_Talairach-ACPC"
        )
        metadata.Talairach_transform.extension = "trm"

        metadata.MNI_transform.seg_directory = "registration"
        metadata.MNI_transform.prefix = ""
        metadata.MNI_transform.short_prefix = "RawT1-"
        metadata.MNI_transform.suffix = (
            f"{metadata.MNI_transform.acquisition.value()}_TO_Talairach-MNI"
        )
        metadata.MNI_transform.extension = "trm"

        metadata["left_graph", "right_graph"].prefix = None
        metadata["left_graph", "right_graph"].suffix = None

        metadata.subject.subject_only = True
        metadata.sulcal_morpho_measures.subject_only = False

    @process_schema("bids", Morphologist)
    def bids_Morphologist(metadata):
        metadata["*"].process = None
        metadata["*"].modality = "t1mri"
        metadata["*"].folder = "derivative"
        metadata["*_pass1"].suffix.append("pass1")
        metadata["*_labelled_graph"].suffix.append(
            metadata["left_labelled_graph"].sulci_recognition_session
        )
        metadata["*_labelled_graph"].suffix.append(
            metadata["left_labelled_graph"].sulci_recognition_type
        )
        metadata["left_*"].side = "L"
        metadata["right_*"].side = "R"
        metadata.t1mri.folder = "rawdata"

    @process_schema("brainvisa", normalization_t1_spm12_reinit)
    def brainvisa_normalization_t1_spm12_reinit(metadata):
        metadata.transformations_informations.analysis = undefined
        metadata.transformations_informations.suffix = "sn"
        metadata.transformations_informations.extension = "mat"

        metadata.normalized_anatomy_data.analysis = undefined
        metadata.normalized_anatomy_data.prefix = "normalized_SPM"
        metadata.normalized_anatomy_data.extension = "nii"

    @process_schema("morphologist_bids", normalization_t1_spm12_reinit)
    def morphologist_bids_normalization_t1_spm12_reinit(metadata):
        brainvisa_normalization_t1_spm12_reinit(metadata)

    @process_schema("brainvisa_shared", normalization_t1_spm12_reinit)
    def brainvisa_shared_normalization_t1_spm12_reinit(metadata):
        metadata.anatomical_template.data_id = "normalization_template"

    @process_schema("brainvisa", normalization_t1_spm8_reinit)
    def brainvisa_normalization_t1_spm8_reinit(metadata):
        metadata.transformations_informations.analysis = undefined
        metadata.transformations_informations.suffix = "sn"
        metadata.transformations_informations.extension = "mat"
        metadata.normalized_anatomy_data.analysis = undefined
        metadata.normalized_anatomy_data.prefix = "normalized_SPM"
        metadata.normalized_anatomy_data.extension = "nii"

    @process_schema("morphologist_bids", normalization_t1_spm8_reinit)
    def morphologist_bids_normalization_t1_spm8_reinit(metadata):
        brainvisa_normalization_t1_spm8_reinit(metadata)

    @process_schema("brainvisa_shared", normalization_t1_spm8_reinit)
    def brainvisa_shared_normalization_t1_spm8_reinit(metadata):
        metadata.anatomical_template.data_id = "normalization_template"

    @process_schema("brainvisa", normalization_aimsmiregister)
    def brainvisa_normalization_aimsmiregister(metadata):
        metadata.transformation_to_ACPC.prefix = "normalized_aims"
        metadata.transformation_to_ACPC.extension = "trm"

    @process_schema("morphologist_bids", normalization_aimsmiregister)
    def morphologist_bids_normalization_aimsmiregister(metadata):
        brainvisa_normalization_aimsmiregister(metadata)

    @process_schema("brainvisa_shared", normalization_aimsmiregister)
    def brainvisa_shared_normalization_aimsmiregister(metadata):
        metadata.anatomical_template.data_id = "normalization_template"

    @process_schema("brainvisa", Normalization_FSL_reinit)
    def brainvisa_Normalization_FSL_reinit(metadata):
        metadata.transformation_matrix.seg_directory = "registration"
        metadata.transformation_matrix.analysis = undefined
        metadata.transformation_matrix.suffix = "fsl"
        metadata.transformation_matrix.extension = "mat"

        metadata.normalized_anatomy_data.seg_directory = None
        metadata.normalized_anatomy_data.analysis = undefined
        metadata.normalized_anatomy_data.prefix = "normalized_FSL"
        metadata.normalized_anatomy_data.suffix = None

    @process_schema("morphologist_bids", Normalization_FSL_reinit)
    def morphologist_bids_Normalization_FSL_reinit(metadata):
        brainvisa_Normalization_FSL_reinit(metadata)

    @process_schema("brainvisa", T1BiasCorrection)
    def brainvisa_T1BiasCorrection(metadata):
        metadata["*"].seg_directory = None
        # TODO: check the conversion of the following code
        #     _ = {
        #         "*": {
        #             "analysis": lambda **kwargs: f'{kwargs["initial_meta"].analysis}',
        #         }
        #     }
        metadata["*"].analysis = metadata.initial_meta.analysis
        metadata.transformation_matrix.seg_directory = "registration"
        metadata.t1mri_nobias.prefix = "nobias"
        metadata.b_field.prefix = "biasfield"
        metadata.hfiltered.prefix = "hfiltered"
        metadata.white_ridges.prefix = "whiteridge"
        metadata.variance.prefix = "variance"
        metadata.edges.prefix = "edges"
        metadata.meancurvature.prefix = "meancurvature"

    @process_schema("morphologist_bids", T1BiasCorrection)
    def morphologist_bids_T1BiasCorrection(metadata):
        brainvisa_T1BiasCorrection(metadata)

    @process_schema("brainvisa", HistoAnalysis)
    def brainvisa_HistoAnalysis(metadata):
        metadata["histo", "histo_analysis"].prefix = "nobias"
        metadata.histo.extension = "his"
        metadata.histo_analysis.extension = "han"

    @process_schema("morphologist_bids", HistoAnalysis)
    def morphologist_bids_HistoAnalysis(metadata):
        brainvisa_HistoAnalysis(metadata)

    @process_schema("brainvisa", BrainSegmentation)
    def brainvisa_BrainSegmentation(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.brain_mask.prefix = "brain"
        metadata["output:*"] = metadata.histo_analysis

    @process_schema("morphologist_bids", BrainSegmentation)
    def morphologist_bids_BrainSegmentation(metadata):
        brainvisa_BrainSegmentation(metadata)

    @process_schema("brainvisa", skullstripping)
    def brainvisa_skullstripping(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.skull_stripped.prefix = "skull_stripped"

    @process_schema("morphologist_bids", skullstripping)
    def morphologist_bids_skullstripping(metadata):
        brainvisa_skullstripping(metadata)

    @process_schema("brainvisa", ScalpMesh)
    def brainvisa_ScalpMesh(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.head_mask.prefix = "head"
        metadata.head_mesh.seg_directory = "segmentation/mesh"
        metadata.head_mesh.suffix = "head"
        metadata.head_mesh.prefix = None
        metadata.head_mesh.extension = "gii"

    @process_schema("morphologist_bids", ScalpMesh)
    def morphologist_bids_ScalpMesh(metadata):
        brainvisa_ScalpMesh(metadata)

    @process_schema("brainvisa", SplitBrain)
    def brainvisa_SplitBrain(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.split_brain.prefix = "voronoi"
        # TODO: check the conversion of the following code
        # split_brain = {
        #     "analysis": lambda **kwargs: f'{kwargs["initial_meta"].analysis}',
        # }
        metadata.split_brain.analysis = metadata.initial_meta.analysis
        metadata["output:*"] = metadata.histo_analysis

    @process_schema("morphologist_bids", SplitBrain)
    def morphologist_bids_SplitBrain(metadata):
        brainvisa_SplitBrain(metadata)

    @process_schema("brainvisa", GreyWhiteClassificationHemi)
    def brainvisa_GreyWhiteClassificationHemi(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.grey_white.prefix = "grey_white"
        metadata["output:*"] = metadata.histo_analysis

    @process_schema("morphologist_bids", GreyWhiteClassificationHemi)
    def morphologist_bids_GreyWhiteClassificationHemi(metadata):
        brainvisa_GreyWhiteClassificationHemi(metadata)

    @process_schema("brainvisa", GreyWhiteTopology)
    def brainvisa_GreyWhiteTopology(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.hemi_cortex.prefix = "cortex"
        metadata["output:*"] = metadata.histo_analysis

    @process_schema("morphologist_bids", GreyWhiteTopology)
    def morphologist_bids_GreyWhiteTopology(metadata):
        brainvisa_GreyWhiteTopology(metadata)

    @process_schema("brainvisa", GreyWhiteMesh)
    def brainvisa_GreyWhiteMesh(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.white_mesh.side = None
        metadata.white_mesh.prefix = None
        metadata.white_mesh.suffix = "white"
        metadata.white_mesh.extension = "gii"
        metadata["output:*"] = metadata.histo_analysis

    @process_schema("morphologist_bids", GreyWhiteMesh)
    def morphologist_bids_GreyWhiteMesh(metadata):
        brainvisa_GreyWhiteMesh(metadata)

    @process_schema("brainvisa", PialMesh)
    def brainvisa_PialMesh(metadata):
        metadata["*"].seg_directory = "segmentation/mesh"
        metadata.pial_mesh.side = None
        metadata.pial_mesh.prefix = None
        metadata.pial_mesh.suffix = "hemi"
        metadata.pial_mesh.extension = "gii"

    @process_schema("morphologist_bids", PialMesh)
    def morphologist_bids_PialMesh(metadata):
        brainvisa_PialMesh(metadata)

    @process_schema("brainvisa", SulciSkeleton)
    def brainvisa_SulciSkeleton(metadata):
        metadata["*"].seg_directory = "segmentation"
        metadata.roots.prefix = None
        metadata.skeleton.prefix = "skeleton"

    @process_schema("morphologist_bids", SulciSkeleton)
    def morphologist_bids_SulciSkeleton(metadata):
        brainvisa_SulciSkeleton(metadata)

    @process_schema("brainvisa", SulciGraph)
    def brainvisa_SulciGraph(metadata):
        metadata["*"].seg_directory = "folds"
        metadata["*"].sidebis = None
        metadata.graph.extension = "arg"
        metadata.graph.sulci_graph_version = (
            metadata.executable.CorticalFoldsGraph_graph_version
        )
        metadata.sulci_voronoi.prefix = "sulcivoronoi"
        metadata.sulci_voronoi.sulci_graph_version = (
            metadata.executable.CorticalFoldsGraph_graph_version
        )
        metadata.cortex_mid_interface.seg_directory = "segmentation"
        metadata.cortex_mid_interface.prefix = "gw_interface"
        # TODO: check conversion of the following code:
        # _meta_links = {
        #     "*_mesh": {"*": []},
        # }
        metadata["output"] = metadata.pial_mesh

    @process_schema("morphologist_bids", SulciGraph)
    def morphologist_bids_SulciGraph(metadata):
        brainvisa_SulciGraph(metadata)

    @process_schema("brainvisa", SulciLabellingANN)
    def brainvisa_SulciLabellingANN(metadata):
        metadata["*"].seg_directory = "folds"
        metadata.output_graph.suffix = metadata.output_graph.sulci_recognition_session
        metadata.output_graph.suffix.append(
            metadata.output_graph.sulci_recognition_type
        )
        metadata.output_graph.extension = "arg"
        metadata.energy_plot_file.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.energy_plot_file.suffix.append(
            metadata.output_graph.sulci_recognition_type
        )
        metadata.energy_plot_file.extension = "nr"

    @process_schema("morphologist_bids", SulciLabellingANN)
    def morphologist_bids_SulciLabellingANN(metadata):
        brainvisa_SulciLabellingANN(metadata)

    @process_schema("brainvisa_shared", SulciLabellingANN)
    def brainvisa_shared_SSulciLabellingANN(metadata):
        metadata["*"].model_version = "08"

    @process_schema("brainvisa", SulciLabellingSPAMGlobal)
    def brainvisa_SulciLabellingSPAMGlobal(metadata):
        metadata["*"].seg_directory = "folds"
        metadata.output_graph.suffix = metadata.output_graph.sulci_recognition_session
        metadata.output_graph.suffix.append(
            metadata.output_graph.sulci_recognition_type
        )
        metadata.output_graph.extension = "arg"
        metadata.posterior_probabilities.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.energy_plot_file.suffix.append("proba")
        metadata.energy_plot_file.extension = "csv"
        metadata.output_transformation.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.output_transformation.suffix.append("Tal_TO_SPAM")
        metadata.output_transformation.extension = "trm"
        metadata.output_t1_to_global_transformation.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.output_t1_to_global_transformation.suffix.append("T1_TO_SPAM")
        metadata.output_t1_to_global_transformation.extension = "trm"

    @process_schema("morphologist_bids", SulciLabellingSPAMGlobal)
    def morphologist_bids_SulciLabellingSPAMGlobal(metadata):
        brainvisa_SulciLabellingSPAMGlobal(metadata)

    @process_schema("brainvisa", SulciLabellingSPAMLocal)
    def brainvisa_SulciLabellingSPAMLocal(metadata):
        metadata["*"].seg_directory = "folds"
        metadata.output_graph.suffix = metadata.output_graph.sulci_recognition_session
        metadata.output_graph.suffix.append(
            metadata.output_graph.sulci_recognition_type
        )
        metadata.output_graph.extension = "arg"
        metadata.posterior_probabilities.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.energy_plot_file.suffix.append("proba")
        metadata.energy_plot_file.extension = "csv"
        metadata.output_local_transformations.suffix = (
            metadata.output_graph.sulci_recognition_session
        )
        metadata.output_local_transformations.suffix.append("global_TO_local")
        metadata.output_local_transformations.extension = None

    @process_schema("morphologist_bids", SulciLabellingSPAMLocal)
    def morphologist_bids_SulciLabellingSPAMLocal(metadata):
        brainvisa_SulciLabellingSPAMLocal(metadata)

    # class SulciLabellingSPAMMarkovBrainVISA(
    #     ProcessSchema, schema="brainvisa", process=SulciLabellingSPAMMarkov
    # ):
    #     _ = {
    #         "*": {"seg_directory": "folds"},
    #     }
    #     output_graph = {
    #         "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
    #         f'_{kwargs["metadata"].sulci_recognition_type}',
    #         "extension": "arg",
    #     }
    #     posterior_probabilities = {
    #         "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_proba',
    #         "extension": "csv",
    #     }

    # class SulciLabellingSPAMMarkovBIDS(
    #     SulciLabellingSPAMMarkovBrainVISA,
    #     schema="morphologist_bids",
    #     process=SulciLabellingSPAMMarkov,
    # ):
    #     pass

    # class SulciDeepLabelingBrainVISA(
    #     ProcessSchema, schema="brainvisa", process=SulciDeepLabeling
    # ):
    #     _ = {"*": {"seg_directory": "folds"}}

    #     metadata_per_parameter = {
    #         "*": {
    #             "unused": [
    #                 "subject_only",
    #                 "sulci_recognition_session",
    #                 "sulci_graph_version",
    #             ]
    #         },
    #         "graph": {"unused": ["subject_only", "sulci_recognition_session"]},
    #         "roots": {
    #             "unused": [
    #                 "subject_only",
    #                 "sulci_recognition_session",
    #                 "sulci_graph_version",
    #             ]
    #         },
    #         "skeleton": {
    #             "unused": [
    #                 "subject_only",
    #                 "sulci_recognition_session",
    #                 "sulci_graph_version",
    #             ]
    #         },
    #         "labeled_graph": {"unused": ["subject_only"]},
    #     }

    #     graph = {"extension": "arg"}
    #     roots = {
    #         "seg_directory": "segmentation",
    #         "prefix": "roots",
    #         "extension": "nii.gz",
    #     }
    #     skeleton = {
    #         "seg_directory": "segmentation",
    #         "prefix": "skeleton",
    #         "extension": "nii.gz",
    #     }
    #     labeled_graph = {
    #         "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
    #         f'_{kwargs["metadata"].sulci_recognition_type}',
    #         "extension": "arg",
    #     }

    # class SulciDeepLabelingBIDS(
    #     SulciDeepLabelingBrainVISA,
    #     schema="morphologist_bids",
    #     process=SulciDeepLabeling,
    # ):
    #     pass

    # class SulciDeepLabelingShared(
    #     ProcessSchema, schema="brainvisa_shared", process=SulciDeepLabeling
    # ):
    #     model_file = {"data_id": "sulci_cnn_recognition_model", "model_version": "19"}
    #     param_file = {"data_id": "sulci_cnn_recognition_param", "model_version": "19"}

    # class sulcigraphmorphometrybysubjectBrainVISA(
    #     ProcessSchema, schema="brainvisa", process=sulcigraphmorphometrybysubject
    # ):
    #     sulcal_morpho_measures = {
    #         "extension": "csv",
    #         "side": None,
    #         "_": Append("suffix", "sulcal_morphometry"),
    #     }

    # class sulcigraphmorphometrybysubjectBIDS(
    #     sulcigraphmorphometrybysubjectBrainVISA,
    #     schema="morphologist_bids",
    #     process=sulcigraphmorphometrybysubject,
    # ):
    #     pass

    # class BrainVolumesBrainVISA(
    #     ProcessSchema, schema="brainvisa", process=brainvolumes
    # ):
    #     _ = {"*": {"seg_directory": "segmentation"}}
    #     metadata_per_parameter = {
    #         "*": {
    #             "unused": [
    #                 "subject_only",
    #                 "sulci_graph_version",
    #                 "sulci_recognition_session",
    #             ]
    #         },
    #         "*_labelled_graph": {"unused": ["subject_only"]},
    #         "subject": {"used": ["subject_only", "subject"]},
    #     }
    #     left_csf = {
    #         "prefix": "csf",
    #         "side": "L",
    #         "sidebis": None,
    #         "suffix": None,
    #         "extension": "nii.gz",  # should not be hard-coded but I failed
    #     }
    #     right_csf = {
    #         "prefix": "csf",
    #         "side": "R",
    #         "sidebis": None,
    #         "suffix": None,
    #         "extension": "nii.gz",  # should not be hard-coded but I failed
    #     }
    #     brain_volumes_file = {
    #         "prefix": "brain_volumes",
    #         "suffix": None,
    #         "side": None,
    #         "sidebis": None,
    #         "extension": "csv",
    #     }
    #     subject = {
    #         "seg_directory": None,
    #         "prefix": None,
    #         "side": None,
    #         "subject_in_filename": False,
    #     }
    #     _meta_links = {
    #         "*_labelled_graph": {"*": []},
    #         "*_grey_white": {"*": []},
    #         "*_mesh": {"*": []},
    #         "left_grey_white": {"left_csf": ["extension"]},  # no effect ..?
    #         "right_grey_white": {"right_csf": ["extension"]},  # no effect ..?
    #     }

    # class BrainVolumesBIDS(
    #     BrainVolumesBrainVISA, schema="morphologist_bids", process=brainvolumes
    # ):
    #     pass

    # class MorphoReportBrainVISA(
    #     ProcessSchema, schema="brainvisa", process=morpho_report
    # ):
    #     _ = {"*": {"seg_directory": None}}
    #     metadata_per_parameter = {
    #         "*": {
    #             "unused": [
    #                 "subject_only",
    #                 "sulci_graph_version",
    #                 "sulci_recognition_session",
    #             ]
    #         },
    #         "*_labelled_graph": {"unused": ["subject_only"]},
    #         "subject": {"used": ["subject_only", "subject"]},
    #     }
    #     report = {
    #         "prefix": None,
    #         "side": None,
    #         "sidebis": None,
    #         "subject_in_filename": False,
    #         "suffix": "morphologist_report",
    #         "extension": "pdf",
    #     }
    #     subject = {
    #         "prefix": None,
    #         "side": None,
    #         "subject_in_filename": False,
    #     }

    # class MorphoReportBIDS(
    #     MorphoReportBrainVISA, schema="morphologist_bids", process=morpho_report
    # ):
    #     pass

    # class MorphologistShared(
    #     ProcessSchema, schema="brainvisa_shared", process=Morphologist
    # ):
    #     PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template = {
    #         "data_id": "normalization_template"
    #     }
    #     PrepareSubject_Normalization_NormalizeFSL_template = {
    #         "data_id": "normalization_template"
    #     }
    #     PrepareSubject_Normalization_NormalizeSPM_template = {
    #         "data_id": "normalization_template"
    #     }
    #     PrepareSubject_Normalization_NormalizeBaladin_template = {
    #         "data_id": "normalization_template"
    #     }
    #     PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {
    #         "data_id": "trans_acpc_to_mni"
    #     }
    #     PrepareSubject_TalairachFromNormalization_acpc_referential = {
    #         "data_id": "acpc_ref"
    #     }
    #     Renorm_template = {"data_id": "normalization_template_brain"}
    #     Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {
    #         "data_id": "trans_mni_to_acpc"
    #     }
    #     PrepareSubject_TalairachFromNormalization_normalized_referential = {
    #         "data_id": "icbm152_ref"
    #     }
    #     PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized = {
    #         "data_id": "trans_acpc_to_mni"
    #     }
    #     SplitBrain_split_template = {"data_id": "hemi_split_template"}
    #     sulcal_morphometry_sulci_file = {"data_id": "sulcal_morphometry_sulci_file"}
    #     SulciRecognition_recognition2000_model = {
    #         "data_id": "sulci_ann_recognition_model",
    #         "side": "L",
    #         "graph_version": "3.1",
    #     }
    #     SulciRecognition_1_recognition2000_model = {
    #         "data_id": "sulci_ann_recognition_model",
    #         "side": "R",
    #         "graph_version": "3.1",
    #     }
    #     SPAM_recognition_labels_translation_map = {
    #         "data_id": "sulci_spam_recognition_labels_trans",
    #         "model_version": "08",
    #     }
    #     SulciRecognition_SPAM_recognition09_global_recognition_model = {
    #         "data_id": "sulci_spam_recognition_global_model",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_global_recognition_model = {
    #         "data_id": "sulci_spam_recognition_global_model",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_local_recognition_model = {
    #         "data_id": "sulci_spam_recognition_local_model",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_local_recognition_model = {
    #         "data_id": "sulci_spam_recognition_local_model",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_markovian_recognition_model = {
    #         "data_id": "sulci_spam_recognition_global_model",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_markovian_recognition_model = {
    #         "data_id": "sulci_spam_recognition_global_model",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_global_recognition_labels_priors = {
    #         "data_id": "sulci_spam_recognition_global_labels_priors",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors = {
    #         "data_id": "sulci_spam_recognition_global_labels_priors",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_local_recognition_local_referentials = {
    #         "data_id": "sulci_spam_recognition_local_refs",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials = {
    #         "data_id": "sulci_spam_recognition_local_refs",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_local_recognition_direction_priors = {
    #         "data_id": "sulci_spam_recognition_local_dir_priors",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors = {
    #         "data_id": "sulci_spam_recognition_local_dir_priors",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_SPAM_recognition09_local_recognition_angle_priors = {
    #         "data_id": "sulci_spam_recognition_local_angle_priors",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors = {
    #         "data_id": "sulci_spam_recognition_local_angle_priors",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_local_recognition_translation_priors = {
    #         "data_id": "sulci_spam_recognition_local_trans_priors",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors = {
    #         "data_id": "sulci_spam_recognition_local_trans_priors",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model = {
    #         "data_id": "sulci_spam_recognition_markov_rels",
    #         "model_version": "08",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model = {
    #         "data_id": "sulci_spam_recognition_markov_rels",
    #         "model_version": "08",
    #         "side": "R",
    #     }
    #     SulciRecognition_CNN_recognition19_model_file = {
    #         "data_id": "sulci_cnn_recognition_model",
    #         "model_version": "19",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_CNN_recognition19_model_file = {
    #         "data_id": "sulci_cnn_recognition_model",
    #         "model_version": "19",
    #         "side": "R",
    #     }
    #     SulciRecognition_CNN_recognition19_param_file = {
    #         "data_id": "sulci_cnn_recognition_param",
    #         "model_version": "19",
    #         "side": "L",
    #     }
    #     SulciRecognition_1_CNN_recognition19_param_file = {
    #         "data_id": "sulci_cnn_recognition_param",
    #         "model_version": "19",
    #         "side": "R",
    #     }
