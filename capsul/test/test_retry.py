import os
import tempfile
from capsul.api import Capsul, Process, Pipeline
from soma.controller import field, File, undefined


class ControlledFailure(Process):
    file: field(type_=File, read=True, write=True, optional=True)
    fail_count: int = 0
    value: field(type_=str, optional=True)
    input: field(type_=File, optional=True)
    output: field(type_=File, write=True)

    def execute(self, context):
        if self.file is not undefined and self.fail_count:
            if os.path.exists(self.file):
                with open(self.file) as f:
                    count = f.read()
                count = int(count) if count else 0
            else:
                count = 0
            count += 1
            with open(self.file, "w") as f:
                f.write(str(count))
            if self.fail_count >= count:
                raise Exception(
                    f"Process run count = {count} but failure count = {self.fail_count}"
                )
        result = []
        if self.input is not undefined:
            with open(self.input) as input:
                result.append(input.read())
        if self.value is not undefined:
            result.append(self.value)
        with open(self.output, "w") as output:
            output.write("\n".join(result))


class PipelineToRestart(Pipeline):
    def pipeline_definition(self):
        self.add_process(
            "initial_value",
            ControlledFailure,
            do_not_export=["file", "fail_count", "value"],
        )
        self.add_process(
            "successful",
            ControlledFailure,
            do_not_export=["file", "fail_count", "value"],
        )
        self["successful.value"] = "successful"
        self.add_process(
            "must_restart", ControlledFailure, do_not_export=["fail_count", "value"]
        )
        self["must_restart.value"] = "must_restart"
        self["must_restart.fail_count"] = 1
        self.add_process(
            "final_value",
            ControlledFailure,
            do_not_export=["file", "fail_count", "value"],
        )
        self["final_value.value"] = "final_value"

        self.export_parameter("initial_value", "value", "initial_value")
        self.add_link("initial_value.output->successful.input")
        self.add_link("successful.output->must_restart.input")
        self.add_link("must_restart.output->final_value.input")
        self.export_parameter("initial_value", "output", allow_existing_plug=True)
        self.export_parameter("successful", "output", allow_existing_plug=True)
        self.export_parameter("must_restart", "output", allow_existing_plug=True)
        self.export_parameter("final_value", "output", allow_existing_plug=True)


class SubPipelineToRestart(Pipeline):
    def pipeline_definition(self):
        self.add_process("sub1", PipelineToRestart, do_not_export=["initial_value"])
        self["sub1.initial_value"] = "initial_value_1"
        self.add_process("sub2", PipelineToRestart, do_not_export=["initial_value"])
        self["sub2.initial_value"] = "initial_value_2"
        self.add_link("sub1.output->sub2.input")
        self.export_parameter("sub1", "file", "file1")
        self.export_parameter("sub2", "file", "file2")
        self.export_parameter("sub1", "output", allow_existing_plug=True)
        self.export_parameter("sub2", "output", allow_existing_plug=True)


def test_retry_pipeline():
    executable = Capsul.executable(PipelineToRestart)
    tmp_failure = tempfile.NamedTemporaryFile()
    tmp_result = tempfile.NamedTemporaryFile()
    executable.initial_value = "initial_value"
    executable.file = tmp_failure.name
    executable.output = tmp_result.name

    with Capsul().engine() as engine:
        engine.assess_ready_to_start(executable)
        execution_id = engine.start(executable)
        engine.wait(execution_id, timeout=30)
        error = engine.database.error(engine.engine_id, execution_id)
        with open(executable.output) as f:
            result = f.read()
        assert error == "Some jobs failed"
        assert result == "initial_value\nsuccessful"
        engine.prepare_pipeline_for_retry(executable, execution_id)
        execution_id = engine.start(executable)
        engine.wait(execution_id, timeout=30)
        error = engine.database.error(engine.engine_id, execution_id)
        with open(executable.output) as f:
            result = f.read()
        assert error == None
        assert result == "initial_value\nsuccessful\nmust_restart\nfinal_value"
        engine.raise_for_status(execution_id)


def test_retry_sub_pipeline():
    executable = Capsul.executable(SubPipelineToRestart)
    tmp_failure1 = tempfile.NamedTemporaryFile()
    tmp_failure2 = tempfile.NamedTemporaryFile()
    tmp_result = tempfile.NamedTemporaryFile()
    executable.file1 = tmp_failure1.name
    executable.file2 = tmp_failure2.name
    executable.output = tmp_result.name

    with Capsul().engine() as engine:
        engine.assess_ready_to_start(executable)
        execution_id = engine.start(executable)
        engine.wait(execution_id, timeout=30)
        error = engine.database.error(engine.engine_id, execution_id)
        with open(executable.output) as f:
            result = f.read()
        assert error == "Some jobs failed"
        assert result == "initial_value_1\nsuccessful"
        engine.prepare_pipeline_for_retry(executable, execution_id)
        execution_id = engine.start(executable)
        engine.wait(execution_id, timeout=30)
        error = engine.database.error(engine.engine_id, execution_id)
        with open(executable.output) as f:
            result = f.read()
        assert error == "Some jobs failed"
        assert (
            result
            == "initial_value_1\nsuccessful\nmust_restart\nfinal_value\ninitial_value_2\nsuccessful"
        )
        engine.prepare_pipeline_for_retry(executable, execution_id)
        execution_id = engine.start(executable)
        engine.wait(execution_id, timeout=30)
        error = engine.database.error(engine.engine_id, execution_id)
        with open(executable.output) as f:
            result = f.read()
        assert error == None
        assert (
            result
            == "initial_value_1\nsuccessful\nmust_restart\nfinal_value\ninitial_value_2\nsuccessful\nmust_restart\nfinal_value"
        )
        engine.raise_for_status(execution_id)
