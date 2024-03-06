"""
Specific subprocess-like functions to call FSL taking into account
configuration stored in ExecutionContext.
::

    from capsul.api import Process
    from capsul.in_context.fsl import fsl_check_call

    ce = Capsul()
    # .. configure it ...
    Class MyProcess(Process):

        # [declare fields etc] ...

        def execute(self, execution_context):
            fsl_check_call(['bet', '-h'], execution_context=execution_context)

For calling FSL command with this module, the first argument of
command line must be the FSL executable without any path nor prefix.
Prefix are used in Neurodebian install. For instance on Ubuntu 16.04
Neurodebian FSL commands are prefixed with "fsl5.0-".
The appropriate path and eventually prefix are added from the configuration
of the ExecutionContext.

Alternatively, without an ExecutionContext object, if environment variables are
properly set, the functions will use:

- FSL_PREFIX
- FSLDIR
- FSL_CONFIG
"""

import os
import os.path as osp
import subprocess

from soma.controller import undefined
from soma.utils.env import parse_env_lines

"""
If this variable is set, it contains FSL runtime env variables, allowing to run
directly FSL commands from this process.
"""
fsl_runtime_env = None


def set_env_from_config(execution_context):
    """
    Set environment variables FSLDIR, FSL_CONFIG, FSL_PREFIX according to the
    execution context configuration.
    """
    fsl_mod = getattr(execution_context, "fsl", None)
    if fsl_mod:
        if fsl_mod.directory is not undefined:
            os.environ["FSLDIR"] = fsl_mod.directory
        if fsl_mod.setup_script is not undefined:
            os.environ["FSL_CONFIG"] = fsl_mod.setup_script
        if fsl_mod.prefix is not undefined:
            os.environ["FSL_PREFIX"] = fsl_mod.prefix


def fsl_command_with_environment(
    command, execution_context=None, use_prefix=True, use_runtime_env=True
):
    """
    Given an FSL command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the FSL configuration stored in the
    activated ExecutionContext.

    Using :func:`fsl_env` is an alternative to this.
    """
    if execution_context is not None:
        set_env_from_config(execution_context)

    if use_prefix:
        fsl_prefix = os.environ.get("FSL_PREFIX", "")
    else:
        fsl_prefix = ""
    if use_runtime_env and fsl_runtime_env:
        c0 = list(osp.split(command[0]))
        c0[-1] = "%s%s" % (fsl_prefix, c0[-1])
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    fsl_dir = os.environ.get("FSLDIR")
    if fsl_dir:
        dir_prefix = "%s/bin/" % fsl_dir
    else:
        dir_prefix = ""
    fsl_config = os.environ.get("FSL_CONFIG")
    if fsl_prefix and not os.path.isdir(dir_prefix):
        dir_prefix = ""

    if fsl_config:
        fsldir = osp.dirname(osp.dirname(osp.dirname(fsl_config)))
        shell = os.environ.get("SHELL", "/bin/sh")
        if shell.endswith("csh"):
            cmd = [
                shell,
                "-c",
                f'setenv FSLDIR "{fsldir}"; setenv PATH "{fsldir}/bin:$PATH"; source {fsldir}/etc/fslconf/fsl.csh;exec {fsl_prefix}{command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]
        else:
            cmd = [
                shell,
                "-c",
                f'export FSLDIR="{fsldir}"; export PATH="{fsldir}/bin:$PATH"; . {fsldir}/etc/fslconf/fsl.sh;exec {fsl_prefix}{command[0]} '
                + " ".join("'%s'" % i.replace("'", "\\'") for i in command[1:]),
            ]
    else:
        cmd = ["%s%s%s" % (dir_prefix, fsl_prefix, command[0])] + command[1:]
    return cmd


def fsl_env(execution_context=None):
    """
    get FSL env variables by running the setup script in a separate bash
    process
    """
    global fsl_runtime_env

    if fsl_runtime_env is not None:
        return fsl_runtime_env

    if execution_context is not None:
        set_env_from_config(execution_context)

    fsl_config = os.environ.get("FSL_CONFIG")
    fsl_dir = os.environ.get("FSLDIR")
    kwargs = {}
    if not fsl_config:
        cmd = ["env"]
        if fsl_dir:
            kwargs = {
                "env": {
                    "PATH": os.pathsep.join(
                        ["%s/bin" % fsl_dir, os.environ.get("PATH", "")]
                    )
                }
            }
    else:
        cmd = fsl_command_with_environment(
            ["env"], use_prefix=False, use_runtime_env=False
        )
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
    if fsl_dir:
        fsl_bin = osp.join(fsl_dir, "bin")
        env["PATH"] = os.pathsep.join([fsl_bin, os.environ.get("PATH", "")])
    # cache dict
    fsl_runtime_env = env
    return env


class FslPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for FSL commands
    """

    def __init__(self, command, execution_context=None, **kwargs):
        cmd = fsl_command_with_environment(command, execution_context=execution_context)
        env = fsl_env()  # execution_context is not needed any longer
        # since global env variables have been set
        if "env" in kwargs:
            env = dict(env)
            env.update(kwargs["env"])
            kwargs = dict(kwargs)
            del kwargs["env"]
        super().__init__(cmd, env=env, **kwargs)


def fsl_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for FSL commands
    """
    cmd = fsl_command_with_environment(command, execution_context=execution_context)
    env = fsl_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.call(cmd, env=env, **kwargs)


def fsl_check_call(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for FSL commands
    """
    cmd = fsl_command_with_environment(command, execution_context=execution_context)
    env = fsl_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.check_call(cmd, env=env, **kwargs)


def fsl_check_output(command, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for FSL commands
    """
    cmd = fsl_command_with_environment(command, execution_context=execution_context)
    env = fsl_env()
    if "env" in kwargs:
        env = dict(env)
        env.update(kwargs["env"])
        kwargs = dict(kwargs)
        del kwargs["env"]
    return subprocess.check_output(cmd, env=env, **kwargs)
