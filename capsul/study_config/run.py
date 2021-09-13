# -*- coding: utf-8 -*-
'''
Process and pipeline execution management

Functions
=========
:func:`run_process`
-------------------
'''

# System import
from __future__ import absolute_import
from __future__ import print_function
import errno
import os
import logging
import six

# CAPSUL import
from capsul.study_config.memory import Memory
from capsul.process.process import Process

# TRAIT import
from traits.api import Undefined, File, Directory

# Define the logger
logger = logging.getLogger(__name__)


def run_process(output_dir, process_instance,
                generate_logging=False, verbose=0, configuration_dict=None,
                cachedir=None,
                **kwargs):
    """ Execute a capsul process in a specific directory.

    Parameters
    ----------
    output_dir: str (mandatory)
        the folder where the process will write results.
    process_instance: Process (mandatory)
        the capsul process we want to execute.
    cachedir: str (optional, default None)
        save in the cache the current process execution.
        If None, no caching is done.
    generate_logging: bool (optional, default False)
        if True save the log stored in the process after its execution.
    verbose: int
        if different from zero, print console messages.
    configuration_dict: dict (optional)
        configuration dictionary

    Returns
    -------
    returncode: ProcessResult
        contains all execution information.
    output_log_file: str
        the path to the process execution log file.
    """
    # Message
    logger.info("Study Config: executing process '{0}'...".format(
        process_instance.id))

    study_config = process_instance.get_study_config()

    if configuration_dict is None:
        configuration_dict \
            = process_instance.check_requirements('global')

    # create directories for outputs
    if study_config.create_output_directories:
        for name, trait in process_instance.user_traits().items():
            if trait.output and isinstance(trait.handler, (File, Directory)):
                value = getattr(process_instance, name)
                if value is not Undefined and value:
                    base = os.path.dirname(value)
                    if base and not os.path.exists(base):
                        try:
                            os.makedirs(base)
                        except OSError as err:
                            if err.errno != errno.EEXIST:
                                raise
                            # We have a race condition?
                            pass

    if configuration_dict is None:
        configuration_dict = {}
    # clear activations for now.
    from capsul import engine
    engine.activated_modules = set()
    #print('activate config:', configuration_dict)
    engine.activate_configuration(configuration_dict)

    # Run
    if study_config.get_trait_value("use_smart_caching") in [None, False]:
        cachedir = None
    elif cachedir is None:
        cachedir = output_dir

    # Update the output directory folder if necessary
    if output_dir not in (None, Undefined) and output_dir:
        if study_config.process_output_directory:
            output_dir = os.path.join(output_dir, '%s-%s' % (study_config.process_counter, process_instance.name))
        # Guarantee that the output directory exists
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        if study_config.process_output_directory:
            if 'output_directory' in process_instance.user_traits():
                if (process_instance.output_directory is Undefined or
                        not(process_instance.output_directory)):
                    process_instance.output_directory = output_dir

    # Set the current directory directory if necessary
    if hasattr(process_instance, "_nipype_interface"):
        if "spm" in process_instance._nipype_interface_name:
            process_instance._nipype_interface.mlab.inputs.prescript += [
                "cd('{0}');".format(output_dir)]

    # Setup the process log file
    output_log_file = None
    if generate_logging and output_dir not in (None, Undefined):
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
        input_parameters = ["{0}={1}".format(n, v)
                            for n, v in six.iteritems(input_parameters)]
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

    # Increment the number of executed process count
    study_config.process_counter += 1

    return returncode, output_log_file
