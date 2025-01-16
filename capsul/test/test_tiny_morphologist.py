import json
import shutil
import tempfile
import unittest
from pathlib import Path

from soma.controller import Directory, File, field, undefined

from capsul.api import Capsul, Pipeline, Process
from capsul.config.configuration import (
    ModuleConfiguration,
    default_builtin_database,
    default_engine_start_workers,
)
from capsul.dataset import ProcessMetadata, process_schema


class FakeSPMConfiguration(ModuleConfiguration):
    """SPM configuration module"""

    name = "fakespm"
    directory: Directory
    version: str

    def __init__(self):
        super().__init__()

    def is_valid_config(self, requirements, explain=False):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            if explain:
                return f"{self.name} configuration does not match required version {required_version}."
            return False
        return True


class BiasCorrection(Process):
    input: field(type_=File, extensions=(".nii",))
    strength: float = 0.8
    output: field(type_=File, write=True, extensions=(".nii",))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f"{content}Bias correction with strength={self.strength}\n"
        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, "w") as f:
            f.write(content)


@process_schema("bids", "capsul.test.test_tiny_morphologist.BiasCorrection")
def bids_FBiasCorrection(metadata):
    metadata.output = metadata.input
    metadata.output.part.prepend("nobias")


@process_schema("brainvisa", BiasCorrection)
def brainvisa_BiasCorrection(metadata):
    metadata.output = metadata.input
    metadata.output.prefix.prepend("nobias")


class FakeSPMNormalization12(Process):
    input: field(type_=File, extensions=(".nii",))
    template: field(
        type_=File, extensions=(".nii",), completion="spm", dataset="fakespm"
    ) = "!{fakespm.directory}/template"
    output: field(type_=File, write=True, extensions=(".nii",))

    requirements = {"fakespm": {"version": "12"}}

    def execute(self, context):
        fakespmdir = Path(context.fakespm.directory)
        real_version = (fakespmdir / "fakespm").read_text().strip()
        with open(self.input) as f:
            content = f.read()
        with open(self.template) as f:
            template = f.read().strip()
        content = f'{content}Normalization with fakespm {real_version} installed in {fakespmdir} using template "{template}"\n'
        with open(self.output, "w") as f:
            f.write(content)


@process_schema("bids", "capsul.test.test_tiny_morphologist.FakeSPMNormalization12")
def bids_FakeSPMNormalization12(metadata):
    metadata.output = metadata.input
    metadata.output.part.prepend("normalized_fakespm12")


@process_schema(
    "brainvisa", "capsul.test.test_tiny_morphologist.FakeSPMNormalization12"
)
def brainvisa_FakeSPMNormalization12(metadata):
    metadata.output = metadata.input
    metadata.output.prefix.prepend("normalized_fakespm12")


class FakeSPMNormalization8(FakeSPMNormalization12):
    requirements = {"fakespm": {"version": "8"}}


@process_schema("bids", "capsul.test.test_tiny_morphologist.FakeSPMNormalization8")
def bids_FakeSPMNormalization8(metadata):
    metadata.output = metadata.input
    metadata.output.part.prepend("normalized_fakespm8")


@process_schema("brainvisa", "capsul.test.test_tiny_morphologist.FakeSPMNormalization8")
def brainvisa_FakeSPMNormalization8(metadata):
    metadata.output = metadata.input
    metadata.output.prefix.prepend("normalized_fakespm8")


class AimsNormalization(Process):
    input: field(type_=File, extensions=(".nii",))
    origin: field(type_=list[float], default_factory=lambda: [1.2, 3.4, 5.6])
    output: field(type_=File, write=True, extensions=(".nii",))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f"{content}Normalization with Aims, origin={self.origin}\n"
        Path(self.output).parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, "w") as f:
            f.write(content)


@process_schema("bids", "capsul.test.test_tiny_morphologist.AimsNormalization")
def bids_AimsNormalization(metadata):
    metadata.output = metadata.input
    metadata.output.part.prepend("normalized_aims")


