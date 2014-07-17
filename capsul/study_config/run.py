#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# python system modules
import os
import shutil

# traits
from traits.trait_base import _Undefined


def set_output_dir(subj_output_dir, process_instance, spm_dir):
    """ Try to set the study output directory
    """
    if not isinstance(subj_output_dir, _Undefined):
        # nipype setup
        if "_nipype_interface" in dir(process_instance):
            process_instance._nipype_interface.inputs.output_directory = (
                subj_output_dir)
            if "spm" in process_instance._nipype_interface_name:
                process_instance._nipype_interface.mlab.inputs.prescript = [
                    "ver,", "try,", "addpath('{0}');".format(spm_dir),
                    "cd('{0}');".format(subj_output_dir)]
            elif process_instance._nipype_interface_name == "dcm2nii":
                process_instance.output_dir = subj_output_dir
                trait = process_instance._nipype_interface.inputs.trait(
                    "output_dir")
                trait.genfile = False
                trait = process_instance._nipype_interface.inputs.trait(
                    "config_file")
                trait.genfile = False

        if "output_directory" in process_instance.user_traits():
            process_instance.output_directory = subj_output_dir


def _run_process(subj_output_dir, description, process_instance,
                 generate_logging, spm_dir):
    """ Execute the process
    """
    # First set instance parameters
    set_output_dir(subj_output_dir, process_instance, spm_dir)
    if generate_logging:
        output_log_file = os.path.join(subj_output_dir, description + ".json")
        process_instance.log_file = output_log_file
    returncode = process_instance()

    # generate some log
    output_log_file = None
    if generate_logging:
        output_log_file = os.path.join(subj_output_dir, description + ".json")
        process_instance.log_file = output_log_file
        process_instance.save_log(returncode)

    # for spm, need to move the batch
    # (create in cwd: cf nipype.interfaces.matlab.matlab l.181)
    if ("_nipype_interface" in dir(process_instance) and
        process_instance._nipype_interface_name == "spm"):
            mfile = os.path.join(os.getcwd(),
                process_instance._nipype_interface.mlab.inputs.script_file)
            n_mfile = os.path.join(subj_output_dir,
                process_instance._nipype_interface.mlab.inputs.script_file)
            if os.path.isfile(mfile):
                shutil.move(mfile, n_mfile)

    return returncode, output_log_file

