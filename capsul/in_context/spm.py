"""
Specific subprocess-like functions to call SPM taking into account
configuration stored in ExecutionContext.
"""

import glob
import os
import os.path as osp
import subprocess

from soma.controller import undefined


def set_env_from_config(execution_context):
    """
    Set environment variables according to the
    execution context configuration.
    """
    spm_mod = getattr(execution_context, "spm", None)
    if spm_mod:
        if spm_mod.directory is not undefined:
            os.environ["SPM_DIRECTORY"] = spm_mod.directory
        if spm_mod.standalone is not undefined:
            os.environ["SPM_STANDALONE"] = str(int(spm_mod.standalone))
        from . import matlab

        matlab.set_env_from_config(execution_context)


def spm_command(spm_batch_filename, execution_context=None):
    if execution_context is not None:
        set_env_from_config(execution_context)

    if os.environ.get("SPM_STANDALONE") == "yes":
        if spm_batch_filename is not None:
            # Check that batch file exists and raise appropriate error if
            # not
            open(spm_batch_filename)
        spm_directory = os.environ.get("SPM_DIRECTORY", "")
        mcr_dir = os.environ.get("MCR_HOME")
        if mcr_dir is None:
            mcr_glob = osp.join(spm_directory, "mcr", "v*")
            mcr_dir = glob.glob(mcr_glob)
            if not mcr_dir:
                raise ValueError("Cannot find Matlab MCR dir: %s" % mcr_glob)
            mcr_dir = mcr_dir[0]
        if spm_batch_filename is not None:
            print("---- BATCH SMP ----")
            print(open(spm_batch_filename).read())
            print("-------------------")
        cmd = [
            osp.join(spm_directory, "run_spm%s.sh" % os.environ.get("SPM_VERSION", "")),
            mcr_dir,
        ]
        if spm_batch_filename is not None:
            cmd += ["batch", spm_batch_filename]
    else:
        raise NotImplementedError("Running SPM with matlab is not implemented yet")
    return cmd


class SPMPopen(subprocess.Popen):
    """
    Equivalent to Python subprocess.Popen for SPM batch
    """

    def __init__(self, spm_batch_filename, execution_context=None, **kwargs):
        cmd = spm_command(spm_batch_filename, execution_context=execution_context)
        super().__init__(cmd, **kwargs)


def spm_call(spm_batch_filename, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.call for SPM batch
    """
    cmd = spm_command(spm_batch_filename, execution_context=execution_context)
    return subprocess.call(cmd, **kwargs)


def spm_check_call(spm_batch_filename, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_call for SPM batch
    """
    cmd = spm_command(spm_batch_filename, execution_context=execution_context)
    return subprocess.check_call(cmd, **kwargs)


def spm_check_output(spm_batch_filename, execution_context=None, **kwargs):
    """
    Equivalent to Python subprocess.check_output for SPM batch
    """
    cmd = spm_command(spm_batch_filename, execution_context=execution_context)
    return subprocess.check_output(cmd, **kwargs)
