#! /usr/bin/env python
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

# CAPSUL import
from capsul.study_config.memory import Memory

# TRAIT import
from traits.api import Undefined

# Define the logger
logger = logging.getLogger(__name__)


def run_process(output_dir, process_instance, cachedir=None,
                generate_logging=False, verbose=1, **kwargs):
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
    # Guarantee that the output directory exists
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Update the instance output directory trait before execution
    if output_dir is not Undefined:
        if "output_directory" in process_instance.user_traits():
            process_instance.output_directory = output_dir

    # Setup the process log file
    output_log_file = None
    if generate_logging:
        output_log_file = os.path.join(
            os.path.basename(output_dir),
            os.path.dirname(output_dir) + ".json")
        process_instance.log_file = output_log_file

    # Create a memory object
    mem = Memory(cachedir)
    proxy_instance = mem.cache(process_instance, verbose=verbose)

    # Execute the proxy process
    returncode = proxy_instance(**kwargs)

    # Save the process log
    if generate_logging:
        process_instance.save_log(returncode)

    return returncode, output_log_file
