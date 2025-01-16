import os
import shutil
import sys
import tempfile
import unittest

from soma.controller import File

from capsul.api import Capsul, Pipeline, Process


class DummyProcess1(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=File)

        # outputs
        self.add_field("output", type_=File, output=True, write=True)

    def execute(self, context):
        base, ext = os.path.splitext(self.input)
        self.output = f"{base}_output{ext}"
        with open(self.output, "w") as f:
            with open(self.input) as g:
                f.write(g.read())
            f.write("This is an output file\n")


class DummyProcess2(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=File)

        # outputs
        self.add_field("outputs", type_=list[File], output=True, write=False)

    def execute(self, context):
        base, ext = os.path.splitext(self.input)
        new_output = f"{base}_bis{ext}"
        self.outputs = [self.input, new_output]
        with open(new_output, "w") as f:
            with open(self.input) as g:
                f.write(g.read() + "And a second output file\n")


class DummyProcess2alt(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=File)

        # outputs
        self.add_field("outputs", list[File], output=True, write=True)

    def execute(self, context):
        base, ext = os.path.splitext(self.input)
        new_output = f"{base}_ter{ext}"
        self.outputs = [new_output]
        with open(new_output, "w") as f:
            with open(self.input) as g:
                f.write(g.read() + "And another output file\n")


class DummyProcess3(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=list[File])

        # outputs
        self.add_field("output", type_=File, write=True)

    def execute(self, definition):
        with open(self.output, "w") as f:
            for in_filename in self.input:
                with open(in_filename) as g:
                    f.write(g.read())


class DummyProcess3alt(Process):
    def __init__(self, definition):
        super().__init__(definition)

        # inputs
        self.add_field("input", type_=list[File])

        # outputs
        self.add_field("output", type_=File, output=True, write=True)

    def execute(self, context):
        if len(self.input) != 0:
            base, ext = os.path.splitext(self.input[0])
            self.output = f"{base}_alt{ext}"
            with open(self.output, "w") as f:
                for in_filename in self.input:
                    with open(in_filename) as g:
                        f.write(g.read())


class DummyPipeline(Pipeline):
    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess1"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess2"
        )
        self.add_process(
            "node2alt", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess2alt"
        )
        self.create_switch(
            "node2_switch",
            {
                "node2": {"files": "node2.outputs"},
                "node2alt": {"files": "node2alt.outputs"},
            },
        )
        self.add_process(
            "node3", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess3"
        )
        # Links
        self.add_link("node1.output->node2.input")
        self.add_link("node1.output->node2alt.input")
        self.add_link("node2_switch.files->node3.input")

        self.node_position = {
            "inputs": (0.0, 155.7061),
            "node1": (146.82718967435613, 124.69369999999998),
            "node2": (303.38348967435616, 0.0),
            "node2_switch": (467.2083896743562, 89.69369999999998),
            "node2alt": (303.38348967435616, 124.69369999999998),
            "node3": (709.7284896743562, 124.69369999999998),
            "outputs": (868.9687193487123, 128.69369999999998),
        }


class DummyPipeline2(Pipeline):
    def pipeline_definition(self):
        # Create processes
        self.add_process(
            "node1", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess1"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess2"
        )
        self.add_process(
            "node3", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess3alt"
        )
        # Links
        self.add_link("node1.output->node2.input")
        self.add_link("node2.outputs->node3.input")

        self.node_position = {
            "inputs": (0.0, 155.7061),
            "node1": (146.82718967435613, 124.69369999999998),
            "node2": (303.38348967435616, 0.0),
            "node3": (709.7284896743562, 124.69369999999998),
            "outputs": (868.9687193487123, 128.69369999999998),
        }


class PipelineWithSubpipeline(Pipeline):
    def pipeline_definition(self):
        self.add_process(
            "node1", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess1"
        )
        self.add_process(
            "pipeline1", "capsul.pipeline.test.test_proc_with_outputs.DummyPipeline2"
        )
        self.add_process(
            "node2", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess1"
        )
        self.add_link("node1.output->pipeline1.input")
        self.add_link("pipeline1.output->node2.input")


