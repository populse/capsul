import contextlib
import io
import json
import os
import subprocess
import sys
import traceback

from populse_db.database import json_decode, json_encode
from soma.undefined import undefined

from .application import Capsul
from .database import engine_database


def run_job(
    database,
    engine_id,
    execution_id,
    job_uuid,
    same_python=False,
    debug=False,
    set_pid_function=None,
):
    if same_python:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                execute_job(database, engine_id, execution_id, job_uuid, debug=debug)
                return_code = 0
            except Exception as e:
                print(traceback.format_exc(), file=stderr)
                return_code = 1
        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
    else:
        env = os.environ.copy()
        env["CAPSUL_WORKER_DATABASE"] = json.dumps(database.config)
        if debug:
            env["CAPSUL_DEBUG"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-m", "capsul.run", engine_id, execution_id, job_uuid],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=sys.getdefaultencoding(),
        )
        if set_pid_function is not None:
            set_pid_function(proc.pid)
        stdout, stderr = proc.communicate()
        return_code = proc.returncode
    return return_code, stdout, stderr


def execute_job(database, engine_id, execution_id, job_uuid, debug=False):
    # TODO: the context should be specific to the job, not only the execution
    execution_context = database.execution_context(engine_id, execution_id)
    execution_context.dataset.tmp = {
        "path": database.tmp(engine_id, execution_id),
    }
    execution_context.activate_modules_config()
    job = database.job(engine_id, execution_id, job_uuid)
    if job is None:
        raise ValueError(f"No such job: {job_uuid}")
    job_parameters = database.get_job_input_parameters(
        engine_id, execution_id, job["uuid"]
    )
    process_json = job["process"]
    process = Capsul.executable(process_json)
    if debug:
        from pprint import pprint

        print(f"---- init {process.definition} ----")
        pprint(job_parameters)
        print("----")
    for field in process.user_fields():
        value = job_parameters.get(field.name)
        if value is not None:
            if value == {} and field.is_list():
                # In redis database, LUA converts empty lists to empty dict
                # when encoding json.
                value = []
            setattr(process, field.name, json_decode(value))
    execution_context.executable = process
    process.resolve_paths(execution_context)
    if debug:
        print(f"---- start {process.definition} ----")
        for field in process.user_fields():
            if not field.output:
                value = getattr(process, field.name, undefined)
                if value is not undefined:
                    print("   ", field.name, "=", value)
    process.before_execute(execution_context)
    result = process.execute(execution_context)
    process.after_execute(result, execution_context)
    if debug:
        print(f"---- stop {process.definition} ----")
        for field in process.user_fields():
            if field.output:
                value = getattr(process, field.name, undefined)
                if value is not undefined:
                    print("   ", field.name, "=", value)
    output_values = {}
    for field in process.user_fields():
        if field.output:
            value = getattr(process, field.name, undefined)
            if value is not undefined:
                output_values[field.name] = json_encode(value)
    if output_values is not None:
        database.set_job_output_parameters(
            engine_id, execution_id, job["uuid"], output_values
        )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            f"Wrong number of parameters, 3 expected:command={sys.argv}",
            file=sys.stderr,
        )
        sys.exit(1)
    engine_id = sys.argv[1]
    execution_id = sys.argv[2]
    job_uuid = sys.argv[3]
    db_config = os.environ.get("CAPSUL_WORKER_DATABASE")
    if not db_config:
        print(
            "Capsul cannot run job because CAPSUL_WORKER_DATABASE is not defined: "
            f"command={sys.argv}",
            file=sys.stderr,
        )
        sys.exit(1)
    db_config = json.loads(db_config)
    debug = "CAPSUL_DEBUG" in os.environ
    with engine_database(db_config) as database:
        execute_job(database, engine_id, execution_id, job_uuid, debug=debug)
