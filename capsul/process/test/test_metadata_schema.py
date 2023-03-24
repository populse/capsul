# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from soma.controller import File, field

from capsul.api import Process, executable, Capsul
from ...dataset import Dataset, MetadataSchema
from capsul.dataset import ProcessSchema, ProcessMetadata


class DummyProcess(Process):
    f: float = field(output=False)

    def __init__(self, definition):
        super(DummyProcess, self).__init__(definition)
        self.add_field("truc", type_=File, write=False)
        self.add_field("bidule", type_=File, write=True)

    def execute(self, context):
        with open(self.bidule, "w") as f:
            with open(self.truc) as g:
                f.write(g.read())


class DummyListProcess(Process):
    truc: field(type_=list[File], write=False)
    bidule: field(type_=list[File], write=False)
    result: field(type_=File, write=True)

    def execute(self, context):
        with open(self.result, "w") as f:
            f.write("{\n    truc=%s,\n    bidule=%s\n}" % (self.truc, self.bidule))


class CustomMetadataSchema(MetadataSchema):
    schema_name = "custom"
    process: str
    parameter: str
    center: str
    subject: str
    analysis: str
    group: str

    def _path_list(self):
        items = []
        for field in self.fields():  # noqa: F402
            value = getattr(self, field.name, None)
            if value:
                items.append(value)
        return ["_".join(items)]


class DummyListProcessCustom(ProcessSchema, schema="custom", process=DummyListProcess):
    _ = {"*": {"process": "DummyListProcess"}}
    truc = {"parameter": "truc"}
    bidule = {"parameter": "bidule"}
    result = {"parameter": "result"}


class DummyProcessCustom(ProcessSchema, schema="custom", process=DummyProcess):
    _ = {"*": {"process": "DummyProcess"}}
    truc = {"parameter": "truc"}
    bidule = {"parameter": "bidule"}