@process_schema("brainvisa", "capsul.test.test_tiny_morphologist.AimsNormalization")
def brainvisa_AimsNormalization(metadata):
    metadata.output = metadata.input
    metadata.output.prefix.prepend("normalized_aims")


class Normalization(Pipeline):
    def pipeline_definition(self):
        self.add_process("fakespm_normalization_12", FakeSPMNormalization12)
        self.add_process("fakespm_normalization_8", FakeSPMNormalization8)
        self.add_process("aims_normalization", AimsNormalization)

        self.export_parameter("fakespm_normalization_12", "input")
        self.add_link("input->fakespm_normalization_8.input")
        self.export_parameter("fakespm_normalization_12", "template")
        self.add_link("template->fakespm_normalization_8.template")
        self.add_link("input->aims_normalization.input")

        self.create_switch(
            "normalization",
            {
                "none": {"output": "input"},
                "fakespm12": {"output": "fakespm_normalization_12.output"},
                "fakespm8": {"output": "fakespm_normalization_8.output"},
                "aims": {"output": "aims_normalization.output"},
            },
        )


class SplitBrain(Process):
    input: field(type_=File, extensions=(".nii",))
    right_output: field(type_=File, write=True, extensions=(".nii",))
    left_output: field(type_=File, write=True, extensions=(".nii",))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        for side in ("left", "right"):
            side_content = f"{content}Split brain side={side}\n"
            output = getattr(self, f"{side}_output")
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w") as f:
                f.write(side_content)


@process_schema("brainvisa", "capsul.test.test_tiny_morphologist.SplitBrain")
def brainvisa_SplitBrain(metadata):
    metadata.right_output = metadata.input
    metadata.left_output = metadata.input
    metadata.right_output.prefix.prepend("split")
    metadata.left_output.prefix.prepend("split")
    metadata.right_output.suffix.append("right")
    metadata.left_output.suffix.append("left")


class ProcessHemisphere(Process):
    input: field(type_=File, extensions=(".nii",))
    output: field(type_=File, write=True, extensions=(".nii",))

    def execute(self, context):
        with open(self.input) as f:
            content = f.read()
        content = f"{content}Process hemisphere\n"
        with open(self.output, "w") as f:
            f.write(content)


@process_schema("brainvisa", "capsul.test.test_tiny_morphologist.ProcessHemisphere")
def brainvisa_ProcessHemisphere(metadata):
    metadata.output = metadata.input
    metadata.output.prefix.prepend("hemi")


class TinyMorphologist(Pipeline):
    def pipeline_definition(self):
        self.add_process("nobias", BiasCorrection)

        self.add_process("normalization", Normalization)

        self.add_process("split", SplitBrain)
        self.add_process("right_hemi", ProcessHemisphere)
        self.add_process("left_hemi", ProcessHemisphere)

        self.add_link("nobias.output->normalization.input")
        self.export_parameter("nobias", "output", "nobias")

        self.add_link("normalization.output->split.input")
        self.export_parameter("normalization", "output", "normalized")
        self.add_link("split.right_output->right_hemi.input")
        self.export_parameter("right_hemi", "output", "right_hemisphere")
        self.add_link("split.left_output->left_hemi.input")
        self.export_parameter("left_hemi", "output", "left_hemisphere")


@process_schema("bids", "capsul.test.test_tiny_morphologist.TinyMorphologist")
def bids_TinyMorphologist(metadata):
    metadata["output:*"].process = "tinymorphologist"


@process_schema("brainvisa", "capsul.test.test_tiny_morphologist.TinyMorphologist")
def brainvisa_TinyMorphologist(metadata):
    metadata["output:*"].process = "tinymorphologist"


def concatenate(inputs: list[File], result: File):
    with open(result, "w") as o:
        for f in inputs:
            print("-" * 40, file=o)
            print(f, file=o)
            print("-" * 40, file=o)
            with open(f) as i:
                o.write(i.read())