class PipelineWithIteration(Pipeline):
    def pipeline_definition(self):
        self.add_process(
            "node_a", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess2"
        )
        self.add_iterative_process(
            "pipeline_a",
            "capsul.pipeline.test.test_proc_with_outputs.DummyPipeline2",
            iterative_plugs=["input", "output"],
        )
        self.add_process(
            "node_b", "capsul.pipeline.test.test_proc_with_outputs.DummyProcess3"
        )
        self.add_link("node_a.outputs->pipeline_a.input")
        self.add_link("pipeline_a.output->node_b.input")


class TestPipelineContainingProcessWithOutputs(unittest.TestCase):
    def setUp(self):
        self.pipeline = Capsul.executable(DummyPipeline)

        tmpdir = tempfile.mkdtemp("capsul_output_test")
        tmpout = os.path.join(tmpdir, "capsul_test_node3_out.txt")

        self.tmpdir = tmpdir
        self.pipeline.input = os.path.join(tmpdir, "file_in.nii")
        with open(self.pipeline.input, "w") as f:
            print("Initial file content.", file=f)
        self.pipeline.output = tmpout
        self.capsul = Capsul(database_path="")

    def tearDown(self):
        if "--keep-tmp" not in sys.argv[1:]:
            if os.path.exists(self.tmpdir):
                shutil.rmtree(self.tmpdir)
        elif os.path.exists(self.tmpdir):
            print("leaving temp dir:", self.tmpdir, file=sys.stderr)

    def test_direct_run(self):
        self.pipeline.node2_switch = "node2"
        with self.capsul.engine() as ce:
            ce.run(self.pipeline, timeout=5)
        self.assertEqual(
            self.pipeline.nodes["node1"].output,
            os.path.join(self.tmpdir, "file_in_output.nii"),
        )
        self.assertEqual(
            self.pipeline.nodes["node3"].input,
            [
                os.path.join(self.tmpdir, "file_in_output.nii"),
                os.path.join(self.tmpdir, "file_in_output_bis.nii"),
            ],
        )
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "And a second output file\n",
            ],
        )

    def test_full_wf(self):
        self.pipeline.node2_switch = "node2"

        with self.capsul.engine() as ce:
            ce.run(self.pipeline, timeout=5)
        self.assertEqual(
            self.pipeline.nodes["node1"].output,
            os.path.join(self.tmpdir, "file_in_output.nii"),
        )
        self.assertEqual(
            self.pipeline.nodes["node3"].input,
            [
                os.path.join(self.tmpdir, "file_in_output.nii"),
                os.path.join(self.tmpdir, "file_in_output_bis.nii"),
            ],
        )
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "And a second output file\n",
            ],
        )

    def test_direct_run_switch(self):
        # change switch and re-run
        self.pipeline.node2_switch = "node2alt"
        with self.capsul.engine() as ce:
            ce.run(self.pipeline, timeout=5)
        self.assertEqual(
            self.pipeline.nodes["node1"].output,
            os.path.join(self.tmpdir, "file_in_output.nii"),
        )
        self.assertEqual(
            self.pipeline.nodes["node3"].input,
            [os.path.join(self.tmpdir, "file_in_output_ter.nii")],
        )
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "And another output file\n",
            ],
        )

    def test_full_wf_switch(self):
        # change switch and re-run
        self.pipeline.node2_switch = "node2alt"

        with self.capsul.engine() as ce:
            ce.run(self.pipeline, timeout=5)
        self.assertEqual(
            self.pipeline.nodes["node1"].output,
            os.path.join(self.tmpdir, "file_in_output.nii"),
        )
        self.assertEqual(
            self.pipeline.nodes["node3"].input,
            [os.path.join(self.tmpdir, "file_in_output_ter.nii")],
        )
        with open(self.pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "And another output file\n",
            ],
        )

    def test_direct_run_subpipeline(self):
        pipeline = Capsul.executable(
            "capsul.pipeline.test.test_proc_with_outputs.PipelineWithSubpipeline"
        )
        pipeline.input = os.path.join(self.tmpdir, "file_in.nii")
        with self.capsul.engine() as ce:
            ce.run(pipeline, timeout=5)
        with open(pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "This is an output file\n",
                "And a second output file\n",
                "This is an output file\n",
            ],
        )

    def test_full_wf_subpipeline(self):
        pipeline = Capsul.executable(
            "capsul.pipeline.test.test_proc_with_outputs.PipelineWithSubpipeline"
        )
        pipeline.input = os.path.join(self.tmpdir, "file_in.nii")

        with self.capsul.engine() as ce:
            ce.run(pipeline, timeout=5)
        with open(pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "This is an output file\n",
                "And a second output file\n",
                "This is an output file\n",
            ],
        )

    @unittest.skip("Dynamic iteration not supported yet")
    def test_direct_run_sub_iter(self):
        pipeline = Capsul.executable(
            "capsul.pipeline.test.test_proc_with_outputs.PipelineWithIteration"
        )
        pipeline.input = os.path.join(self.tmpdir, "file_in.nii")
        pipeline.output = os.path.join(self.tmpdir, "file_out.nii")
        with self.capsul.engine() as ce:
            ce.run(pipeline, timeout=5)
        with open(pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "And a second output file\n",
                "Initial file content.\n",
                "And a second output file\n",
                "This is an output file\n",
                "Initial file content.\n",
                "And a second output file\n",
                "This is an output file\n",
                "And a second output file\n",
            ],
        )

    def xtest_full_wf_sub_iter(self):
        pipeline = Capsul.executable(
            "capsul.pipeline.test.test_proc_with_outputs.PipelineWithIteration"
        )
        pipeline.input = os.path.join(self.tmpdir, "file_in.nii")
        pipeline.output = os.path.join(self.tmpdir, "file_out.nii")

        with self.capsul.engine() as ce:
            ce.run(pipeline, timeout=5)
        with open(pipeline.output) as f:
            res_out = f.readlines()
        self.assertEqual(
            res_out,
            [
                "Initial file content.\n",
                "This is an output file\n",
                "Initial file content.\n",
                "This is an output file\n",
                "And a second output file\n",
                "Initial file content.\n",
                "And a second output file\n",
                "This is an output file\n",
                "Initial file content.\n",
                "And a second output file\n",
                "This is an output file\n",
                "And a second output file\n",
            ],
        )


