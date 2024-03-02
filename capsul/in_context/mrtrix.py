# -*- coding: utf-8 -*-
"""
Specific subprocess-like functions to call mrtrix taking into account
configuration stored in ExecutionContext.
"""

import os
import os.path as osp
import subprocess

from soma.controller import undefined
from soma.utils.env import parse_env_lines

mrtrix_runtime_env = None


def set_env_from_config(execution_context):
    """
    Set environment variables according to the
    execution context configuration.
    """
    mrtrix_mod = getattr(execution_context, "mrtrix", None)
    if mrtrix_mod:
        if mrtrix_mod.directory is not undefined:
            os.environ["MRTRIXPATH"] = mrtrix_mod.directory


def mrtrix_command_with_environment(
    command, execution_context=None, use_runtime_env=True
):
    """
    Given an mrtrix command where first element is a command name without
    any path. Returns the appropriate command to call taking into account
    the mrtrix configuration stored in the
    activated ExecutionContext.
    """

    if execution_context is not None:
        set_env_from_config(execution_context)

    if use_runtime_env and mrtrix_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    mrtrix_dir = os.environ.get("MRTRIXPATH")
    cmd = command
    if mrtrix_dir:
        shell = os.environ.get("SHELL", "/bin/sh")
        if shell.endswith("csh"):
            cmd = [
                shell,
                "-c",
                'setenv MRTRIXPATH "{0}"; setenv PATH "{0}:$PATH";exec {1} '.format(
                    mrtrix_dir, command[0]
                )
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]
        else:
            cmd = [
                shell,
                "-c",
                'export MRTRIXPATH="{0}"; export PATH="{0}:$PATH"; exec {1} '.format(
                    mrtrix_dir, command[0]
                )
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]

    return cmd


def mrtrix_env(execution_context=None):
    """
    get mrtrix env variables
    process
    """
    global mrtrix_runtime_env

    if mrtrix_runtime_env is not None:
        return mrtrix_runtime_env

    if execution_context is not None:
        set_env_from_config(execution_context)

    mrtrix_dir = os.environ.get("MRTRIXPATH")
    kwargs = {}

    cmd = mrtrix_command_with_environment(["env"], use_runtime_env=False)
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
    if mrtrix_dir:
        env["PATH"] = os.pathsep.join([mrtrix_dir, os.environ.get("PATH", "")])
    # cache dict
    mrtrix_runtime_env = env
    return env


class MrtrixPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for mrtrix commands
    """

    def __init__(self, command, execution_context=None, **kwargs):
        cmd = mrtrix_command_with_environment(
            command, execution_context=execution_context
        )
        super(MrtrixPopen, self).__init__(cmd, **kwargs)


def mrtrix_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for mrtrix commands
    """
    cmd = mrtrix_command_with_environment(command, execution_context=execution_context)
    return subprocess.call(cmd, **kwargs)


def mrtrix_check_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for mrtrix commands
    """
    cmd = mrtrix_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_call(cmd, **kwargs)


def mrtrix_check_output(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for mrtrix commands
    """
    cmd = mrtrix_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_output(cmd, **kwargs)