class TestTinyMorphologist(unittest.TestCase):
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
        self.tmp = tmp = Path(tempfile.mkdtemp(prefix="capsul_test_tinym_"))
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
                        / f"sub-{subject}_ses-{session}_{data_type}.nii"
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

                    with file.with_suffix(".json").open("w") as f:
                        json.dump(
                            dict(json_metadata=f"JSON metadata for {file_name}"), f
                        )

        # Configuration base dictionary
        config = {
            "databases": {
                "builtin": {
                    "path": "",
                },
            },
            "builtin": {
                "config_modules": [
                    "capsul.test.test_tiny_morphologist",
                ],
                "dataset": {
                    "input": {
                        "path": str(self.bids),
                        "metadata_schema": "bids",
                    },
                    "output": {
                        "path": str(self.brainvisa),
                        "metadata_schema": "brainvisa",
                    },
                },
            },
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
            }
            config["builtin"].setdefault("fakespm", {})[f"fakespm_{version}"] = (
                fakespm_config
            )

        # Create a configuration file
        self.config_file = tmp / "capsul_config.json"
        with self.config_file.open("w") as f:
            json.dump(config, f)

        self.capsul = Capsul(
            "test_tiny_morphologist",
            site_file=self.config_file,
            user_file=None,
            database_path="",
        )
        return super().setUp()

    def tearDown(self):
        self.capsul = None
        shutil.rmtree(self.tmp)
        return super().tearDown()

    def test_tiny_morphologist_config(self):
        self.maxDiff = 2000
        expected_config = {
            "databases": {
                "builtin": {"path": "", "type": default_builtin_database["type"]}
            },
            "builtin": {
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
                },
                "persistent": True,
                "fakespm": {
                    "fakespm_12": {
                        "directory": str(self.tmp / "software" / "fakespm-12"),
                        "version": "12",
                    },
                    "fakespm_8": {
                        "directory": str(self.tmp / "software" / "fakespm-8"),
                        "version": "8",
                    },
                },
                "config_modules": ["capsul.test.test_tiny_morphologist"],
            },
        }
        self.assertEqual(self.capsul.config.asdict(), expected_config)

        engine = self.capsul.engine()
        tiny_morphologist = self.capsul.executable(
            "capsul.test.test_tiny_morphologist.TinyMorphologist"
        )

        context = engine.execution_context(tiny_morphologist)
        expected_context = {
            "config_modules": ["capsul.test.test_tiny_morphologist"],
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
            },
        }
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

        tiny_morphologist.normalization = "fakespm12"
        context = engine.execution_context(tiny_morphologist)
        fakespm12_conf = {
            "directory": str(self.tmp / "software" / "fakespm-12"),
            "version": "12",
        }
        expected_context["fakespm"] = fakespm12_conf
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

        tiny_morphologist_iteration = self.capsul.executable_iteration(
            "capsul.test.test_tiny_morphologist.TinyMorphologist",
            non_iterative_plugs=["template"],
        )

        context = engine.execution_context(tiny_morphologist_iteration)
        del expected_context["fakespm"]
        context = engine.execution_context(tiny_morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)
        tiny_morphologist_iteration.normalization = ["none", "aims", "fakespm12"]
        expected_context["fakespm"] = fakespm12_conf
        context = engine.execution_context(tiny_morphologist_iteration)
        dict_context = context.asdict()
        self.assertEqual(dict_context, expected_context)

    def test_tiny_path_generation(self):
        expected = {
            "none": {
                "template": "!{fakespm.directory}/template",
                "nobias": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "normalized": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "right_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_right.nii",
                "left_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_left.nii",
            },
            "aims": {
                "template": "!{fakespm.directory}/template",
                "nobias": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "normalized": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/normalized_aims_nobias_aleksander.nii",
                "right_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                "left_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
            },
            "fakespm12": {
                "template": "!{fakespm.directory}/template",
                "nobias": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "normalized": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/normalized_fakespm12_nobias_aleksander.nii",
                "right_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm12_nobias_aleksander_right.nii",
                "left_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm12_nobias_aleksander_left.nii",
            },
            "fakespm8": {
                "template": "!{fakespm.directory}/template",
                "nobias": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "normalized": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/normalized_fakespm8_nobias_aleksander.nii",
                "right_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                "left_hemisphere": "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
            },
        }

        tiny_morphologist = self.capsul.executable(
            "capsul.test.test_tiny_morphologist.TinyMorphologist"
        )
        engine = self.capsul.engine()
        execution_context = engine.execution_context(tiny_morphologist)
        input = str(
            self.tmp
            / "bids"
            / "rawdata"
            / "sub-aleksander"
            / "ses-m0"
            / "anat"
            / "sub-aleksander_ses-m0_T1w.nii"
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
                "extension": "nii",
                "session_metadata": "session metadata for sub-aleksander_ses-m0_T2w.nii",
                "scan_metadata": "scan metadata for sub-aleksander_ses-m0_T1w.nii",
                "json_metadata": "JSON metadata for sub-aleksander_ses-m0_T1w.nii",
            },
        )
        for normalization in ("none", "aims", "fakespm12", "fakespm8"):
            tiny_morphologist.normalization = normalization
            metadata = ProcessMetadata(tiny_morphologist, execution_context)
            self.assertEqual(
                metadata.parameters_per_schema,
                {
                    "brainvisa": [
                        "nobias",
                        "normalized",
                        "right_hemisphere",
                        "left_hemisphere",
                    ],
                    "bids": ["input"],
                },
            )
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
                    "extension": "nii",
                },
            )
            metadata.generate_paths(tiny_morphologist)
            params = dict(
                (i, getattr(tiny_morphologist, i, undefined))
                for i in (
                    "template",
                    "nobias",
                    "normalized",
                    "right_hemisphere",
                    "left_hemisphere",
                )
            )
            self.maxDiff = 2000
            self.assertEqual(params, expected[normalization])

            with self.capsul.engine() as engine:
                status = engine.run(tiny_morphologist, timeout=30)
                self.assertEqual(status, "ended")

    def test_tiny_morphologist_iteration(self):
        expected_completion = {
            "input": [
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
                "!{dataset.input.path}/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
            ],
            "left_hemisphere": [
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
            ],
            "nobias": [
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
            ],
            "normalization": [
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
            ],
            "right_hemisphere": [
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                "!{dataset.output.path}/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
            ],
        }

        expected_resolution = {
            "input": [
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m0/anat/sub-aleksander_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m12/anat/sub-aleksander_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-aleksander/ses-m24/anat/sub-aleksander_ses-m24_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m0/anat/sub-casimiro_ses-m0_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m12/anat/sub-casimiro_ses-m12_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
                f"{self.tmp}/bids/rawdata/sub-casimiro/ses-m24/anat/sub-casimiro_ses-m24_T1w.nii",
            ],
            "left_hemisphere": [
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_casimiro_left.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_left.nii",
            ],
            "nobias": [
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/nobias_aleksander.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/nobias_casimiro.nii",
            ],
            "normalization": [
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
                "none",
                "aims",
                "fakespm8",
            ],
            "right_hemisphere": [
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/aleksander/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_aleksander_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m0/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m12/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_aims_nobias_casimiro_right.nii",
                f"{self.tmp}/brainvisa/whatever/casimiro/tinymorphologist/m24/default_analysis/hemi_split_normalized_fakespm8_nobias_casimiro_right.nii",
            ],
        }

        tiny_morphologist_iteration = self.capsul.executable_iteration(
            "capsul.test.test_tiny_morphologist.TinyMorphologist",
            non_iterative_plugs=["template"],
        )

        # class TinyMorphologistIterationBrainVISA(ProcessSchema, schema='brainvisa', process=tiny_morphologist_iteration):
        #     _ = {
        #         '*': {
        #             'suffix': lambda iteration_index, **kwargs: f'{{executable.normalization[{iteration_index}]}}',
        #         }
        #     }

        engine = self.capsul.engine()
        execution_context = engine.execution_context(tiny_morphologist_iteration)

        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        inputs = []
        normalizations = []
        for path in sorted(
            self.capsul.config.builtin.dataset.input.find(suffix="T1w", extension="nii")
        ):
            input_metadata = execution_context.dataset["input"].schema.metadata(path)
            inputs.extend([input_metadata] * 3)
            normalizations += ["none", "aims", "fakespm8"]
        tiny_morphologist_iteration.normalization = normalizations

        metadata = ProcessMetadata(tiny_morphologist_iteration, execution_context)
        metadata.bids = inputs
        metadata.brainvisa = [{"center": "whatever"}] * len(inputs)
        metadata.generate_paths(tiny_morphologist_iteration)
        self.maxDiff = 11000
        for name, value in expected_completion.items():
            self.assertEqual(
                getattr(tiny_morphologist_iteration, name),
                value,
                f"Differing value for parameter {name}",
            )
        tiny_morphologist_iteration.resolve_paths(execution_context)
        for name, value in expected_resolution.items():
            self.assertEqual(
                getattr(tiny_morphologist_iteration, name),
                value,
                f"Differing value for parameter {name}",
            )
        for i in (0, 3, 6, 9, 12, 15):
            tiny_morphologist_iteration.select_iteration_index(i)
            self.assertNotIn(
                tiny_morphologist_iteration.process.nodes["split"].input,
                (None, undefined),
            )
        with self.capsul.engine() as engine:
            status = engine.run(tiny_morphologist_iteration, timeout=60)

        self.assertEqual(status, "ended")


