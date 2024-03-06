"""
Specific subprocess-like functions to call Freesurfer taking into account
configuration stored in the execution context configuration.

Alternatively, without an ExecutionContext object, if environment variables are
properly set, the functions will use:

- FREESURFER_HOME
- FREESURFER_SETUP
- SUBJECTS_DIR
"""

import os
import os.path as osp
import subprocess

from soma.controller import undefined
from soma.utils.env import parse_env_lines

"""
If this variable is set, it contains FS runtime env variables,
allowing to run directly freesurfer commands from this process.
"""
freesurfer_runtime_env = None


def set_env_from_config(execution_context):
    """
    Set environment variables FSLDIR, FSL_CONFIG, FSL_PREFIX according to the
    execution context configuration.
    """
    fs_mod = getattr(execution_context, "freesurfer", None)
    if fs_mod:
        if fs_mod.setup_script is not undefined:
            os.environ["FREESURFER_HOME"] = osp.dirname(fs_mod.setup_script)
            os.environ["FREESURFER_SETUP"] = fs_mod.setup_script
        if fs_mod.subjects_dir is not undefined:
            os.environ["SUBJECTS_DIR"] = fs_mod.subjects_dir


def freesurfer_command_with_environment(
    command, execution_context=None, use_runtime_env=True
):
    """
    Given a Freesurfer command where first element is a command name without
    any path or prefix (e.g. "recon-all"). Returns the appropriate command to
    call taking into account the Freesurfer configuration stored in the
    activated configuration.

    Using :func`freesurfer_env` is an alternative to this.
    """

    if execution_context is not None:
        set_env_from_config(execution_context)

    cmd = command
    if use_runtime_env and freesurfer_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    freesurfer_dir = os.environ.get("FREESURFER_HOME")
    freesurfer_script = os.environ.get("FREESURFER_SETUP")

    if freesurfer_script is None and freesurfer_dir is not None:
        freesurfer_script = os.path.join(freesurfer_dir, "SetUpFreeSurfer.sh")

    if freesurfer_script is not None and not os.path.isfile(freesurfer_script):
        freesurfer_script = None

    if freesurfer_dir is not None and freesurfer_script is not None:
        shell = os.environ.get("SHELL", "/bin/sh")

        if shell.endswith("csh"):
            cmd = [
                shell,
                "-c",
                f'setenv FREESURFER_HOME "{freesurfer_dir}"; source {freesurfer_script}; exec {command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]

        else:
            # the SetUpFreeSurfer.sh script is actually for bash, not sh !
            shell = osp.join(osp.dirname(shell), "bash")
            cmd = [
                shell,
                "-c",
                f'export FREESURFER_HOME="{freesurfer_dir}"; source {freesurfer_script}; exec {command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]

    return cmd


def freesurfer_env(execution_context=None):
    """
    get Freesurfer env variables by running the setup script in a separate bash
    process
    """
    global freesurfer_runtime_env

    if freesurfer_runtime_env is not None:
        return freesurfer_runtime_env

    if execution_context is not None:
        set_env_from_config(execution_context)

    kwargs = {}
    cmd = freesurfer_command_with_environment(["env"], use_runtime_env=False)
    new_env = subprocess.check_output(cmd, **kwargs).decode("utf-8").strip()
    new_env = parse_env_lines(new_env)
    env = {}

    for line in new_env:
        name, val = line.strip().split("=", 1)

        if name not in ("_", "SHLVL") and (
            name not in os.environ or os.environ[name] != val
        ):
            env[name] = val

    # cache dict
    freesurfer_runtime_env = env
    return env


class FreesurferPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for Freesurfer commands
    """

    def __init__(self, command, execution_context=None, **kwargs):
        cmd = freesurfer_command_with_environment(
            command, execution_context=execution_context
        )
        env = freesurfer_env()  # execution_context is not needed any longer
        # since global env variables have been set
        if "env" in kwargs:
            env = dict(env)
            env.update(kwargs["env"])
            kwargs = dict(kwargs)
            del kwargs["env"]
        super().__init__(cmd, env=env, **kwargs)


def freesurfer_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for Freesurfer commands
    """
    cmd = freesurfer_command_with_environment(
        command, execution_context=execution_context
    )
    env = freesurfer_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.call(cmd, env=env, **kwargs)


def freesurfer_check_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for Freesurfer commands
    """
    cmd = freesurfer_command_with_environment(
        command, execution_context=execution_context
    )
    env = freesurfer_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.call(cmd, env=env, **kwargs)


def freesurfer_check_output(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for Freesurfer commands
    """
    cmd = freesurfer_command_with_environment(
        command, execution_context=execution_context
    )
    env = freesurfer_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.check_output(cmd, env=env, **kwargs)
