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
import string

# spm copy tools
from spm_cache_utils import local_map, last_timestamp
from soma.path import ensure_is_dir

# capsul
from run import set_output_dir
from capsul.process import ProcessResult

# joblib caching
from joblib import Memory
from joblib.func_inspect import filter_args, get_func_code

spm_interface_modules = ("nipype.interfaces.spm", "caps.nipype_interfaces.spm")


def _joblib_run_process(subj_output_dir, description, process_instance,
                        generate_logging, spm_dir):
    """ Use joblib smart-caching.
    Deal with files and SPM nipype processes.
    Do not check if files have been deleted by any users or scripts
    """
    # smart-caching directory
    cleanup_table = string.maketrans('()\\/:*?"<>| \t\r\n\0',
                                     '________________')
    name = description.lower().translate(cleanup_table)
    subj_output_dir = os.path.join(subj_output_dir, name)
    ensure_is_dir(subj_output_dir)

    # instance parameters
    # set before execution to prevent instance modification after the
    # call
    # update process instance output dir
    set_output_dir(subj_output_dir, process_instance, spm_dir)
    # set log file name
    if generate_logging:
        output_log_file = os.path.join(subj_output_dir, description + ".json")
        process_instance.log_file = output_log_file   
    
    # init smart-caching with joblib
    mem = Memory(cachedir=subj_output_dir, verbose=2)

    # copy : bool : copy all files (used when image headers are modified)
    copy = False
    if process_instance.id.startswith(spm_interface_modules):
        copy = True

    # first get input file modified times
    inputs = {}
    for name, trait in process_instance.user_traits().iteritems():
        if not trait.output:
            inputs[name] = process_instance.get_parameter(name)

    last_modified_file = last_timestamp(inputs)

    if copy:
        # update function arguments : Symbolic links
        local_inputs = local_map(inputs, subj_output_dir, False)
    else:
        local_inputs = inputs.copy()

    # now update process inputs
    for trait_name, trait_value in local_inputs.iteritems():
        #if trait_ids(process_instance.trait(trait_name)), trait_value
        if trait_value:
            setattr(process_instance, trait_name, trait_value)

    # interface smart-caching with joblib
    _mprocess = mem.cache(process_instance.__call__)

    # find and update joblib smart-caching directory
    output_dir, argument_hash = _mprocess.get_output_dir()
    if os.path.exists(output_dir):
        cache_time = os.path.getmtime(output_dir)
        # call the joblib clear function if necessary to deal with
        # files on disk
        if cache_time < last_modified_file:
            _mprocess.clear()
    else:
        # restrain joblib to one directory to handle output files on disk
        to_remove = [os.path.join(_mprocess._get_func_dir(), x)
            for x in os.listdir(_mprocess._get_func_dir())
            if os.path.isdir(os.path.join(_mprocess._get_func_dir(), x))]
        for joblib_folder in to_remove:
            shutil.rmtree(joblib_folder)

    # clean the output directory and copy the input files if requested
    is_memorized = (_mprocess._check_previous_func_code(stacklevel=3) and
                    os.path.exists(output_dir))
    if copy and not is_memorized:
        to_delete = [os.path.join(subj_output_dir, x)
                     for x in os.listdir(subj_output_dir)]
        for item in to_delete:
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.remove(item)
        local_map(inputs, subj_output_dir, True)

    # call interface
    outputs = _mprocess()

    # Ensure that the func_code.py is written in the cache
    # Not necessary with joblib version < 8
    func_code, source_file, first_line = get_func_code(_mprocess.func)
    func_dir = _mprocess._get_func_dir()
    func_code_file = os.path.join(func_dir, "func_code.py")
    _mprocess._write_func_code(func_code_file, func_code, first_line)

    # for Process, need to set the class instance attributes returned
    if isinstance(outputs, ProcessResult):
        for trait_name, trait_value in outputs.outputs.iteritems():
            setattr(process_instance, trait_name, trait_value)

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

    # generate log
    output_log_file = None
    if generate_logging:
        process_instance.save_log(outputs)

    # remove symbolic links
    to_delete = [os.path.join(subj_output_dir, x)
                  for x in os.listdir(subj_output_dir)
                  if os.path.islink(os.path.join(subj_output_dir, x))]
    for item in to_delete:
        os.unlink(item)

    # return the output interface information
    return outputs, output_log_file
