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
import collections
import json

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.trait_base import _Undefined
from traits.api import Directory, File, Bool

# Nipype import
try:
    import nipype.interfaces.matlab as matlab
    from nipype.interfaces import spm
except ImportError:
    spm = None
    matlab = None

# Soma import
from soma.controller import Controller

# Capsul import
from config_utils import find_spm, environment
from capsul.pipeline import Pipeline
from capsul.process import Process
from run import _run_process
from capsul.pipeline.pipeline_workflow import (
    workflow_from_pipeline, local_workflow_run)
from capsul.pipeline.pipeline_nodes import IterativeNode
try:
    from run_with_cache import _joblib_run_process
except ImportError:
    _joblib_run_process = None


default_config = collections.OrderedDict([
    ("spm_directory", "/i2bm/local/spm8"),
    ("matlab_exec", "/neurospin/local/bin/matlab"),
    ("fsl_config", "/etc/fsl/4.1/fsl.sh"),
    ("spm_exec_cmd", "/i2bm/local/bin/spm8"),
    ("use_spm_mcr", False),
    ("use_fsl", True)
])


class StudyConfig(Controller):
    """ Class to store the study parameters and processing options.

    This in turn is used to evaluate a Process instance or a Pipeline

    Attributes
    ----------
    `input_directory` : str
        parameter to set the study input directory
    `output_directory` : str
        parameter to set the study output directory
    `shared_directory` : dict (default None)
        parameter to set the study shared directory
    `generate_logging` : bool (default False)
        parameter to control the log generation
    `spm_directory` : str
        parameter to set the SPM directory
    `matlab_exec` : str
        parameter to set the Matlab command path
    `fsl_config` : str
        parameter to specify the fsl.sh path
    `spm_exec_cmd` : bool (default False)
        parameter to set the SPM standalone (MCR) command path
    `use_spm_mcr` : bool
        parameter to select way we execute SPM: the standalone or matlab
        version
    `use_fsl` : bool
        parameter to tell that we need to configure FSL
    `use_smart_caching` : bool (default False)
        parameter to use smart-caching during the execution
    `use_soma_workflow` : bool (default False)
        parameter to choose soma woklow for the execution

    Methods
    -------
    run
    reset_process_counter
    save_study_configuration
    update_study_configuration
    set_study_configuration
    set_trait_value
    get_trait
    get_trait_value
    _use_smart_caching_changed
    _use_spm_mcr_changed
    _use_fsl_changed
    """

    def __init__(self, init_config=None):
        """ Initilize the StudyConfig class

        Parameters
        ----------
        init_config: ordered dict (default None)
            the structure that contain the default study configuration:
            see the class attributes to build this structure.
        """
        # Intern identifier
        self.name = self.__class__.__name__

        # If no configuration are passed as argument, used the default one
        if init_config is None:
            init_config = default_config

        # Inheritance
        super(StudyConfig, self).__init__()

        # Parameter that is incremented at each process execution
        self.process_counter = 1

        # Add the study parameters
        self.add_trait("input_directory", Directory(
            _Undefined(),
            output=False,
            desc="Parameter to set the study input directory"))
        self.add_trait("output_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study output directory",
            output=False,
            exists=True))
        self.add_trait("shared_directory", Directory(
            _Undefined(),
            output=False,
            desc="Parameter to set the study shared directory",
            exists=True))
        self.add_trait("generate_logging", Bool(
            False,
            output=False,
            desc="Parameter to control the log generation"))

        # Add some dependencie parameters
        self.add_trait("spm_directory", Directory(
            _Undefined(),
            output=False,
            desc="Parameter to set the SPM directory",
            exists=True))
        self.add_trait("matlab_exec", File(
            _Undefined(),
            output=False,
            desc="Parameter to set the Matlab command path",
            exists=True))
        self.add_trait("fsl_config", File(
            _Undefined(),
            output=False,
            desc="Parameter to specify the fsl.sh path",
            exists=True))
        self.add_trait("spm_exec_cmd", File(
            _Undefined(),
            output=False,
            desc="parameter to set the SPM standalone (MCR) command path",
            exists=True))
        self.add_trait("use_spm_mcr", Bool(
            _Undefined(),
            output=False,
            desc=("Parameter to select way we execute SPM: the standalone "
                  "or matlab version")))
        self.add_trait("use_fsl", Bool(
            _Undefined(),
            output=False,
            desc="Parameter to tell that we need to configure FSL"))

        # Set the caller
        self.add_trait("use_soma_workflow", Bool(
            False,
            output=False,
            desc="Parameter to choose soma woklow for the execution"))
        self.add_trait("use_smart_caching", Bool(
            False,
            output=False,
            desc="Parameter to use smart-caching during the execution"))
        self._caller = _run_process

        # Set the study configuration
        self.set_study_configuration(init_config)

    ####################################################################
    # Methods
    ####################################################################

    def run(self, process_or_pipeline, executer_qc_nodes=False):
        """ Method to execute a process or a pipline in a study
        configuration environment.

        Parameters
        ----------
        process_or_pipeline: Process or Pipeline instance (mandatory)
            the process or pipeline we want to execute
        execute_qc_nodes: bool (optional, default False)
            if True execute process nodes that are taged as qualtity control
            process nodes.
        """
        # Use soma worflow to execute the pipeline or porcess in parallel
        # on the local machine
        if self.get_trait_value("use_soma_workflow"):

            # Create soma workflow pipeline
            workflow = workflow_from_pipeline(process_or_pipeline)
            local_workflow_run(process_or_pipeline.id, workflow)

        # Use the local machine to execute the pipeline or process
        else:

            # Generate ordered execution list
            execution_list = []
            if isinstance(process_or_pipeline, Pipeline):
                execution_list = process_or_pipeline.workflow_ordered_nodes()
            elif isinstance(process_or_pipeline, Process):
                execution_list.append(process_or_pipeline)
            else:
                raise Exception(
                    "Unknown instance type. Got {0}"
                    "and expect Process or Pipeline"
                    "instances".format(process_or_pipeline.__module__.name__))

            # Filter process nodes if necessary
            if not executer_qc_nodes:
                execution_list = [node for node in execution_list
                                  if node.node_type != "view_node"]

            # Execute each process node element
            for process_node in execution_list:

                # Special case: an iterative node
                # Execute each element of the iterative pipeline
                if isinstance(process_node, IterativeNode):

                    # Get the iterative pipeline
                    iterative_pipeline = process_node.process

                    # Generate ordered execution list
                    iterative_execution_list = (
                        iterative_pipeline.workflow_ordered_nodes())

                    # Filter process nodes if necessary
                    if not executer_qc_nodes:
                        iterative_execution_list = [
                            node for node in iterative_execution_list
                            if node.node_type != "view_node"]

                    # Execute the iterative process instances
                    for iterative_process_node in iterative_execution_list:
                        self._run(iterative_process_node.process)

                # Execute the process instance
                else:
                    self._run(process_node.process)

    def _run(self, process_instance):
        """ Method to execute a process in a study configuration environment.

        Parameters
        ----------
        process_instance: Process instance (mandatory)
            the process we want to execute
        """
        # Message
        logger.info("Study Config: executing process "
                    "'{0}'...".format(process_instance.id))

        # Run
        returncode, log_file = self._caller(
            self.output_directory,
            "{0}-{1}".format(self.process_counter,
                             process_instance.name),
            process_instance,
            self.generate_logging,
            self.spm_directory)

        # Increment the number of executed process count
        self.process_counter += 1

    def reset_process_counter(self):
        """ Method to reset the process counter to one
        """
        self.process_counter = 1

    def save_study_configuration(self, json_fname):
        """ Save study configuration as json file.

        Parameters
        ----------
        json_fname: str (mandatory)
            the path to the output json file.
        """
        # Dump the study configuration elements
        json_string = json.dumps(
            self.user_traits(), indent=4, separators=(",", ": "))

        # Write the dumped the study configuration elements
        with open(json_fname, "w") as f:
            f.write(unicode(json_string))

    def update_study_configuration(self, json_fname):
        """ Update the study configuration from a json file.

        Parameters
        ----------
        json_fname: str (mandatory)
            the path to the output json file.
        """
        # Load the json file
        with open(json_fname, "r") as json_data:
            new_config = json.load(
                json_data, object_pairs_hook=collections.OrderedDict)

        # Update the study configuration
        self.set_study_configuration(new_config)

    def add_trait(self, name, *trait):
        """ Add a new trait.

        Parameters
        ----------
        name: str (mandatory)
            the trait name.
        trait: traits.api (mandatory)
            a valid trait.
        """
        # Call the controller add_trait method
        super(StudyConfig, self).add_trait(name, *trait)

        # Get the trait instance and if it is a user trait load the traits
        # to get it in the traits accessor method that can select traits from
        # trait attributes
        trait_instance = self.trait(name)
        if self.is_user_trait(trait_instance):
            self.get(name)

    ####################################################################
    # Accessors
    ####################################################################

    def set_study_configuration(self, new_config):
        """ Method to set the new configuration of the study.

        If a study configuration element can't be updated properly,
        send an error message to the logger.

        Parameters
        ----------
        new_config: ordered dict (mandatory)
            the structure that contain the default study configuration:
            see the class attributes to build this structure.
        """
        # Go through the configuration structure
        for trait_name, trait_value in new_config.iteritems():

            # Try to update the 'trait_name' configuration element
            try:
                self.set_trait_value(trait_name, trait_value)
            except:
                logger.debug(
                    "Could not set value for config variable {0}: "
                    "{1}".format(trait_name, repr(trait_value)))

    def set_trait_value(self, trait_name, trait_value):
        """ Method to set the value of a parameter.

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to modify
        trait_value: object (madatory)
            the trait value we want to set
        """
        if trait_name in self.traits(output=False):
            setattr(self, trait_name, trait_value)

    def get_trait(self, trait_name):
        """ Method to access the 'trait_name' study configuration element.

        .. note:

            If the 'trait_name' element is not found, return None

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to access

        Returns
        -------
        trait: trait
            the trait we want to access
        """
        if trait_name in self.traits(output=False):
            return self.trait(trait_name)
        else:
            return None

    def get_trait_value(self, trait_name):
        """ Method to access the value of the 'trait_name' study
        configuration element.

        .. note:

            If the 'trait_name' element is not found, return None

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to modify

        Returns
        -------
        value: object
            the trait value we want to access
        """
        if trait_name in self.traits(output=False):
            return getattr(self, trait_name)
        else:
            return None

    ####################################################################
    # Trait callbacks
    ####################################################################

    def _use_smart_caching_changed(self, old_trait_value, new_trait_value):
        """ Event to setup the apropriate caller.
        """
        # Try to set the smart caching caller
        if new_trait_value:

            # If the smart caching caller is not defined defined, raise
            # an Exception
            if _joblib_run_process is None:
                raise Exception("The smart cahing caller is not defined, "
                                "please investigate.")
            self._caller = _joblib_run_process

        # Set the standard caller
        else:
            self._caller = _run_process

    def _use_spm_mcr_changed(self, old_trait_value, new_trait_value):
        """ Event to setup SPM environment

        We interact with spm through nipype. If the nipype spm interface
        has not been imported properly, do nothing.

        .. note :

            If the path to the spm standalone binaries are not specified,
            raise an exception.
        """
        # Set up standalone SPM version
        if new_trait_value:

            # To set up standalone SPM version, need the path to the
            # binaries
            if not isinstance(self.spm_exec_cmd, _Undefined):

                # We interact with spm through nipype. If the spm
                # interface has been imported properly, configure this
                # interface
                if spm is not None:
                    spm.SPMCommand.set_mlab_paths(
                        matlab_cmd=self.spm_exec_cmd + " run script",
                        use_mcr=True)

            # Otherwise raise an exception
            else:
                raise Exception(
                    "No SPM execution command specified. "
                    "It is impossible to configure spm stanalone version.")

        # Setup the classical matlab spm version
        else:

            # We interact with spm through nipype. If the spm
            # interface has been imported properly, configure this
            # interface
            if spm is not None:
                spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)

            # Need to set up the matlab path
            if not isinstance(self.matlab_exec, _Undefined):

                # If the smatlab interface has been imported properly,
                # configure this interface
                if matlab is not None:
                    matlab.MatlabCommand.set_default_matlab_cmd(
                        self.matlab_exec + " -nodesktop -nosplash")

            # Otherwise raise an exception
            else:
                raise Exception(
                    "No MATLAB binary specified. "
                    "It is impossible to configure the matlab spm version.")

            # Need to set up the spm path
            # If the spm directory is not specified, try to find it
            # automatically
            if isinstance(self.spm_directory, _Undefined):
                self.spm_directory = find_spm(self.matlab_exec)

            # If the smatlab interface has been imported properly,
            # configure this interface
            if matlab is not None:
                matlab.MatlabCommand.set_default_paths(self.spm_directory)

    def _use_fsl_changed(self, new_trait_value):
        """ Event tp setup FSL environment
        """
        # If the option is True
        if new_trait_value:

            # Get the fsl.sh path from the study configuration elements
            fsl_config_file = self.get_trait_value("fsl_config")

            # If the fsl.sh path has been defined
            if not isinstance(fsl_config_file, _Undefined):

                # Parse the fsl environment
                envfsl = environment(fsl_config_file)
                if (not envfsl["LD_LIBRARY_PATH"] in
                   os.environ.get("LD_LIBRARY_PATH", [])):

                    # Set the fsl environment
                    for envname, envval in envfsl.iteritems():
                        if envname in os.environ:
                            if envname.startswith("FSL"):
                                os.environ[envname] = envval
                            else:
                                os.environ[envname] += ":" + envval
                        else:
                            os.environ[envname] = envval

            # Otherwise raise an exception
            else:
                raise Exception("No FSL configuration file specified. "
                                "It is impossible to configure FSL.")


if __name__ == "__main__":

    # Test the configuration time
    import timeit

    # Standard configuration
    tic = timeit.default_timer()
    study = StudyConfig()
    toc = timeit.default_timer()
    print "Standard configuration done in  {0} s.".format(toc - tic)

    # Empty configuration
    empty_config = collections.OrderedDict([])
    tic = timeit.default_timer()
    study = StudyConfig(empty_config)
    toc = timeit.default_timer()
    print "Empty configuration done in  {0} s.".format(toc - tic)