if __name__ == "__main__":
    verbose = False
    do_test = True
    if len(sys.argv) >= 2 and sys.argv[1] in ("-v", "--verbose"):
        verbose = True
    if "--notest" in sys.argv[1:]:
        do_test = False

    if verbose:
        import sys

        from soma.qt_gui import qt_backend

        qt_backend.set_qt_backend(compatible_qt5=True)
        from soma.qt_gui.qt_backend import QtGui

        from capsul.qt_gui.widgets import PipelineDeveloperView

        app = QtGui.QApplication(sys.argv)
        pipeline = DummyPipeline()
        pipeline.input = "/tmp/file_in.nii"
        pipeline.output = "/tmp/file_out3.nii"
        pipeline.node2_switch = "node2alt"
        view1 = PipelineDeveloperView(
            pipeline, show_sub_pipelines=True, allow_open_controller=True
        )
        view1.show()

        pipeline2 = PipelineWithSubpipeline()
        pipeline2.input = "/tmp/file_in.nii"
        view2 = PipelineDeveloperView(
            pipeline2, show_sub_pipelines=True, allow_open_controller=True
        )
        view2.show()

        pipeline3 = PipelineWithIteration()
        pipeline3.input = "/tmp/file_in.nii"
        pipeline3.output = "/tmp/file_out4.nii"
        view3 = PipelineDeveloperView(
            pipeline3, show_sub_pipelines=True, allow_open_controller=True
        )
        view3.show()

        app.processEvents()

    # if do_test:
    # print("RETURNCODE: ", test())

    if verbose:
        app.exec_()
        del view1
        del view2
