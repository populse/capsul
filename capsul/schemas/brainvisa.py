import copy
import importlib

from soma.controller import undefined

from capsul.dataset import MetadataSchema, SchemaMapping, process_schema


class BrainVISASharedSchema(MetadataSchema):
    """Metadata schema for BrainVISA shared dataset"""

    schema_name = "brainvisa_shared"
    data_id: str = ""
    side: str = None
    sulci_graph_version: str = None
    model_version: str = None

    def _path_list(self, unused_meta=None):
        """
        The path has the following pattern:
        <something>
        """

        full_side = {"L": "left", "R": "right", None: "<None>"}
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
                self.sulci_graph_version,
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
        dest.sulci_graph_version = source.sulci_graph_version


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
        metadata["output:*"].modality = "t1mri"
        metadata["*_pass1"].suffix.append("pass1")
        metadata["left_*"].side = "L"
        metadata["right_*"].side = "R"
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
        metadata.subject.subject.used()

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

        metadata["left_graph", "right_graph"].sulci_recognition_session.unused()
        # metadata["left_graph", "right_graph"].prefix = None
        # metadata["left_graph", "right_graph"].suffix = None

    @process_schema("bids", Morphologist)
    def bids_Morphologist(metadata):
        metadata["output:*"].modality = "t1mri"
        metadata["output:*"].folder = "derivative"
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
        metadata["output:*"].seg_directory = None
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
        metadata.meancurvature.prefix = "mean_curvature"

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
        metadata["output:*"] = metadata.t1mri_nobias
        metadata["output:*"].seg_directory = "segmentation"
        metadata.brain_mask.prefix = "brain"

    @process_schema("morphologist_bids", BrainSegmentation)
    def morphologist_bids_BrainSegmentation(metadata):
        brainvisa_BrainSegmentation(metadata)

    @process_schema("brainvisa", skullstripping)
    def brainvisa_skullstripping(metadata):
        metadata["output:*"].seg_directory = "segmentation"
        metadata.skull_stripped.prefix = "skull_stripped"

    @process_schema("morphologist_bids", skullstripping)
    def morphologist_bids_skullstripping(metadata):
        brainvisa_skullstripping(metadata)

    @process_schema("brainvisa", ScalpMesh)
    def brainvisa_ScalpMesh(metadata):
        metadata["output:*"].seg_directory = "segmentation"
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
        metadata["output:*"] = metadata.brain_mask
        metadata["output:*"].seg_directory = "segmentation"
        metadata.split_brain.prefix = "voronoi"
        # TODO: check the conversion of the following code
        # split_brain = {
        #     "analysis": lambda **kwargs: f'{kwargs["initial_meta"].analysis}',
        # }
        metadata.split_brain.analysis = metadata.initial_meta.analysis

    @process_schema("morphologist_bids", SplitBrain)
    def morphologist_bids_SplitBrain(metadata):
        brainvisa_SplitBrain(metadata)

    @process_schema("brainvisa", GreyWhiteClassificationHemi)
    def brainvisa_GreyWhiteClassificationHemi(metadata):
        side = metadata.executable.side
        reside = {"left": "L", "right": "R"}.get(side, side)
        metadata["output:*"] = metadata.t1mri_nobias
        metadata["output:*"].seg_directory = "segmentation"
        metadata.grey_white.prefix = "grey_white"
        metadata.grey_white.side = reside
        metadata.side.side = reside

    @process_schema("morphologist_bids", GreyWhiteClassificationHemi)
    def morphologist_bids_GreyWhiteClassificationHemi(metadata):
        brainvisa_GreyWhiteClassificationHemi(metadata)

    @process_schema("brainvisa", GreyWhiteTopology)
    def brainvisa_GreyWhiteTopology(metadata):
        metadata["output:*"] = metadata.grey_white
        metadata["output:*"].seg_directory = "segmentation"
        metadata.hemi_cortex.prefix = "cortex"

    @process_schema("morphologist_bids", GreyWhiteTopology)
    def morphologist_bids_GreyWhiteTopology(metadata):
        brainvisa_GreyWhiteTopology(metadata)

    @process_schema("brainvisa", GreyWhiteMesh)
    def brainvisa_GreyWhiteMesh(metadata):
        metadata["output:*"] = metadata.hemi_cortex
        metadata["output:*"].seg_directory = "segmentation/mesh"
        metadata.white_mesh.sidebis = metadata.white_mesh.side
        metadata.white_mesh.side.unused()
        metadata.white_mesh.prefix = None
        metadata.white_mesh.suffix = "white"
        metadata.white_mesh.extension = "gii"

    @process_schema("morphologist_bids", GreyWhiteMesh)
    def morphologist_bids_GreyWhiteMesh(metadata):
        brainvisa_GreyWhiteMesh(metadata)

    @process_schema("brainvisa", PialMesh)
    def brainvisa_PialMesh(metadata):
        metadata.pial_mesh = metadata.hemi_cortex
        metadata["output:*"].seg_directory = "segmentation/mesh"
        metadata.pial_mesh.sidebis = metadata.pial_mesh.side
        print("side:", metadata.pial_mesh.sidebis.value())
        metadata.pial_mesh.side.unused()
        metadata.pial_mesh.prefix = None
        metadata.pial_mesh.suffix = "hemi"
        metadata.pial_mesh.extension = "gii"

    @process_schema("morphologist_bids", PialMesh)
    def morphologist_bids_PialMesh(metadata):
        brainvisa_PialMesh(metadata)

    @process_schema("brainvisa", SulciSkeleton)
    def brainvisa_SulciSkeleton(metadata):
        metadata["output:*"] = metadata.hemi_cortex
        metadata["output:*"].seg_directory = "segmentation"
        metadata.roots.prefix = "roots"
        metadata.skeleton.prefix = "skeleton"

    @process_schema("morphologist_bids", SulciSkeleton)
    def morphologist_bids_SulciSkeleton(metadata):
        brainvisa_SulciSkeleton(metadata)

    @process_schema("brainvisa", SulciGraph)
    def brainvisa_SulciGraph(metadata):
        metadata["output:*"] = metadata.skeleton
        metadata["output:*"].seg_directory = "folds"
        metadata["output:*"].sidebis = None
        metadata.graph.extension = "arg"
        metadata.graph.sulci_graph_version = (
            metadata.executable.pipeline.CorticalFoldsGraph_graph_version
        )
        metadata.graph.sulci_recognition_session.unused()
        metadata.graph.prefix = None
        metadata.sulci_voronoi.prefix = "sulcivoronoi"
        metadata.sulci_voronoi.sulci_graph_version = (
            metadata.executable.pipeline.CorticalFoldsGraph_graph_version
        )
        metadata.sulci_voronoi.sulci_graph_version.used()
        metadata.sulci_voronoi.sulci_recognition_session.unused()
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
        metadata["output:*"].seg_directory = "folds"
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
        metadata["output:*"].model_version = "08"

    @process_schema("brainvisa", SulciLabellingSPAMGlobal)
    def brainvisa_SulciLabellingSPAMGlobal(metadata):
        metadata["output:*"].seg_directory = "folds"
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
        metadata["output:*"].seg_directory = "folds"
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

    @process_schema("brainvisa", SulciLabellingSPAMMarkov)
    def brainvisa_SulciLabellingSPAMMarkov(metadata):
        metadata["output:*"].seg_directory = "folds"
        metadata.graph.seg_directory = "folds"
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

    @process_schema("morphologist_bids", SulciLabellingSPAMMarkov)
    def morphologist_bids_SulciLabellingSPAMMarkov(metadata):
        brainvisa_SulciLabellingSPAMMarkov(metadata)

    @process_schema("brainvisa", SulciDeepLabeling)
    def brainvisa_SulciDeepLabeling(metadata):
        metadata["output:*"].seg_directory = "folds"
        metadata.graph.seg_directory = "folds"
        metadata.graph["sulci_graph_version"].used()
        metadata.graph.extension = "arg"
        metadata.labeled_graph[
            "sulci_graph_version", "sulci_recognition_session"
        ].used()
        metadata.roots.seg_directory = "segmentation"
        metadata.roots.prefix = "roots"
        metadata.roots.extension = "nii.gz"
        metadata.skeleton.seg_directory = "segmentation"
        metadata.skeleton.prefix = "skeleton"
        metadata.skeleton.extension = "nii.gz"
        metadata.skeleton.seg_directory = "segmentation"
        metadata.skeleton.prefix = "skeleton"
        metadata.skeleton.extension = "nii.gz"

        metadata.labeled_graph.suffix = metadata.labeled_graph.sulci_recognition_session
        metadata.labeled_graph.suffix.append(
            metadata.labeled_graph.sulci_recognition_type
        )
        metadata.labeled_graph.extension = "arg"

    @process_schema("morphologist_bids", SulciDeepLabeling)
    def morphologist_bids_SulciDeepLabeling(metadata):
        brainvisa_SulciDeepLabeling(metadata)

    @process_schema("brainvisa_shared", SulciDeepLabeling)
    def brainvisa_shared_SulciDeepLabeling(metadata):
        metadata.model_file.data_id = "sulci_cnn_recognition_model"
        metadata.model_file.model_version = "19"
        metadata.param_file.data_id = "sulci_cnn_recognition_param"
        metadata.param_file.model_version = "19"

    @process_schema("brainvisa", sulcigraphmorphometrybysubject)
    def brainvisa_sulcigraphmorphometrybysubject(metadata):
        metadata.sulcal_morpho_measures.extension = "csv"
        metadata.sulcal_morpho_measures.side = None
        metadata.sulcal_morpho_measures.suffix.append("sulcal_morphometry")

    @process_schema("morphologist_bids", sulcigraphmorphometrybysubject)
    def morphologist_bids_sulcigraphmorphometrybysubject(metadata):
        brainvisa_sulcigraphmorphometrybysubject(metadata)

    @process_schema("brainvisa", brainvolumes)
    def brainvisa_brainvolumes(metadata):
        metadata["output:*"].seg_directory = "segmentation"
        metadata["*_labelled_graph"][
            "sulci_graph_version", "sulci_recognition_session"
        ].used()
        metadata.subject["*"].unused()
        metadata.subject["subject"].used()

        metadata.left_csf.prefix = "csf"
        metadata.left_csf.side = "L"
        metadata.left_csf.sidebis = None
        metadata.left_csf.suffix = None
        metadata.left_csf.extension = "nii.gz"

        metadata.right_csf.prefix = "csf"
        metadata.right_csf.side = "R"
        metadata.right_csf.sidebis = None
        metadata.right_csf.suffix = None
        metadata.right_csf.extension = "nii.gz"

        metadata.brain_volumes_file.prefix = "brain_volumes"
        metadata.brain_volumes_file.side = None
        metadata.brain_volumes_file.sidebis = None
        metadata.brain_volumes_file.suffix = None
        metadata.brain_volumes_file.extension = "csv"

        metadata["output:*"] = metadata.left_labelled_graph
        metadata.left_csf.extension = metadata.left_grey_white.extension

    @process_schema("morphologist_bids", brainvolumes)
    def morphologist_bids_brainvolumes(metadata):
        brainvisa_brainvolumes(metadata)

    @process_schema("brainvisa", morpho_report)
    def brainvisa_morpho_report(metadata):
        metadata["output:*"].seg_directory = "segmentation"
        metadata.report.seg_directory = None
        metadata["*_labelled_graph"][
            "sulci_graph_version", "sulci_recognition_session"
        ].used()
        metadata.subject["*"].unused()
        metadata.subject["subject"].used()
        metadata.report.prefix = None
        metadata.report.side = None
        metadata.report.sidebis = None
        metadata.report.subject_in_filename = False
        metadata.report.suffix = "morphologist_report"
        metadata.report.extension = "pdf"
        metadata.subject.prefix = None
        metadata.subject.side = None
        metadata.subject.subject_in_filename = False

    @process_schema("morphologist_bids", morpho_report)
    def morphologist_bids_morpho_report(metadata):
        brainvisa_morpho_report(metadata)

    @process_schema("brainvisa_shared", Morphologist)
    def brainvisa_shared_Morphologist(metadata):
        metadata.PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template.data_id = "normalization_template"
        metadata.PrepareSubject_Normalization_NormalizeFSL_template.data_id = (
            "normalization_template"
        )
        metadata.PrepareSubject_Normalization_NormalizeSPM_template.data_id = (
            "normalization_template"
        )
        metadata.PrepareSubject_Normalization_NormalizeBaladin_template.data_id = (
            "normalization_template"
        )
        metadata.PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc.data_id = "trans_acpc_to_mni"
        metadata.PrepareSubject_TalairachFromNormalization_acpc_referential.data_id = (
            "acpc_ref"
        )
        metadata.Renorm_template.data_id = "normalization_template_brain"
        metadata.Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc.data_id = "trans_mni_to_acpc"
        metadata.PrepareSubject_TalairachFromNormalization_normalized_referential.data_id = "icbm152_ref"
        metadata.PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized.data_id = "trans_acpc_to_mni"
        metadata.SplitBrain_split_template.data_id = "hemi_split_template"
        metadata.sulcal_morphometry_sulci_file.data_id = "sulcal_morphometry_sulci_file"
        metadata.SulciRecognition_recognition2000_model.data_id = (
            "sulci_ann_recognition_model"
        )
        metadata.SulciRecognition_recognition2000_model.side = "L"
        metadata.SulciRecognition_recognition2000_model.graph_version = "3.1"
        metadata.SulciRecognition_1_recognition2000_model.data_id = (
            "sulci_ann_recognition_model"
        )
        metadata.SulciRecognition_1_recognition2000_model.side = "R"
        metadata.SulciRecognition_1_recognition2000_model.graph_version = "3.1"
        metadata.SPAM_recognition_labels_translation_map.data_id = (
            "sulci_spam_recognition_labels_trans"
        )
        metadata.SPAM_recognition_labels_translation_map.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_model.data_id = "sulci_spam_recognition_global_model"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_model.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_model.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_model.data_id = "sulci_spam_recognition_global_model"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_model.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_model.side = (
            "R"
        )
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_model.data_id = (
            "sulci_spam_recognition_local_model"
        )
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_model.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_model.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_model.data_id = "sulci_spam_recognition_local_model"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_model.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_model.side = (
            "R"
        )
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_model.data_id = "sulci_spam_recognition_global_model"
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_model.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_model.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_model.data_id = "sulci_spam_recognition_global_model"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_model.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_model.side = "R"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_labels_priors.data_id = "sulci_spam_recognition_global_labels_priors"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_labels_priors.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_global_recognition_labels_priors.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors.data_id = "sulci_spam_recognition_global_labels_priors"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors.side = "R"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_local_referentials.data_id = "sulci_spam_recognition_local_refs"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_local_referentials.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_local_referentials.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials.data_id = "sulci_spam_recognition_local_refs"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials.side = "R"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_direction_priors.data_id = "sulci_spam_recognition_local_dir_priors"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_direction_priors.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_direction_priors.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors.data_id = "sulci_spam_recognition_local_dir_priors"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors.side = "L"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_angle_priors.data_id = "sulci_spam_recognition_local_angle_priors"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_angle_priors.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_angle_priors.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors.data_id = "sulci_spam_recognition_local_angle_priors"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors.side = "R"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_translation_priors.data_id = "sulci_spam_recognition_local_trans_priors"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_translation_priors.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_local_recognition_translation_priors.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors.data_id = "sulci_spam_recognition_local_trans_priors"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors.side = "R"
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model.data_id = "sulci_spam_recognition_markov_rels"
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model.model_version = "08"
        metadata.SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model.side = "L"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model.data_id = "sulci_spam_recognition_markov_rels"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model.model_version = "08"
        metadata.SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model.side = "R"
        metadata.SulciRecognition_CNN_recognition19_model_file.data_id = (
            "sulci_cnn_recognition_model"
        )
        metadata.SulciRecognition_CNN_recognition19_model_file.model_version = "19"
        metadata.SulciRecognition_CNN_recognition19_model_file.side = "L"
        metadata.SulciRecognition_1_CNN_recognition19_model_file.data_id = (
            "sulci_cnn_recognition_model"
        )
        metadata.SulciRecognition_1_CNN_recognition19_model_file.model_version = "19"
        metadata.SulciRecognition_1_CNN_recognition19_model_file.side = "R"
        metadata.SulciRecognition_CNN_recognition19_param_file.data_id = (
            "sulci_cnn_recognition_param"
        )
        metadata.SulciRecognition_CNN_recognition19_param_file.model_version = "19"
        metadata.SulciRecognition_CNN_recognition19_param_file.side = "L"
        metadata.SulciRecognition_1_CNN_recognition19_param_file.data_id = (
            "sulci_cnn_recognition_param"
        )
        metadata.SulciRecognition_1_CNN_recognition19_param_file.model_version = "19"
        metadata.SulciRecognition_1_CNN_recognition19_param_file.side = "R"
