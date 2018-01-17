##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import logging
import six

# CAPSUL import
from capsul.study_config.memory import Memory

# TRAIT import
from traits.api import Undefined

# Define the logger
logger = logging.getLogger(__name__)


def run_process(output_dir, process_instance, cachedir=None,
                generate_logging=False, verbose=0, **kwargs):
    """ Execute a capsul process in a specific directory.

    Parameters
    ----------
    output_dir: str (mandatory)
        the folder where the process will write results.
    process_instance: Process (madatory)
        the capsul process we want to execute.
    cachedir: str (optional, default None)
        save in the cache the current process execution.
        If None, no caching is done.
    generate_logging: bool (optional, default False)
        if True save the log stored in the process after its execution.
    verbose: int
        if different from zero, print console messages.

    Returns
    -------
    returncode: ProcessResult
        contains all execution information.
    output_log_file: str
        the path to the process execution log file.
    """
    # Set the current directory directory if necessary
    if hasattr(process_instance, "_nipype_interface"):
        if "spm" in process_instance._nipype_interface_name:
            process_instance._nipype_interface.mlab.inputs.prescript += [
                "cd('{0}');".format(output_dir)]

    # Setup the process log file
    output_log_file = None
    if generate_logging and output_dir is not None and output_dir is not Undefined:
        output_log_file = os.path.join(
            os.path.basename(output_dir),
            os.path.dirname(output_dir) + ".json")
        process_instance.log_file = output_log_file

    # Check extra parameters name
    for arg_name in kwargs:
        # If the extra parameter name does not match with a user
        # trait parameter name, raise a AttributeError
        if arg_name not in process_instance.user_traits():
            raise AttributeError(
                "execution of process {0} got an unexpected keyword "
                "argument '{1}'".format(process_instance, arg_name))

    # Information message
    if verbose:
        input_parameters = {}
        for name, trait in six.iteritems(process_instance.user_traits()):
            value = process_instance.get_parameter(name)
            # Skip undefined trait attributes and outputs
            if not trait.output and value is not Undefined:
                # Store the input parameter
                input_parameters[name] = value
        input_parameters = ["{0}={1}".format(name, value)
              for name, value in six.iteritems(input_parameters)]
        call_with_inputs = "{0}({1})".format(process_instance.id, ", ".join(input_parameters))
        print("{0}\n[Process] Calling {1}...\n{2}".format(
            80 * "_", process_instance.id,
            call_with_inputs))
    if cachedir:
        # Create a memory object
        mem = Memory(cachedir)
        proxy_instance = mem.cache(process_instance, verbose=verbose)

        # Execute the proxy process
        returncode = proxy_instance(**kwargs)
    else:
        for k, v in six.iteritems(kwargs):
            setattr(process_instance, k, v)
        missing = process_instance.get_missing_mandatory_parameters()
        if len(missing) != 0:
            raise ValueError('In process %s: missing mandatory parameters: %s'
                             % (process_instance.name, ', '.join(missing)))
        process_instance._before_run_process()
        returncode = process_instance._run_process()
        returncode = process_instance._after_run_process(returncode)

    # Save the process log
    if generate_logging:
        process_instance.save_log(returncode)

    return returncode, output_log_file
