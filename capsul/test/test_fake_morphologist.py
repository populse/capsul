import json
import os.path as osp
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from soma.controller import undefined

from capsul.api import Capsul
from capsul.config.configuration import (
    default_builtin_database,
    default_engine_start_workers,
)
from capsul.dataset import BrainVISASchema, ProcessMetadata, process_schema
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm8_reinit import (
    normalization_t1_spm8_reinit,
)

# patch processes to setup their requirements
from capsul.pipeline.test.fake_morphologist.normalization_t1_spm12_reinit import (
    normalization_t1_spm12_reinit,
)
from capsul.schemas.brainvisa import declare_morpho_schemas

normalization_t1_spm12_reinit.requirements = {"spm": {"version": "12"}}

normalization_t1_spm8_reinit.requirements = {"spm": {"version": "8"}}

declare_morpho_schemas("capsul.pipeline.test.fake_morphologist")


def get_shared_path():
    try:
        from soma import aims

        return aims.carto.Paths.resourceSearchPath()[-1]
    except Exception:
        return "!{dataset.shared.path}"


class TestFakeMorphologist(unittest.TestCase):
    subjects = (
        "aleksander",
        "casimiro",
        # 'christophorus',
        # 'christy',
        # 'conchobhar',
        # 'cornelia',
        # 'dakila',
        # 'demosthenes',
        # 'devin',
        # 'ferit',
        # 'gautam',
        # 'hikmat',
        # 'isbel',
        # 'ivona',
        # 'jordana',
        # 'justyn',
        # 'katrina',
        # 'lyda',
        # 'melite',
        # 'til',
        # 'vanessza',
        # 'victoria'
    )

    def setUp(self):
        self.tmp = tmp = Path(tempfile.mkdtemp(prefix="capsul_test_fakem"))
        # -------------------#
        # Environment setup #
        # -------------------#

        # Create BIDS directory
        self.bids = bids = tmp / "bids"
        # Write Capsul specific information
        bids.mkdir()
        with (bids / "capsul.json").open("w") as f:
            json.dump({"metadata_schema": "bids"}, f)

        # Create BrainVISA directory
        self.brainvisa = brainvisa = tmp / "brainvisa"
        brainvisa.mkdir()
        # Write Capsul specific information
        with (brainvisa / "capsul.json").open("w") as f:
            json.dump({"metadata_schema": "brainvisa"}, f)

        # Generate fake T1 and T2 data in bids directory
        for subject in self.subjects:
            for session in ("m0", "m12", "m24"):
                for data_type in ("T1w", "T2w"):
                    subject_dir = bids / "rawdata" / f"sub-{subject}"
                    session_dir = subject_dir / f"ses-{session}"
                    file = (
                        session_dir
                        / "anat"
                        / f"sub-{subject}_ses-{session}_{data_type}.nii.gz"
                    )
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file_name = str(file.name)
                    with file.open("w") as f:
                        print(
                            f"{data_type} acquisition for subject {subject} acquired in session {session}",
                            file=f,
                        )

                    sessions_file = subject_dir / f"sub-{subject}_sessions.tsv"
                    if not sessions_file.exists():
                        with open(sessions_file, "w") as f:
                            f.write("session_id\tsession_metadata\n")
                    with open(sessions_file, "a") as f:
                        f.write(f"ses-{session}\tsession metadata for {file_name}\n")

                    scans_file = session_dir / f"sub-{subject}_ses-{session}_scans.tsv"
                    if not scans_file.exists():
                        with open(scans_file, "w") as f:
                            f.write("filename\tscan_metadata\n")
                    with open(scans_file, "a") as f:
                        f.write(
                            f"{file.relative_to(session_dir)}\tscan metadata for {file_name}\n"
                        )

                    if file.suffix == ".gz":
                        json_file = Path(str(file)[:-3]).with_suffix(".json")
                    else:
                        json_file = file.with_suffix(".json")
                    with json_file.open("w") as f:
                        json.dump(
                            dict(json_metadata=f"JSON metadata for {file_name}"), f
                        )

        # Configuration base dictionary
        config = {
            "builtin": {
                #'config_modules': [
                #'spm',
                # ],
                "dataset": {
                    "input": {
                        "path": str(self.bids),
                        "metadata_schema": "bids",
                    },
                    "output": {
                        "path": str(self.brainvisa),
                        "metadata_schema": "brainvisa",
                    },
                    "shared": {
                        "path": get_shared_path(),
                        "metadata_schema": "brainvisa_shared",
                    },
                }
            }
        }
        # Create fake SPM directories
        for version in ("8", "12"):
            fakespm = tmp / "software" / f"fakespm-{version}"
            fakespm.mkdir(parents=True, exist_ok=True)
            # Write a file containing only the version string that will be used
            # by fakespm module to check installation.
            (fakespm / "fakespm").write_text(version)
            # Write a fake template file
            (fakespm / "template").write_text(f"template of fakespm {version}")
            fakespm_config = {
                "directory": str(fakespm),
                "version": version,
                "standalone": True,
            }
            config["builtin"].setdefault("spm", {})[f"spm_{version}_standalone"] = (
                fakespm_config
            )

        matlab_config = {
            "mcr_directory": str(tmp / "software" / "matlab"),
        }
        config["builtin"].setdefault("matlab", {})["matlab"] = matlab_config

        # Create a configuration file
        self.config_file = tmp / "capsul_config.json"
        with self.config_file.open("w") as f:
            json.dump(config, f)

        self.capsul = Capsul(
            "test_fake_morphologist",
            site_file=self.config_file,
            user_file=None,
            database_path=osp.join(self.tmp, "capsul_engine_database.sqlite"),
        )
        return super().setUp()

    def tearDown(self):
        # print('tmp dir:', self.tmp)
        # input('continue ?')
        self.capsul = None
        shutil.rmtree(self.tmp)
        return super().tearDown()

    def test_fake_morphologist_config(self):
        self.maxDiff = 2000
        expected_config = {
            "databases": {
                "builtin": {
                    "path": osp.join(self.tmp, "capsul_engine_database.sqlite"),
                    "type": default_builtin_database["type"],
                }
            },
            "builtin": {
                "config_modules": ["spm", "matlab"],
                "database": "builtin",
                "start_workers": default_engine_start_workers,
                "dataset": {
                    "input": {
                        "path": str(self.tmp / "bids"),
                        "metadata_schema": "bids",
                    },
                    "output": {
                        "path": str(self.tmp / "brainvisa"),
                        "metadata_schema": "brainvisa",
                    },
                    "shared": {
                        "path": get_shared_path(),
                        "metadata_schema": "brainvisa_shared",
                    },
                },
                "persistent": True,
                "spm": {
                    "spm_12_standalone": {
                        "directory": str(self.tmp / "software" / "fakespm-12"),
                        "version": "12",
                        "standalone": True,
                    },
                    "spm_8_standalone": {
                        "directory": str(self.tmp / "software" / "fakespm-8"),
                        "version": "8",
                        "standalone": True,
                    },
                },
                "matlab": {
                    "matlab": {
                        "mcr_directory": str(self.tmp / "software" / "matlab"),
                    },
                },
                #'config_modules': ['capsul.test.test_fake_morphologist'],
            },
        }
        # print("\nconfig:", self.capsul.config.asdict(), "\n")
        self.assertEqual(self.capsul.config.asdict(), expected_config)

        engine = self.capsul.engine()
        morphologist = self.capsul.executable(
            "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist"
        )

        morphologist.select_Talairach = "StandardACPC"
        morphologist.perform_skull_stripped_renormalization = "initial"

        context = engine.execution_context(morphologist)
        expected_context = {
            #'config_modules': ['capsul.test.test_fake_morphologist'],
            "config_modules": ["spm", "matlab"],
            "python_modules": [],
            "dataset": {
                "input": {
                    "path": str(self.tmp / "bids"),
                    "metadata_schema": "bids",
                },
                "output": {
                    "path": str(self.tmp / "brainvisa"),
                    "metadata_schema": "brainvisa",
                },
                "shared": {
                    "path": get_shared_path(),
                    "metadata_schema": "brainvisa_shared",
                },
            },
        }
        dict_context = context.asdict()
        ds_context = {"dataset": dict_context["dataset"]}
        # print('requirements:')
        # print(context.executable_requirements(morphologist))
        self.assertEqual(dict_context, expected_context)
        # spms = list(expected_config['builtin']['spm'].values())
        # self.assertTrue(dict_context['spm'] in spms)

        morphologist.select_Talairach = "Normalization"
        morphologist.perform_skull_stripped_renormalization = "skull_stripped"
        morphologist.Normalization_select_Normalization_pipeline = "NormalizeSPM"
        morphologist.spm_normalization_version = "normalization_t1_spm12_reinit"

        context = engine.execution_context(morphologist)
        # print('context:')
        # print(dict_context)
        # print('requirements:')
        # print(context.executable_requirements(morphologist))
        fakespm12_conf = {
            "directory": str(self.tmp / "software" / "fakespm-12"),
            "version": "12",
            "standalone": True,
        }
        matlab_conf = {
            "mcr_directory": str(self.tmp / "software" / "matlab"),
        }
        expected_context["spm"] = fakespm12_conf
        expected_context["matlab"] = matlab_conf
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

        morphologist_iteration = self.capsul.executable_iteration(
            "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist",
            # non_iterative_plugs=['template'],
        )

        context = engine.execution_context(morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)
        morphologist_iteration.select_Talairach = [
            "StandardACPC",
            "Normalization",
            "Normalization",
        ]
        morphologist_iteration.perform_skull_stripped_renormalization = [
            "initial",
            "skull_stripped",
            "skull_stripped",
        ]

        morphologist_iteration.Normalization_select_Normalization_pipeline = [
            "NormalizeSPM",
            "Normalization_AimsMIRegister",
            "NormalizeSPM",
        ]
        expected_context["spm"] = fakespm12_conf
        expected_context["matlab"] = matlab_conf
        context = engine.execution_context(morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

    def clear_values(self, morphologist):
        for field in morphologist.user_fields():  # noqa: F402
            if field.path_type:
                value = getattr(morphologist, field.name, undefined)
                if value in (None, undefined):
                    continue
                if isinstance(value, list):
                    setattr(morphologist, field.name, [])
                else:
                    setattr(morphologist, field.name, undefined)

    def test_path_generation(self):
        expected = {
            (
                "StandardACPC",
                "initial",
                "NormalizeSPM",
                "normalization_t1_spm12_reinit",
            ): {
                "imported_t1mri": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/aleksander.nii.gz",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template": "!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz",
                "t1mri_nobias": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii.gz",
                "Talairach_transform": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm",
                "left_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "right_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
            },
            (
                "Normalization",
                "skull_stripped",
                "Normalization_AimsMIRegister",
                "normalization_t1_spm12_reinit",
            ): {
                "imported_t1mri": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/aleksander.nii.gz",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template": "!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz",
                "t1mri_nobias": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii.gz",
                "Talairach_transform": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm",
                "left_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "right_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
            },
            (
                "Normalization",
                "skull_stripped",
                "NormalizeSPM",
                "normalization_t1_spm12_reinit",
            ): {
                "imported_t1mri": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/aleksander.nii.gz",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template": "!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz",
                "t1mri_nobias": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii.gz",
                "Talairach_transform": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm",
                "left_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "right_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
            },
            (
                "Normalization",
                "skull_stripped",
                "NormalizeSPM",
                "normalization_t1_spm8_reinit",
            ): {
                "imported_t1mri": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/aleksander.nii.gz",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template": "!{dataset.shared.path}/anatomical_templates/MNI152_T1_2mm.nii.gz",
                "t1mri_nobias": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/nobias_aleksander.nii.gz",
                "Talairach_transform": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/registration/RawT1-aleksander_m0_TO_Talairach-ACPC.trm",
                "left_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "right_labelled_graph": "!{dataset.output.path}/whatever/aleksander/t1mri/m0/default_analysis/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
            },
        }
        engine = self.capsul.engine()
        sel_tal = ["StandardACPC", "Normalization", "Normalization", "Normalization"]
        renorm = ["initial", "skull_stripped", "skull_stripped", "skull_stripped"]
        norm = [
            "NormalizeSPM",
            "Normalization_AimsMIRegister",
            "NormalizeSPM",
            "NormalizeSPM",
        ]
        normspm = [
            "normalization_t1_spm12_reinit",
            "normalization_t1_spm12_reinit",
            "normalization_t1_spm12_reinit",
            "normalization_t1_spm8_reinit",
        ]

        morphologist = self.capsul.executable(
            "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist"
        )
        self.clear_values(morphologist)

        execution_context = engine.execution_context(morphologist)

        input = str(
            self.tmp
            / "bids"
            / "rawdata"
            / "sub-aleksander"
            / "ses-m0"
            / "anat"
            / "sub-aleksander_ses-m0_T1w.nii.gz"
        )
        input_metadata = execution_context.dataset["input"].schema.metadata(input)
        self.assertEqual(
            input_metadata,
            {
                "folder": "rawdata",
                "sub": "aleksander",
                "ses": "m0",
                "data_type": "anat",
                "suffix": "T1w",
                "extension": "nii.gz",
                "session_metadata": "session metadata for sub-aleksander_ses-m0_T2w.nii.gz",
                "scan_metadata": "scan metadata for sub-aleksander_ses-m0_T1w.nii.gz",
                "json_metadata": "JSON metadata for sub-aleksander_ses-m0_T1w.nii.gz",
            },
        )

        expected_params_per_schema = {
            "brainvisa": [
                "imported_t1mri",
                "commissure_coordinates",
                "Talairach_transform",
                "t1mri_nobias",
                "histo_analysis",
                "BrainSegmentation_brain_mask",
                "split_brain",
                "HeadMesh_head_mesh",
                "GreyWhiteClassification_grey_white",
                "GreyWhiteClassification_1_grey_white",
                "GreyWhiteTopology_hemi_cortex",
                "GreyWhiteTopology_1_hemi_cortex",
                "GreyWhiteMesh_white_mesh",
                "GreyWhiteMesh_1_white_mesh",
                "SulciSkeleton_skeleton",
                "SulciSkeleton_1_skeleton",
                "PialMesh_pial_mesh",
                "PialMesh_1_pial_mesh",
                "left_graph",
                "right_graph",
                "left_labelled_graph",
                "right_labelled_graph",
                "sulcal_morpho_measures",
                "t1mri_referential",
                "reoriented_t1mri",
                "normalization_fsl_native_transformation_pass1",
                "normalization_fsl_native_transformation",
                "normalization_baladin_native_transformation_pass1",
                "normalization_baladin_native_transformation",
                "normalized_t1mri",
                "MNI_transform",
                "normalization_spm_native_transformation",
                "normalization_spm_native_transformation_pass1",
                "BiasCorrection_b_field",
                "BiasCorrection_hfiltered",
                "BiasCorrection_white_ridges",
                "BiasCorrection_variance",
                "BiasCorrection_edges",
                "BiasCorrection_meancurvature",
                "HistoAnalysis_histo",
                "Renorm_skull_stripped",
                "HeadMesh_head_mask",
                "SulciSkeleton_roots",
                "CorticalFoldsGraph_sulci_voronoi",
                "CorticalFoldsGraph_cortex_mid_interface",
                "SulciRecognition_recognition2000_energy_plot_file",
                "SulciRecognition_SPAM_recognition09_global_recognition_posterior_probabilities",
                "SulciRecognition_SPAM_recognition09_global_recognition_output_transformation",
                "SulciRecognition_SPAM_recognition09_global_recognition_output_t1_to_global_transformation",
                "SulciRecognition_SPAM_recognition09_local_recognition_posterior_probabilities",
                "SulciRecognition_SPAM_recognition09_local_recognition_output_local_transformations",
                "SulciRecognition_SPAM_recognition09_markovian_recognition_posterior_probabilities",
                "SulciSkeleton_1_roots",
                "CorticalFoldsGraph_1_sulci_voronoi",
                "CorticalFoldsGraph_1_cortex_mid_interface",
                "SulciRecognition_1_recognition2000_energy_plot_file",
                "SulciRecognition_1_SPAM_recognition09_global_recognition_posterior_probabilities",
                "SulciRecognition_1_SPAM_recognition09_global_recognition_output_transformation",
                "SulciRecognition_1_SPAM_recognition09_global_recognition_output_t1_to_global_transformation",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_posterior_probabilities",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_output_local_transformations",
                "SulciRecognition_1_SPAM_recognition09_markovian_recognition_posterior_probabilities",
                "GlobalMorphometry_brain_volumes_file",
                "GlobalMorphometry_left_csf",
                "GlobalMorphometry_right_csf",
                "subject",
                "Report_report",
            ],
            "bids": [
                "t1mri",
            ],
            "brainvisa_shared": [
                "PrepareSubject_TalairachFromNormalization_normalized_referential",
                "PrepareSubject_TalairachFromNormalization_acpc_referential",
                "PrepareSubject_TalairachFromNormalization_transform_chain_ACPC_to_Normalized",
                "SPAM_recognition_labels_translation_map",
                "sulcal_morphometry_sulci_file",
                "PrepareSubject_Normalization_NormalizeFSL_template",
                "PrepareSubject_Normalization_NormalizeSPM_template",
                "PrepareSubject_Normalization_NormalizeBaladin_template",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template",
                "PrepareSubject_Normalization_Normalization_AimsMIRegister_mni_to_acpc",
                "Renorm_template",
                "Renorm_Normalization_Normalization_AimsMIRegister_mni_to_acpc",
                "SplitBrain_split_template",
                "SulciRecognition_recognition2000_model",
                "SulciRecognition_SPAM_recognition09_global_recognition_labels_priors",
                "SulciRecognition_SPAM_recognition09_global_recognition_model",
                "SulciRecognition_SPAM_recognition09_local_recognition_model",
                "SulciRecognition_SPAM_recognition09_local_recognition_local_referentials",
                "SulciRecognition_SPAM_recognition09_local_recognition_direction_priors",
                "SulciRecognition_SPAM_recognition09_local_recognition_angle_priors",
                "SulciRecognition_SPAM_recognition09_local_recognition_translation_priors",
                "SulciRecognition_SPAM_recognition09_markovian_recognition_model",
                "SulciRecognition_SPAM_recognition09_markovian_recognition_segments_relations_model",
                "SulciRecognition_CNN_recognition19_model_file",
                "SulciRecognition_CNN_recognition19_param_file",
                "SulciRecognition_1_recognition2000_model",
                "SulciRecognition_1_SPAM_recognition09_global_recognition_labels_priors",
                "SulciRecognition_1_SPAM_recognition09_global_recognition_model",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_model",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_local_referentials",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_direction_priors",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_angle_priors",
                "SulciRecognition_1_SPAM_recognition09_local_recognition_translation_priors",
                "SulciRecognition_1_SPAM_recognition09_markovian_recognition_model",
                "SulciRecognition_1_SPAM_recognition09_markovian_recognition_segments_relations_model",
                "SulciRecognition_1_CNN_recognition19_model_file",
                "SulciRecognition_1_CNN_recognition19_param_file",
            ],
        }

        # iterate manually
        count = -1
        for it, normalization in enumerate(zip(sel_tal, renorm, norm, normspm)):
            count += 1
            # morphologist.t1mri = str(self.tmp / 'bids'/'rawdata'/'sub-aleksander'/'ses-m0'/'anat'/'sub-aleksander_ses-m0_T1w.nii.gz')
            morphologist.select_Talairach = normalization[0]
            morphologist.perform_skull_stripped_renormalization = normalization[1]
            morphologist.Normalization_select_Normalization_pipeline = normalization[2]
            morphologist.spm_normalization_version = normalization[3]
            morphologist.select_sulci_recognition = (
                "CNN_recognition19"  # 'SPAM_recognition09'
            )

            metadata = ProcessMetadata(morphologist, execution_context)

            expected_sch = expected_params_per_schema
            expected_sch["brainvisa"] = sorted(expected_sch["brainvisa"])

            got_sch = dict(metadata.parameters_per_schema)
            got_sch["brainvisa"] = sorted(got_sch["brainvisa"])

            self.maxDiff = None
            self.assertEqual(got_sch, expected_sch)

            metadata.bids = input_metadata
            metadata.brainvisa = {"center": "whatever"}
            self.assertEqual(
                metadata.bids.asdict(),
                {
                    "folder": "rawdata",
                    "process": None,
                    "sub": "aleksander",
                    "ses": "m0",
                    "data_type": "anat",
                    "task": None,
                    "acq": None,
                    "ce": None,
                    "rec": None,
                    "run": None,
                    "echo": None,
                    "part": None,
                    "suffix": "T1w",
                    "extension": "nii.gz",
                },
            )

            t0 = time.time()
            metadata.generate_paths(morphologist)
            t1 = time.time()
            print("completion time:", t1 - t0, "s")

            debug = False
            if debug:
                from soma.qt_gui.qt_backend import Qt

                from capsul.qt_gui.widgets.pipeline_developer_view import (
                    PipelineDeveloperView,
                )

                app = Qt.QApplication.instance()
                if app is None:
                    app = Qt.QApplication([])
                pv = PipelineDeveloperView(
                    morphologist,
                    allow_open_controller=True,
                    enable_edition=True,
                    show_sub_pipelines=True,
                )
                pv.show()
                app.exec_()

            params = dict(
                (i, getattr(morphologist, i, undefined))
                for i in (
                    "PrepareSubject_Normalization_Normalization_AimsMIRegister_anatomical_template",
                    "imported_t1mri",
                    "t1mri_nobias",
                    "Talairach_transform",
                    "left_labelled_graph",
                    "right_labelled_graph",
                )
            )
            self.maxDiff = None
            self.assertEqual(params, expected[normalization])
            # for field in morphologist.fields():
            #     value = getattr(morphologist, field.name, undefined)
            #     print(f'!{normalization}!', field.name, value)

            # run it
            # with self.capsul.engine() as engine:
            # status = engine.run(morphologist)
            # print('run status:', status)
            # self.assertEqual(
            # status,
            # {'status': 'ended', 'error': None, 'error_detail': None,
            #'engine_output': ''})

    def test_fake_morphologist_iteration(self):
        expected_completion = {
            "t1mri": [
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
            ],
            "left_labelled_graph": [
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
            ],
            "t1mri_nobias": [
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
            ],
            "Normalization_select_Normalization_pipeline": [
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
            ],
            "right_labelled_graph": [
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
            ],
            "Report_report": [
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                "!{dataset.output.path}/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/morphologist_report.pdf",
            ],
        }

        expected_resolution = {
            "t1mri": [
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii.gz",
            ],
            "left_labelled_graph": [
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Laleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Lcasimiro_default_session_auto.arg",
            ],
            "t1mri_nobias": [
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/nobias_aleksander.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/nobias_casimiro.nii.gz",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/nobias_casimiro.nii.gz",
            ],
            "Normalization_select_Normalization_pipeline": [
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
            ],
            "right_labelled_graph": [
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Raleksander_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/folds/3.1/default_session_auto/Rcasimiro_default_session_auto.arg",
            ],
            "Report_report": [
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m0/Normalization-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m12/Normalization-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/aleksander/t1mri/m24/Normalization-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m0/Normalization-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m12/Normalization-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/StandardACPC-NormalizeSPM/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-Normalization_AimsMIRegister/morphologist_report.pdf",
                f"{self.tmp}/brainvisa/whatever/casimiro/t1mri/m24/Normalization-NormalizeSPM/morphologist_report.pdf",
            ],
        }

        morphologist_iteration = self.capsul.executable_iteration(
            "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist",
            non_iterative_plugs=["template"],
        )

        self.clear_values(morphologist_iteration)
        self.clear_values(morphologist_iteration.process)

        @process_schema("brainvisa", morphologist_iteration)
        def brainvisa_morphologist_iteration(metadata):
            metadata["*"].suffix = metadata.executable.normalization

        engine = self.capsul.engine()
        execution_context = engine.execution_context(morphologist_iteration)

        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        count = 0
        iter_meta_bids = []
        iter_meta_brainvisa = []
        select_Talairach = []
        perform_skull_stripped_renormalization = []
        Normalization_select_Normalization_pipeline = []
        spm_normalization_version = []

        for path in sorted(
            self.capsul.config.builtin.dataset.input.find(
                suffix="T1w", extension="nii.gz"
            )
        ):
            input_metadata = execution_context.dataset["input"].schema.metadata(path)
            iter_meta_bids.extend([input_metadata] * 3)
            select_Talairach += ["StandardACPC", "Normalization", "Normalization"]
            perform_skull_stripped_renormalization += [
                "initial",
                "skull_stripped",
                "skull_stripped",
            ]
            Normalization_select_Normalization_pipeline += [
                "NormalizeSPM",
                "Normalization_AimsMIRegister",
                "NormalizeSPM",
            ]
            spm_normalization_version += [
                "normalization_t1_spm12_reinit",
                "normalization_t1_spm12_reinit",
                "normalization_t1_spm8_reinit",
            ]

            for i in range(3):
                brainvisa = BrainVISASchema()
                brainvisa.analysis = f"{select_Talairach[i]}-{Normalization_select_Normalization_pipeline[i]}"
                brainvisa.center = "whatever"
                iter_meta_brainvisa.append(brainvisa)

        # Set the input data
        morphologist_iteration.select_Talairach = select_Talairach
        morphologist_iteration.perform_skull_stripped_renormalization = (
            perform_skull_stripped_renormalization
        )
        morphologist_iteration.Normalization_select_Normalization_pipeline = (
            Normalization_select_Normalization_pipeline
        )
        morphologist_iteration.spm_normalization_version = spm_normalization_version

        metadata = ProcessMetadata(morphologist_iteration, execution_context)
        metadata.bids = iter_meta_bids
        metadata.brainvisa = iter_meta_brainvisa
        p = self.capsul.executable(
            "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist"
        )
        metadata.generate_paths(morphologist_iteration)

        # debug = False
        # if debug:
        #     from soma.qt_gui.qt_backend import Qt
        #     from capsul.qt_gui.widgets.pipeline_developer_view import PipelineDeveloperView

        #     app = Qt.QApplication.instance()
        #     if app is None:
        #         app = Qt.QApplication([])
        #     pv = PipelineDeveloperView(morphologist_iteration, allow_open_controller=True, enable_edition=True, show_sub_pipelines=True)
        #     pv.show()
        #     app.exec_()

        self.maxDiff = None
        for name, value in expected_completion.items():
            # print('test parameter:', name)
            self.assertEqual(getattr(morphologist_iteration, name, undefined), value)
        morphologist_iteration.resolve_paths(execution_context)
        for name, value in expected_resolution.items():
            self.assertEqual(getattr(morphologist_iteration, name, undefined), value)

    #     try:
    #         with capsul.engine() as ce:
    #             # Finally execute all the Morphologist instances
    #             execution_id = ce.run(processing_pipeline)
    #     except Exception:
    #         import traceback
    #         traceback.print_exc()

    #     import sys
    #     sys.stdout.flush()
    #     from soma.qt_gui.qt_backend import QtGui
    #     from capsul.qt_gui.widgets import PipelineDeveloperView
    #     app = QtGui.QApplication.instance()
    #     if not app:
    #         app = QtGui.QApplication(sys.argv)
    #     view1 = PipelineDeveloperView(processing_pipeline, show_sub_pipelines=True)
    #     view1.show()
    #     app.exec_()
    #     del view1


def with_iteration(engine):
    morphologist_iteration = Capsul.executable_iteration(
        "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist",
        non_iterative_plugs=["template"],
    )

    execution_context = engine.execution_context(morphologist_iteration)

    # Parse the dataset with BIDS-specific query (here "suffix" is part
    #  of BIDS specification). The object returned contains info for main
    # BIDS fields (sub, ses, acq, etc.)
    count = 0
    iter_meta_bids = []
    select_Talairach = []
    perform_skull_stripped_renormalization = []
    Normalization_select_Normalization_pipeline = []
    spm_normalization_version = []
    analysis = []

    for path in sorted(
        self.capsul.config.builtin.dataset.input.find(suffix="T1w", extension="nii.gz")
    ):
        input_metadata = execution_context.dataset["input"].schema.metadata(path)
        iter_meta_bids.extend([input_metadata] * 3)
        select_Talairach += ["StandardACPC", "Normalization", "Normalization"]
        perform_skull_stripped_renormalization += [
            "initial",
            "skull_stripped",
            "skull_stripped",
        ]
        Normalization_select_Normalization_pipeline += [
            "NormalizeSPM",
            "Normalization_AimsMIRegister",
            "NormalizeSPM",
        ]
        spm_normalization_version += [
            "normalization_t1_spm12_reinit",
            "normalization_t1_spm12_reinit",
            "normalization_t1_spm8_reinit",
        ]
        analysis += [
            "StandardACPC-NormalizeSPM",
            "Normalization-AimsMIRegister",
            "Normalization-NormalizeSPM",
        ]
    # Set the input data
    morphologist_iteration.select_Talairach = select_Talairach
    morphologist_iteration.perform_skull_stripped_renormalization = (
        perform_skull_stripped_renormalization
    )
    morphologist_iteration.Normalization_select_Normalization_pipeline = (
        Normalization_select_Normalization_pipeline
    )
    morphologist_iteration.spm_normalization_version = spm_normalization_version

    metadata = ProcessMetadata(morphologist_iteration, execution_context)
    metadata.bids = iter_meta_bids
    metadata.brainvisa.center = "whatever"
    metadata.brainvisa.analysis = analysis
    metadata.generate_paths(morphologist_iteration)

    execution_id = engine.start(morphologist_iteration)
    return execution_id


def without_iteration(engine):
    select_Talairach = ["StandardACPC", "Normalization", "Normalization"]
    perform_skull_stripped_renormalization = [
        "initial",
        "skull_stripped",
        "skull_stripped",
    ]
    Normalization_select_Normalization_pipeline = [
        "NormalizeSPM",
        "Normalization_AimsMIRegister",
        "NormalizeSPM",
    ]
    spm_normalization_version = [
        "normalization_t1_spm12_reinit",
        "normalization_t1_spm12_reinit",
        "normalization_t1_spm8_reinit",
    ]

    execution_ids = []
    for path in sorted(
        self.capsul.config.builtin.dataset.input.find(suffix="T1w", extension="nii.gz")
    ):
        for i in range(3):
            morphologist = Capsul.executable(
                "capsul.pipeline.test.fake_morphologist.morphologist.Morphologist",
            )
            execution_context = engine.execution_context(morphologist)
            input_metadata = execution_context.dataset["input"].schema.metadata(path)

            # Set the input data
            morphologist.select_Talairach = select_Talairach[i]
            morphologist.perform_skull_stripped_renormalization = (
                perform_skull_stripped_renormalization[i]
            )
            morphologist.Normalization_select_Normalization_pipeline = (
                Normalization_select_Normalization_pipeline[i]
            )
            morphologist.spm_normalization_version = spm_normalization_version[i]

            metadata = ProcessMetadata(morphologist, execution_context)
            metadata.bids = input_metadata
            metadata.generate_paths(morphologist)
            execution_ids.append(engine.start(morphologist))
    return execution_ids


if __name__ == "__main__":
    import sys

    from soma.qt_gui.qt_backend import Qt

    from capsul.web import CapsulBrowserWindow

    qt_app = Qt.QApplication.instance()
    if not qt_app:
        qt_app = Qt.QApplication(sys.argv)
    self = TestFakeMorphologist()
    self.subjects = [f"subject{i:04}" for i in range(20)]
    print(f"Setting up config and data files for {len(self.subjects)}")
    self.setUp()
    try:
        with self.capsul.engine() as engine:
            widget = CapsulBrowserWindow()
            widget.show()
            # import cProfile
            # cProfile.run(
            #     'execution_ids = without_iteration(engine)',
            #     '/tmp/without_iteration')
            # cProfile.run(
            #     'execution_ids = with_iteration(engine)',
            #     '/tmp/with_iteration')
            start = time.time()
            execution_ids = with_iteration(engine)
            print("Duration:", time.time() - start)
            qt_app.exec_()
            del widget
            for execution_id in execution_ids:
                engine.dispose(execution_id)
    finally:
        self.tearDown()
