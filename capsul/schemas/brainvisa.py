from capsul.dataset import ProcessSchema, MetadataSchema, Append, SchemaMapping
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

    bv_acq_meta = {
        "unused": [
            "subject_only",
            "analysis",
            "seg_directory",
            "side",
            "sidebis",
            "sulci_graph_version",
            "sulci_recognition_session",
        ]
    }
    bv_t1_meta = copy.deepcopy(bv_acq_meta)
    bv_t1_meta["unused"] += ["suffix"]
    bv_ref_meta = copy.deepcopy(bv_acq_meta)
    bv_ref_meta["unused"].remove("seg_directory")

    def updated(d, *args):
        res = copy.deepcopy(d)
        for d2 in args:
            res.update(d2)
        return res

    class MorphologistBrainVISA(
        ProcessSchema, schema="brainvisa", process=Morphologist
    ):
        _ = {
            "*": {"process": None, "modality": "t1mri"},
            "*_pass1": Append("suffix", "pass1"),
            "*_labelled_graph": {
                "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
                f'_{kwargs["metadata"].sulci_recognition_type}',
            },
            "left_*": {"side": "L"},
            "right_*": {"side": "R"},
        }

        _nodes = {
            "GreyWhiteClassification": {"*": {"side": "L"}},
            "GreyWhiteTopology": {"*": {"side": "L"}},
            "GreyWhiteMesh": {"*": {"sidebis": "L"}},
            "PialMesh": {"*": {"sidebis": "L"}},
            "SulciSkeleton": {"*": {"side": "L"}},
            "CorticalFoldsGraph": {"*": {"side": "L"}},
            "SulciRecognition": {"*": {"side": "L"}},
            "*_1": {"*": {"side": "R"}},
            "GreyWhiteMesh_1": {"*": {"sidebis": "R", "side": None}},
            "PialMesh_1": {"*": {"sidebis": "R", "side": None}},
            "SulciRecognition*": {
                "*": {
                    "sulci_graph_version": lambda **kwargs: f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
                    "prefix": None,
                    "sidebis": None,
                }
            },
            "*.ReorientAnatomy": {
                "_meta_links": {
                    "transformation": {
                        "*": [],
                    },
                },
            },
            "*.Convert*normalizationToAIMS": {
                "_meta_links": {
                    "*": {
                        "*": [],
                    },
                },
            },
        }

        metadata_per_parameter = {
            "*": {
                "unused": [
                    "subject_only",
                    "sulci_graph_version",
                    "sulci_recognition_session",
                ]
            },
            "*_graph": {"unused": ["subject_only", "sulci_recognition_session"]},
            "*_labelled_graph": {"unused": ["subject_only"]},
            "t1mri": bv_t1_meta,
            "imported_t1mri": bv_t1_meta,
            "reoriented_t1mri": bv_t1_meta,
            "normalized_t1mri": bv_acq_meta,
            "normalization_spm_native_transformation": bv_acq_meta,
            "commissure_coordinates": bv_t1_meta,
            "t1mri_referential": bv_ref_meta,
            "Talairach_transform": bv_ref_meta,
            "MNI_transform": bv_ref_meta,
            "subject": {"used": ["subject_only", "subject"]},
            "sulcal_morpho_measures": {"unused": ["subject_only"]},
        }

        normalization_spm_native_transformation = {"prefix": None}
        commissure_coordinates = {
            "extension": "APC",
        }
        t1mri_referential = {
            "seg_directory": "registration",
            "short_prefix": "RawT1-",
            "suffix": lambda **kwargs: f'{kwargs["metadata"].acquisition}',
            "extension": "referential",
        }
        Talairach_transform = {
            "seg_directory": "registration",
            "prefix": "",
            "short_prefix": "RawT1-",
            "suffix": lambda **kwargs: f'{kwargs["metadata"].acquisition}_TO_Talairach-ACPC',
            "extension": "trm",
        }
        MNI_transform = {
            "seg_directory": "registration",
            "prefix": "",
            "short_prefix": "RawT1-",
            "suffix": lambda **kwargs: f'{kwargs["metadata"].acquisition}_TO_Talairach-MNI',
            "extension": "trm",
        }
        left_graph = {
            "prefix": None,
            "suffix": None,
        }
        right_graph = {
            "prefix": None,
            "suffix": None,
        }
        subject = {"subject_only": True}
        sulcal_morpho_measures = {"subject_only": False}

    class MorphologistBIDS(
        MorphologistBrainVISA, schema="morphologist_bids", process=Morphologist
    ):
        _ = {
            "*": {"process": None, "modality": "t1mri", "folder": "derivative"},
            "*_pass1": Append("suffix", "pass1"),
            "*_labelled_graph": {
                "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
                f'_{kwargs["metadata"].sulci_recognition_type}',
            },
            "left_*": {"side": "L"},
            "right_*": {"side": "R"},
        }
        t1mri = {
            "folder": "rawdata",
        }

    class SPM12NormalizationBrainVISA(
        ProcessSchema, schema="brainvisa", process=normalization_t1_spm12_reinit
    ):
        transformations_informations = {
            "analysis": undefined,
            "suffix": "sn",
            "extension": "mat",
        }
        normalized_anatomy_data = {
            "analysis": undefined,
            "prefix": "normalized_SPM",
            "extension": "nii",
        }

    class SPM12NormalizationBIDS(
        SPM12NormalizationBrainVISA,
        schema="morphologist_bids",
        process=normalization_t1_spm12_reinit,
    ):
        pass

    class SPM12NormalizationShared(
        ProcessSchema, schema="brainvisa_shared", process=normalization_t1_spm12_reinit
    ):
        anatomical_template = {"data_id": "normalization_template"}

    class SPM8NormalizationBrainVISA(
        ProcessSchema, schema="brainvisa", process=normalization_t1_spm8_reinit
    ):
        transformations_informations = {
            "analysis": undefined,
            "suffix": "sn",
            "extension": "mat",
        }
        normalized_anatomy_data = {
            "analysis": undefined,
            "prefix": "normalized_SPM",
            "extension": "nii",
        }

    class SPM8NormalizationBIDS(
        SPM8NormalizationBrainVISA,
        schema="morphologist_bids",
        process=normalization_t1_spm8_reinit,
    ):
        pass

    class SPM8NormalizationShared(
        ProcessSchema, schema="brainvisa_shared", process=normalization_t1_spm8_reinit
    ):
        anatomical_template = {"data_id": "normalization_template"}

    class AimsNormalizationBrainVISA(
        ProcessSchema, schema="brainvisa", process=normalization_aimsmiregister
    ):
        transformation_to_ACPC = {"prefix": "normalized_aims", "extension": "trm"}

    class AimsNormalizationBIDS(
        AimsNormalizationBrainVISA,
        schema="morphologist_bids",
        process=normalization_aimsmiregister,
    ):
        pass

    class AimsNormalizationShared(
        ProcessSchema, schema="brainvisa_shared", process=normalization_aimsmiregister
    ):
        anatomical_template = {"data_id": "normalization_template"}

    class FSLNormalizationBrainVISA(
        ProcessSchema, schema="brainvisa", process=Normalization_FSL_reinit
    ):
        transformation_matrix = {
            "seg_directory": "registration",
            "analysis": undefined,
            "suffix": "fsl",
            "extension": "mat",
        }
        normalized_anatomy_data = {
            "seg_directory": None,
            "analysis": undefined,
            "prefix": "normalized_FSL",
            "suffix": None,
        }

    class FSLNormalizationBIDS(
        FSLNormalizationBrainVISA,
        schema="morphologist_bids",
        process=Normalization_FSL_reinit,
    ):
        pass

    class T1BiasCorrectionBrainVISA(
        ProcessSchema, schema="brainvisa", process=T1BiasCorrection
    ):
        _ = {
            "*": {
                "seg_directory": None,
                "analysis": lambda **kwargs: f'{kwargs["initial_meta"].analysis}',
            }
        }
        t1mri_nobias = {"prefix": "nobias"}
        b_field = {"prefix": "biasfield"}
        hfiltered = {"prefix": "hfiltered"}
        white_ridges = {"prefix": "whiteridge"}
        variance = {"prefix": "variance"}
        edges = {"prefix": "edges"}
        meancurvature = {"prefix": "meancurvature"}

    class T1BiasCorrectionBIDS(
        T1BiasCorrectionBrainVISA, schema="morphologist_bids", process=T1BiasCorrection
    ):
        pass

    class HistoAnalysisBrainVISA(
        ProcessSchema, schema="brainvisa", process=HistoAnalysis
    ):
        histo = {"prefix": "nobias", "extension": "his"}
        histo_analysis = {"prefix": "nobias", "extension": "han"}

    class HistoAnalysisBIDS(
        HistoAnalysisBrainVISA, schema="morphologist_bids", process=HistoAnalysis
    ):
        pass

    class BrainSegmentationBrainVISA(
        ProcessSchema, schema="brainvisa", process=BrainSegmentation
    ):
        _ = {"*": {"seg_directory": "segmentation"}}
        brain_mask = {"prefix": "brain"}
        _meta_links = {
            "histo_analysis": {
                "*": [],
            }
        }

    class BrainSegmentationBIDS(
        BrainSegmentationBrainVISA,
        schema="morphologist_bids",
        process=BrainSegmentation,
    ):
        pass

    class skullstrippingBrainVISA(
        ProcessSchema, schema="brainvisa", process=skullstripping
    ):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        skull_stripped = {"prefix": "skull_stripped"}

    class skullstrippingBIDS(
        skullstrippingBrainVISA, schema="morphologist_bids", process=skullstripping
    ):
        pass

    class ScalpMeshBrainVISA(ProcessSchema, schema="brainvisa", process=ScalpMesh):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        head_mask = {"prefix": "head"}
        head_mesh = {
            "seg_directory": "segmentation/mesh",
            "suffix": "head",
            "prefix": None,
            "extension": "gii",
        }
        _meta_links = {"histo_analysis": {"*": []}}

    class ScalpMeshBBIDS(
        ScalpMeshBrainVISA, schema="morphologist_bids", process=ScalpMesh
    ):
        pass

    class SplitBrainBrainVISA(ProcessSchema, schema="brainvisa", process=SplitBrain):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        split_brain = {
            "prefix": "voronoi",
            "analysis": lambda **kwargs: f'{kwargs["initial_meta"].analysis}',
        }
        _meta_links = {"histo_analysis": {"*": []}}

    class SplitBrainBIDS(
        SplitBrainBrainVISA, schema="morphologist_bids", process=SplitBrain
    ):
        pass

    class GreyWhiteClassificationHemiBrainVISA(
        ProcessSchema, schema="brainvisa", process=GreyWhiteClassificationHemi
    ):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        grey_white = {"prefix": "grey_white"}
        _meta_links = {"histo_analysis": {"*": []}}

    class GreyWhiteClassificationHemiBIDS(
        GreyWhiteClassificationHemiBrainVISA,
        schema="morphologist_bids",
        process=GreyWhiteClassificationHemi,
    ):
        pass

    class GreyWhiteTopologyBrainVISA(
        ProcessSchema, schema="brainvisa", process=GreyWhiteTopology
    ):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        hemi_cortex = {"prefix": "cortex"}
        _meta_links = {"histo_analysis": {"*": []}}

    class GreyWhiteTopologyBIDS(
        GreyWhiteTopologyBrainVISA,
        schema="morphologist_bids",
        process=GreyWhiteTopology,
    ):
        pass

    class GreyWhiteMeshBrainVISA(
        ProcessSchema, schema="brainvisa", process=GreyWhiteMesh
    ):
        _ = {
            "*": {"seg_directory": "segmentation/mesh"},
        }
        white_mesh = {
            "side": None,
            "prefix": None,
            "suffix": "white",
            "extension": "gii",
        }

    class GreyWhiteMeshBIDS(
        GreyWhiteMeshBrainVISA, schema="morphologist_bids", process=GreyWhiteMesh
    ):
        pass

    class PialMeshBrainVISA(ProcessSchema, schema="brainvisa", process=PialMesh):
        _ = {
            "*": {"seg_directory": "segmentation/mesh"},
        }
        pial_mesh = {"side": None, "prefix": None, "suffix": "hemi", "extension": "gii"}

    class PialMeshBIDS(PialMeshBrainVISA, schema="morphologist_bids", process=PialMesh):
        pass

    class SulciSkeletonBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciSkeleton
    ):
        _ = {
            "*": {"seg_directory": "segmentation"},
        }
        skeleton = {"prefix": "skeleton"}
        roots = {"prefix": "roots"}

    class SulciSkeletonBIDS(
        SulciSkeletonBrainVISA, schema="morphologist_bids", process=SulciSkeleton
    ):
        pass

    class SulciGraphBrainVISA(ProcessSchema, schema="brainvisa", process=SulciGraph):
        _ = {
            "*": {"seg_directory": "folds", "sidebis": None},
        }
        graph = {
            "extension": "arg",
            "sulci_graph_version": lambda **kwargs: f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
        }
        sulci_voronoi = {
            "prefix": "sulcivoronoi",
            "sulci_graph_version": lambda **kwargs: f'{kwargs["process"].CorticalFoldsGraph_graph_version}',
        }
        cortex_mid_interface = {
            "seg_directory": "segmentation",
            "prefix": "gw_interface",
        }
        _meta_links = {
            "*_mesh": {"*": []},
        }

    class SulciGraphBIDS(
        SulciGraphBrainVISA, schema="morphologist_bids", process=SulciGraph
    ):
        pass

    class SulciLabellingANNBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciLabellingANN
    ):
        _ = {
            "*": {"seg_directory": "folds"},
        }
        output_graph = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "arg",
        }
        energy_plot_file = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "nrj",
        }

    class SulciLabellingANNBIDS(
        SulciLabellingANNBrainVISA,
        schema="morphologist_bids",
        process=SulciLabellingANN,
    ):
        pass

    class SulciLabellingANNShared(
        ProcessSchema, schema="brainvisa_shared", process=SulciLabellingANN
    ):
        _ = {
            "*": {
                "model_version": "08",
            }
        }

    class SulciLabellingSPAMGlobalBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciLabellingSPAMGlobal
    ):
        _ = {
            "*": {"seg_directory": "folds"},
        }
        output_graph = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "arg",
        }
        posterior_probabilities = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_proba',
            "extension": "csv",
        }
        output_transformation = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_Tal_TO_SPAM',
            "extension": "trm",
        }
        output_t1_to_global_transformation = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_T1_TO_SPAM',
            "extension": "trm",
        }

    class SulciLabellingSPAMGlobalBIDS(
        SulciLabellingSPAMGlobalBrainVISA,
        schema="morphologist_bids",
        process=SulciLabellingSPAMGlobal,
    ):
        pass

    class SulciLabellingSPAMLocalBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciLabellingSPAMLocal
    ):
        _ = {
            "*": {"seg_directory": "folds"},
        }
        output_graph = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "arg",
        }
        posterior_probabilities = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_proba',
            "extension": "csv",
        }
        output_local_transformations = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_global_TO_local',
            "extension": None,
        }

    class SulciLabellingSPAMLocalBIDS(
        SulciLabellingSPAMLocalBrainVISA,
        schema="morphologist_bids",
        process=SulciLabellingSPAMLocal,
    ):
        pass

    class SulciLabellingSPAMMarkovBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciLabellingSPAMMarkov
    ):
        _ = {
            "*": {"seg_directory": "folds"},
        }
        output_graph = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "arg",
        }
        posterior_probabilities = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}_proba',
            "extension": "csv",
        }

    class SulciLabellingSPAMMarkovBIDS(
        SulciLabellingSPAMMarkovBrainVISA,
        schema="morphologist_bids",
        process=SulciLabellingSPAMMarkov,
    ):
        pass

    class SulciDeepLabelingBrainVISA(
        ProcessSchema, schema="brainvisa", process=SulciDeepLabeling
    ):
        _ = {"*": {"seg_directory": "folds"}}

        metadata_per_parameter = {
            "*": {
                "unused": [
                    "subject_only",
                    "sulci_recognition_session",
                    "sulci_graph_version",
                ]
            },
            "graph": {"unused": ["subject_only", "sulci_recognition_session"]},
            "roots": {
                "unused": [
                    "subject_only",
                    "sulci_recognition_session",
                    "sulci_graph_version",
                ]
            },
            "skeleton": {
                "unused": [
                    "subject_only",
                    "sulci_recognition_session",
                    "sulci_graph_version",
                ]
            },
            "labeled_graph": {"unused": ["subject_only"]},
        }

        graph = {"extension": "arg"}
        roots = {
            "seg_directory": "segmentation",
            "prefix": "roots",
            "extension": "nii.gz",
        }
        skeleton = {
            "seg_directory": "segmentation",
            "prefix": "skeleton",
            "extension": "nii.gz",
        }
        labeled_graph = {
            "suffix": lambda **kwargs: f'{kwargs["metadata"].sulci_recognition_session}'
            f'_{kwargs["metadata"].sulci_recognition_type}',
            "extension": "arg",
        }

    class SulciDeepLabelingBIDS(
        SulciDeepLabelingBrainVISA,
        schema="morphologist_bids",
        process=SulciDeepLabeling,
    ):
        pass

    class SulciDeepLabelingShared(
        ProcessSchema, schema="brainvisa_shared", process=SulciDeepLabeling
    ):
        model_file = {"data_id": "sulci_cnn_recognition_model", "model_version": "19"}
        param_file = {"data_id": "sulci_cnn_recognition_param", "model_version": "19"}

    class sulcigraphmorphometrybysubjectBrainVISA(
        ProcessSchema, schema="brainvisa", process=sulcigraphmorphometrybysubject
    ):
        sulcal_morpho_measures = {
            "extension": "csv",
            "side": None,
            "_": Append("suffix", "sulcal_morphometry"),
        }

    class sulcigraphmorphometrybysubjectBIDS(
        sulcigraphmorphometrybysubjectBrainVISA,
        schema="morphologist_bids",
        process=sulcigraphmorphometrybysubject,
    ):
        pass

    class BrainVolumesBrainVISA(
        ProcessSchema, schema="brainvisa", process=brainvolumes
    ):
        _ = {"*": {"seg_directory": "segmentation"}}
        metadata_per_parameter = {
            "*": {
                "unused": [
                    "subject_only",
                    "sulci_graph_version",
                    "sulci_recognition_session",
                ]
            },
            "*_labelled_graph": {"unused": ["subject_only"]},
            "subject": {"used": ["subject_only", "subject"]},
        }
        left_csf = {
            "prefix": "csf",
            "side": "L",
            "sidebis": None,
            "suffix": None,
            "extension": "nii.gz",  # should not be hard-coded but I failed
        }
        right_csf = {
            "prefix": "csf",
            "side": "R",
            "sidebis": None,
            "suffix": None,
            "extension": "nii.gz",  # should not be hard-coded but I failed
        }
        brain_volumes_file = {
            "prefix": "brain_volumes",
            "suffix": None,
            "side": None,
            "sidebis": None,
            "extension": "csv",
        }
        subject = {
            "seg_directory": None,
            "prefix": None,
            "side": None,
            "subject_in_filename": False,
        }
        _meta_links = {
            "*_labelled_graph": {"*": []},
            "*_grey_white": {"*": []},
            "*_mesh": {"*": []},
            "left_grey_white": {"left_csf": ["extension"]},  # no effect ..?
            "right_grey_white": {"right_csf": ["extension"]},  # no effect ..?
        }

    class BrainVolumesBIDS(
        BrainVolumesBrainVISA, schema="morphologist_bids", process=brainvolumes
    ):
        pass

    class MorphoReportBrainVISA(
        ProcessSchema, schema="brainvisa", process=morpho_report
    ):
        _ = {"*": {"seg_directory": None}}
        metadata_per_parameter = {
            "*": {
                "unused": [
                    "subject_only",
                    "sulci_graph_version",
                    "sulci_recognition_session",
                ]
            },
            "*_labelled_graph": {"unused": ["subject_only"]},
            "subject": {"used": ["subject_only", "subject"]},
        }
        report = {
            "prefix": None,
            "side": None,
            "sidebis": None,
            "subject_in_filename": False,
            "suffix": "morphologist_report",
            "extension": "pdf",
        }
        subject = {
            "prefix": None,
            "side": None,
            "subject_in_filename": False,
        }

    class MorphoReportBIDS(
        MorphoReportBrainVISA, schema="morphologist_bids", process=morpho_report
    ):
        pass

    class MorphologistShared(
        ProcessSchema, schema="brainvisa_shared", process=Morphologist
    ):
        PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template = {
            "data_id": "normalization_template"
        }
        PrepareSubject_Normalization_NormalizeFSL_template = {
            "data_id": "normalization_template"
        }
        PrepareSubject_Normalization_NormalizeSPM_template = {
            "data_id": "normalization_template"
        }
        PrepareSubject_Normalization_NormalizeBaladin_template = {
            "data_id": "normalization_template"
        }
        PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {
            "data_id": "trans_acpc_to_mni"
        }
        PrepareSubject_TalairachFromNormalization_acpc_referential = {
            "data_id": "acpc_ref"
        }
        Renorm_template = {"data_id": "normalization_template_brain"}
        Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc = {
            "data_id": "trans_mni_to_acpc"
        }
        PrepareSubject_TalairachFromNormalization_normalized_referential = {
            "data_id": "icbm152_ref"
        }
        PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized = {
            "data_id": "trans_acpc_to_mni"
        }
        SplitBrain_split_template = {"data_id": "hemi_split_template"}
        sulcal_morphometry_sulci_file = {"data_id": "sulcal_morphometry_sulci_file"}
        SulciRecognition_recognition2000_model = {
            "data_id": "sulci_ann_recognition_model",
            "side": "L",
            "graph_version": "3.1",
        }
        SulciRecognition_1_recognition2000_model = {
            "data_id": "sulci_ann_recognition_model",
            "side": "R",
            "graph_version": "3.1",
        }
        SPAM_recognition_labels_translation_map = {
            "data_id": "sulci_spam_recognition_labels_trans",
            "model_version": "08",
        }
        SulciRecognition_SPAM_recognition09_global_recognition_model = {
            "data_id": "sulci_spam_recognition_global_model",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_global_recognition_model = {
            "data_id": "sulci_spam_recognition_global_model",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_local_recognition_model = {
            "data_id": "sulci_spam_recognition_local_model",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_local_recognition_model = {
            "data_id": "sulci_spam_recognition_local_model",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_markovian_recognition_model = {
            "data_id": "sulci_spam_recognition_global_model",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_markovian_recognition_model = {
            "data_id": "sulci_spam_recognition_global_model",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_global_recognition_labels_priors = {
            "data_id": "sulci_spam_recognition_global_labels_priors",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors = {
            "data_id": "sulci_spam_recognition_global_labels_priors",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_local_recognition_local_referentials = {
            "data_id": "sulci_spam_recognition_local_refs",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials = {
            "data_id": "sulci_spam_recognition_local_refs",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_local_recognition_direction_priors = {
            "data_id": "sulci_spam_recognition_local_dir_priors",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors = {
            "data_id": "sulci_spam_recognition_local_dir_priors",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_SPAM_recognition09_local_recognition_angle_priors = {
            "data_id": "sulci_spam_recognition_local_angle_priors",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors = {
            "data_id": "sulci_spam_recognition_local_angle_priors",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_local_recognition_translation_priors = {
            "data_id": "sulci_spam_recognition_local_trans_priors",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors = {
            "data_id": "sulci_spam_recognition_local_trans_priors",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model = {
            "data_id": "sulci_spam_recognition_markov_rels",
            "model_version": "08",
            "side": "L",
        }
        SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model = {
            "data_id": "sulci_spam_recognition_markov_rels",
            "model_version": "08",
            "side": "R",
        }
        SulciRecognition_CNN_recognition19_model_file = {
            "data_id": "sulci_cnn_recognition_model",
            "model_version": "19",
            "side": "L",
        }
        SulciRecognition_1_CNN_recognition19_model_file = {
            "data_id": "sulci_cnn_recognition_model",
            "model_version": "19",
            "side": "R",
        }
        SulciRecognition_CNN_recognition19_param_file = {
            "data_id": "sulci_cnn_recognition_param",
            "model_version": "19",
            "side": "L",
        }
        SulciRecognition_1_CNN_recognition19_param_file = {
            "data_id": "sulci_cnn_recognition_param",
            "model_version": "19",
            "side": "R",
        }