if __name__ == "__main__":
    import sys

    from soma.qt_gui.qt_backend import Qt

    from capsul.web import CapsulBrowserWindow

    qt_app = Qt.QApplication.instance()
    if not qt_app:
        qt_app = Qt.QApplication(sys.argv)
    self = TestTinyMorphologist()
    self.subjects = [f"subject{i:04}" for i in range(500)]
    print(
        f"Setting up config and data files for {len(self.subjects)} subjects and 3 time points"
    )
    self.setUp()
    try:
        tiny_morphologist_iteration = self.capsul.executable_iteration(
            "capsul.test.test_tiny_morphologist.TinyMorphologist",
            non_iterative_plugs=["template"],
        )

        engine = self.capsul.engine()
        execution_context = engine.execution_context(tiny_morphologist_iteration)

        # Parse the dataset with BIDS-specific query (here "suffix" is part
        #  of BIDS specification). The object returned contains info for main
        # BIDS fields (sub, ses, acq, etc.)
        inputs = []
        normalizations = []
        for path in sorted(
            self.capsul.config.builtin.dataset.input.find(suffix="T1w", extension="nii")
        ):
            input_metadata = execution_context.dataset["input"].schema.metadata(path)
            inputs.extend([input_metadata] * 3)
            normalizations += ["none", "aims", "fakespm8"]
        tiny_morphologist_iteration.normalization = normalizations

        metadata = ProcessMetadata(tiny_morphologist_iteration, execution_context)
        metadata.bids = inputs
        metadata.brainvisa = {"center": "whatever"}
        metadata.generate_paths(tiny_morphologist_iteration)

        with self.capsul.engine() as engine:
            execution_id = engine.start(tiny_morphologist_iteration)
            try:
                widget = CapsulBrowserWindow()
                widget.show()
                # from capsul.qt_gui.widgets import PipelineDeveloperView
                tiny_morphologist = Capsul.executable(
                    "capsul.test.test_tiny_morphologist.TinyMorphologist"
                )
                # view1 = PipelineDeveloperView(tiny_morphologist, show_sub_pipelines=True, allow_open_controller=True, enable_edition=True)
                # view1.show()
                qt_app.exec_()
                del widget
                # del view1
                engine.wait(execution_id, timeout=1000)
                # engine.raise_for_status(execution_id)
            except TimeoutError:
                # engine.print_execution_report(engine.execution_report(engine.engine_id, execution_id))
                raise
    finally:
        self.tearDown()