class TestCompletion(unittest.TestCase):
    def setUp(self):
        global old_home
        global temp_home_dir
        # Run tests with a temporary HOME directory so that they are isolated from
        # the user's environment
        temp_home_dir = None
        old_home = os.environ.get("HOME")
        try:
            app_name = "test_metadata_schema"
            temp_home_dir = Path(tempfile.mkdtemp(prefix=f"capsul_{app_name}_"))
            os.environ["HOME"] = str(temp_home_dir)
            config = temp_home_dir / ".config"
            config.mkdir()
            input = temp_home_dir / "in"
            input.mkdir()
            output = temp_home_dir / "out"
            output.mkdir()
            site_file = config / f"{app_name}.json"
            with site_file.open("w") as f:
                json.dump(
                    {
                        "builtin": {
                            "python_modules": [
                                "capsul.process.test.test_metadata_schema"
                            ],
                            "dataset": {
                                "input": {
                                    "path": str(input),
                                    "metadata_schema": "custom",
                                },
                                "output": {
                                    "path": str(output),
                                    "metadata_schema": "custom",
                                },
                            },
                        }
                    },
                    f,
                )
            Capsul.delete_singleton()
            capsul = Capsul(app_name, site_file=site_file)

        except BaseException:  # clean up in case of interruption
            if old_home is None:
                del os.environ["HOME"]
            else:
                os.environ["HOME"] = old_home
            if temp_home_dir:
                shutil.rmtree(temp_home_dir)
            raise

    def tearDown(self):
        if old_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = old_home
        shutil.rmtree(temp_home_dir)
        Capsul.delete_singleton()

    def test_completion(self):
        global temp_home_dir

        process = executable("capsul.process.test.test_metadata_schema.DummyProcess")
        execution_context = Capsul().engine().execution_context(process)

        metadata = ProcessMetadata(process, execution_context)

        metadata.custom = {
            "center": "jojo",
            "subject": "barbapapa",
        }

        metadata.generate_paths(process)
        process.resolve_paths(execution_context)
        self.assertEqual(
            os.path.normpath(process.truc),
            os.path.normpath(f"{temp_home_dir}/in/DummyProcess_truc_jojo_barbapapa"),
        )
        self.assertEqual(
            os.path.normpath(process.bidule),
            os.path.normpath(f"{temp_home_dir}/out/DummyProcess_bidule_jojo_barbapapa"),
        )

    def test_iteration(self):
        pipeline = Capsul().executable_iteration(
            "capsul.process.test.test_metadata_schema.DummyProcess",
            iterative_plugs=["truc", "bidule"],
        )
        execution_context = Capsul().engine().execution_context(pipeline)

        metadata = ProcessMetadata(pipeline, execution_context)

        metadata.custom = [
            {
                "process": "DummyProcess",
                "center": "muppets",
                "subject": i,
            }
            for i in ["kermit", "piggy", "stalter", "waldorf"]
        ]

        metadata.generate_paths(pipeline)
        pipeline.resolve_paths(execution_context)
        self.assertEqual(
            [os.path.normpath(p) for p in pipeline.truc],
            [
                f"{temp_home_dir}/in/DummyProcess_truc_muppets_kermit",
                f"{temp_home_dir}/in/DummyProcess_truc_muppets_piggy",
                f"{temp_home_dir}/in/DummyProcess_truc_muppets_stalter",
                f"{temp_home_dir}/in/DummyProcess_truc_muppets_waldorf",
            ],
        )
        self.assertEqual(
            [os.path.normpath(p) for p in pipeline.bidule],
            [
                f"{temp_home_dir}/out/DummyProcess_bidule_muppets_kermit",
                f"{temp_home_dir}/out/DummyProcess_bidule_muppets_piggy",
                f"{temp_home_dir}/out/DummyProcess_bidule_muppets_stalter",
                f"{temp_home_dir}/out/DummyProcess_bidule_muppets_waldorf",
            ],
        )

    @unittest.skip("Not working yet")
    def test_list_completion(self):
        process = executable(
            "capsul.process.test.test_metadata_schema.DummyListProcess"
        )
        execution_context = Capsul().engine().execution_context(process)

        metadata = ProcessMetadata(process, execution_context)

        metadata.custom = [
            {
                "center": "jojo",
                "subject": "barbapapa",
                "group": "cartoon",
            },
            {
                "center": "koko",
                "subject": "barbatruc",
                "group": "cartoon",
            },
        ]

        metadata.generate_paths(process)
        process.resolve_paths(execution_context)
        self.assertEqual(
            [os.path.normpath(p) for p in process.truc],
            [
                f"{temp_home_dir}/in/DummyListProcess_truc_jojo_barbapapa",
                f"{temp_home_dir}/in/DummyListProcess_truc_koko_barbatruc",
            ],
        )
        self.assertEqual(
            [os.path.normpath(p) for p in process.bidule],
            [
                f"{temp_home_dir}/in/DummyListProcess_bidule_jojo_barbapapa",
                f"{temp_home_dir}/in/DummyListProcess_bidule_koko_barbatruc",
            ],
        )
        self.assertEqual(
            os.path.normpath(process.result),
            f"{temp_home_dir}/out/DummyListProcess_result_cartoon",
        )

    def test_run_iteraton(self):
        pipeline = Capsul().executable_iteration(
            "capsul.process.test.test_metadata_schema.DummyProcess",
            iterative_plugs=["truc", "bidule"],
        )
        execution_context = Capsul().engine().execution_context(pipeline)
        subjects = ["kermit", "piggy", "stalter", "waldorf"]

        metadata = ProcessMetadata(pipeline, execution_context)

        metadata.custom = [
            {
                "process": "DummyProcess",
                "center": "muppets",
                "subject": i,
            }
            for i in subjects
        ]

        metadata.generate_paths(pipeline)

        # create input files
        for s in subjects:
            with open(
                Path(execution_context.dataset.input.path)
                / f"DummyProcess_truc_muppets_{s}",
                "w",
            ) as f:
                f.write(f"{s}\n")

        # run
        with Capsul().engine() as engine:
            engine.run(pipeline, timeout=5)

        # check outputs
        out_files = [
            Path(execution_context.dataset.output.path)
            / f"DummyProcess_bidule_muppets_{s}"
            for s in subjects
        ]
        for s, out_file in zip(subjects, out_files):
            self.assertTrue(out_file.is_file())
            with open(out_file) as f:
                self.assertTrue(f.read() == f"{s}\n")
