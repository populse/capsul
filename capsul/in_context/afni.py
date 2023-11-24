# -*- coding: utf-8 -*-
"""
Specific subprocess-like functions to call AFNI taking into account
configuration stored in ExecutionContext.For instance::

    from capsul.engine import Capsul
    from capsul.in_context.afni import afni_check_call

    c = Capsul(user_file='my_config.json')
    p = c.executable('nipype.interfaces.afni.preprocess.Automask')
    ce = c.engine().execution_context(p)
    afni_check_call(['afni_comamnd', '/somewhere/myimage.nii'])

For calling AFNI command with this module, the first argument of
command line must be the AFNI executable without any path.
The appropriate path is added from the configuration
of the ExecutionContext.
"""

import os
import os.path as osp
import subprocess
from soma.utils.env import parse_env_lines
from soma.controller import undefined


afni_runtime_env = None


def set_env_from_config(execution_context):
    """
    Set environment variables FSLDIR, FSL_CONFIG, FSL_PREFIX according to the
    execution context configuration.
    """
    afni_mod = getattr(execution_context, "afni", None)
    if afni_mod:
        if afni_mod.directory is not undefined:
            os.environ["AFNIPATH"] = afni_mod.directory


def afni_command_with_environment(
    command, execution_context=None, use_runtime_env=True
):
    """
    Given an AFNI command where first element is a command name without
    any path. Returns the appropriate command to call taking into account
    the AFNI configuration stored in the
    activated ExecutionContext.
    """

    if execution_context is not None:
        set_env_from_config(execution_context)

    if use_runtime_env and afni_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    afni_dir = os.environ.get("AFNIPATH")
    cmd = command
    if afni_dir:
        shell = os.environ.get("SHELL", "/bin/sh")
        if shell.endswith("csh"):
            cmd = [
                shell,
                "-c",
                'setenv AFNIPATH "{0}"; setenv PATH "{0}:$PATH";exec {1} '.format(
                    afni_dir, command[0]
                )
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]
        else:
            cmd = [
                shell,
                "-c",
                'export AFNIPATH="{0}"; export PATH="{0}:$PATH"; exec {1} '.format(
                    afni_dir, command[0]
                )
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]

    return cmd


def afni_env(execution_context=None):
    """
    get AFNI env variables
    process
    """
    global afni_runtime_env

    if afni_runtime_env is not None:
        return afni_runtime_env

    if execution_context is not None:
        set_env_from_config(execution_context)

    afni_dir = os.environ.get("AFNIPATH")
    kwargs = {}

    cmd = afni_command_with_environment(["env"], use_runtime_env=False)
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
    if afni_dir:
        env["PATH"] = os.pathsep.join([afni_dir, os.environ.get("PATH", "")])
    # cache dict
    afni_runtime_env = env
    return env


class AFNIPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for AFNI commands
    """

    def __init__(self, command, execution_context=None, **kwargs):
        cmd = afni_command_with_environment(
            command, execution_context=execution_context
        )
        super(AFNIPopen, self).__init__(cmd, **kwargs)


def afni_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for AFNI commands
    """
    cmd = afni_command_with_environment(command, execution_context=execution_context)
    return subprocess.call(cmd, **kwargs)


def afni_check_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for AFNI commands
    """
    cmd = afni_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_call(cmd, **kwargs)


def afni_check_output(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for AFNI commands
    """
    cmd = afni_command_with_environment(command, execution_context=execution_context)
    return subprocess.check_output(cmd, **kwargs)
