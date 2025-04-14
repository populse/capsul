"""
Specific subprocess-like functions to call ANTS taking into account
configuration stored in ExecutionContext.For instance::

    from capsul.engine import Capsul
    from capsul.in_context.afni import ants_check_call

    c = Capsul(user_file='my_config.json')
    p = c.executable('nipype.interfaces.afni.preprocess.Automask')
    ce = c.engine().execution_context(p)
    ants_check_call(['ants_comamnd', '/somewhere/myimage.nii'])

For calling ANTS command with this module, the first argument of
command line must be the ANTS executable without any path.
The appropriate path is added from the configuration
of the ExecutionContext.
"""

import os
import os.path as osp
import subprocess

from soma.controller import undefined
from soma.utils.env import parse_env_lines

ants_runtime_env = None


def set_env_from_config(execution_context):
    """
    Set environment variables FSLDIR, FSL_CONFIG, FSL_PREFIX according to the
    execution context configuration.
    """
    ants_mod = getattr(execution_context, "ants", None)
    if ants_mod:
        if ants_mod.directory is not undefined:
            os.environ["ANTSPATH"] = ants_mod.directory


def ants_command_with_environment(
    command, execution_context=None, use_runtime_env=True
):
    """
    Given an ANTS command where first element is a command name without
    any path. Returns the appropriate command to call taking into account
    the ANTS configuration stored in the
    activated ExecutionContext.
    """

    if execution_context is not None:
        set_env_from_config(execution_context)

    if use_runtime_env and ants_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    ants_dir = os.environ.get("ANTSPATH")
    cmd = command
    if ants_dir:
        shell = os.environ.get("SHELL", "/bin/sh")
        if shell.endswith("csh"):
            cmd = [
                shell,
                "-c",
                f'setenv ANTSPATH "{ants_dir}"; setenv PATH "{ants_dir}:$PATH";exec {command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]
        else:
            cmd = [
                shell,
                "-c",
                f'export ANTSPATH="{ants_dir}"; export PATH="{ants_dir}:$PATH"; exec {command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]

    return cmd


def ants_env(execution_context=None):
    """
    get ANTS env variables
    process
    """
    global ants_runtime_env

    if ants_runtime_env is not None:
        return ants_runtime_env

    if execution_context is not None:
        set_env_from_config(execution_context)

    ants_dir = os.environ.get("ANTSPATH")
    kwargs = {}

    cmd = ants_command_with_environment(["env"], use_runtime_env=False)
    new_env = subprocess.check_output(cmd, **kwargs).decode("utf-8").strip()
    new_env = parse_env_lines(new_env)
    env = {}
    for line in new_env:
        name, val = line.strip().split("=", 1)
        if name not in ("_", "SHLVL") and (
            name not in os.environ or os.environ[name] != val
        ):
            env[name] = val

    # add PATH
    if ants_dir:
        env["PATH"] = os.pathsep.join([ants_dir, os.environ.get("PATH", "")])
    # cache dict
    ants_runtime_env = env
    return env


class ANTSPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for ANTS commands
    """

    def __init__(self, command, execution_context=None, **kwargs):
        cmd = ants_command_with_environment(
            command, execution_context=execution_context
        )
        super().__init__(cmd, **kwargs)


def ants_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for ANTS commands
    """
    cmd = ants_command_with_environment(command, execution_context=execution_context)
    return subprocess.call(cmd, **kwargs)


def ants_check_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for ANTS commands
    """
    cmd = ants_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_call(cmd, **kwargs)


def ants_check_output(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for ANTS commands
    """
    cmd = ants_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_output(cmd, **kwargs)
