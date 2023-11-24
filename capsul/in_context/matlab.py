# -*- coding: utf-8 -*-
"""
Specific subprocess-like functions to call Matlab taking into account
configuration stored in ExecutionContext.
"""

import os
import subprocess
from soma.controller import undefined


def set_env_from_config(execution_context):
    """
    Set environment variables according to the
    execution context configuration.
    """
    matlab_mod = getattr(execution_context, "matlab")
    if matlab_mod:
        if matlab_mod.executable is not undefined:
            os.environ["MATLAB_EXECUTABLE"] = matlab_mod.executable
        if matlab_mod.mcr_directory is not undefined:
            os.environ["MATLAB_MCR_DIRECTORY"] = matlab_mod.mcr_directory


def matlab_command(command, execution_context=None):
    if execution_context is not None:
        set_env_from_config(execution_context)

    cmd = command
    mexe = os.environ.get("MATLAB_EXECUTABLE")
    if mexe:
        cmd = [mexe] + command[1:]
    return cmd


class MatlabPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for Matlab
    """

    def __init__(self, cmd, execution_context=None, **kwargs):
        cmd = matlab_command(cmd, execution_context=execution_context)
        super(MatlabPopen, self).__init__(cmd, **kwargs)


def matlab_call(cmd, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for Matlab
    """
    cmd = matlab_command(cmd, execution_context=execution_context)
    return subprocess.call(cmd, **kwargs)


def matlab_check_call(cmd, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for Matlab
    """
    cmd = matlab_command(cmd, execution_context=execution_context)
    return subprocess.check_call(cmd, **kwargs)


def matlab_check_output(cmd, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for Matlab
    """
    cmd = matlab_command(cmd, execution_context=execution_context)
    return subprocess.check_output(cmd, **kwargs)


if __name__ == "__main__":
    from capsul.api import Capsul
    import tempfile

    c = Capsul()
    c.config.builtin.add_module("matlab")
    c.config.builtin.matlab.directory = "/casa/matlab"
    c.config.builtin.matlab.mcr_directory = "/casa/matlab/mcr/v97"

    batch = tempfile.NamedTemporaryFile(suffix=".m")
    batch.write("fprintf(1, '%s', spm('dir'));")
    batch.flush()
    p = c.executable("nipype.interfaces.spm.Segment")
    matlab_call(
        ["matlab", batch.name], execution_context=c.engine().execution_context(p)
    )
