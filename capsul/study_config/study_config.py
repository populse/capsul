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

# Trait import
try:
    from traits.trait_base import _Undefined
    from traits.api import Directory, File, Bool
except ImportError:
    from enthought.traits.api import Directory, File, Bool

# Nipype import
try:
    import nipype.interfaces.matlab as matlab
    from nipype.interfaces import spm
except ImportError:
    spm = None
    matlab = None
    # logging.warn("Impossible to import nipype, please investigate.")

# Soma import
from soma.controller import Controller
from soma.sorted_dictionary import SortedDictionary

# Capsul import
from config_utils import find_spm, environment
from capsul.pipeline import Pipeline
from capsul.process import Process
from run import _run_process
from capsul.pipeline.pipeline_workflow import (workflow_from_pipeline,
                                               local_workflow_run)
try:
    from run_with_cache import _joblib_run_process
except ImportError:
    _joblib_run_process = None


default_config = SortedDictionary(
    ("spm_directory", "/i2bm/local/spm8"),
    ("matlab_exec", "/neurospin/local/bin/matlab"),
    ("fsl_config", "/etc/fsl/4.1/fsl.sh"),
    ("spm_exec_cmd", "/i2bm/local/bin/spm8"),
    ("use_spm_mcr", False),
    ("use_fsl", True)
)


class StudyConfig(Controller):
    """ Class to store study parameters and processing options.

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
        parameter to select the standalone or matlab SPM version to use
    `use_fsl` : bool
        parameter to tell that we need to configure FSL
    `use_smart_caching` : bool (default False)
        parameter to use smart-caching during the execution
    `use_soma_workflow` : bool (default False)
        parameter to choose soma woklow for the execution

    Methods
    -------
    run
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
            the structure that contain the default study configuration.
            Keys are in attributes.
        """
        # Intern identifier
        self.name = self.__class__.__name__

        # Update configuration
        init_config = init_config or default_config

        # Inheritance
        super(StudyConfig, self).__init__()

        # Parameter that is incremented at each execution
        self.process_counter = 1

        # Add some study parameters
        self.add_trait("input_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study input directory"))
        self.add_trait("output_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study output directory",
            exists=True))
        self.add_trait("shared_directory", Directory(
            _Undefined(),
            desc="Parameter to set the study shared directory",
            exists=True))
        self.add_trait("generate_logging", Bool(
            False,
            desc="Parameter to control the log generation"))

        # Add some dependencie parameters
        self.add_trait("spm_directory", Directory(
            _Undefined(),
            desc="Parameter to set the SPM directory",
            exists=True))
        self.add_trait("matlab_exec", File(
            _Undefined(),
            desc="Parameter to set the Matlab command path",
            exists=True))
        self.add_trait("fsl_config", File(
            _Undefined(),
            desc="Parameter to specify the fsl.sh path",
            exists=True))
        self.add_trait("spm_exec_cmd", File(
            _Undefined(),
            desc="parameter to set the SPM standalone (MCR) command path",
            exists=True))
        self.add_trait("use_spm_mcr", Bool(
            _Undefined(),
            desc=("Parameter to select the standalone or matlab SPM version "
                  "to use")))
        self.add_trait("use_fsl", Bool(
            _Undefined(),
            desc="Parameter to tell that we need to configure FSL"))

        # Set the caller
        self.add_trait("use_soma_workflow", Bool(
            False,
            desc="Parameter to choose soma woklow for the execution"))
        self.add_trait("use_smart_caching", Bool(
            False,
            desc="Parameter to use smart-caching during the execution"))
        self._caller = _run_process

        # Set configuration
        for trait_name, trait_default_value in init_config.items():
            try:
                self.set_trait_value(trait_name, trait_default_value)
            except:
                logging.info(
                    "Could not set value for config variable {0}: "
                    "{1}".format(trait_name, repr(trait_default_value)))

    ##############
    # Properties #
    ##############

    def reset_process_counter(self):
        """ Method to reset the process counter to one
        """
        self.process_counter = 1

    def set_trait_value(self, trait_name, trait_value):
        """ Method to set the value of a parameter.

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to modify
        trait_value: object (madatory)
            the trait value we want to set
        """
        setattr(self, trait_name, trait_value)

    def get_trait(self, trait_name):
        """ Method to access StudyConfig parameter.

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to access

        Returns
        -------
        trait: trait
            the trait we want to access
        """
        # TODO test if trait_name exists
        return self.trait(trait_name)

    def get_trait_value(self, trait_name):
        """ Method to access the value of a parameter.

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to modify

        Returns
        -------
        value: object
            the trait value we want to access
        """
        return getattr(self, trait_name)

    ##############
    # Events     #
    ##############

    def _use_smart_caching_changed(self, old_trait_value, new_trait_value):
        """ Event to setup the the caller
        """
        if new_trait_value:
            if _joblib_run_process is not None:
                self._caller = _joblib_run_process
            else:
                # we could issue a warning
                self._caller = _run_process
        else:
            self._caller = _run_process

    def _use_spm_mcr_changed(self, old_trait_value, new_trait_value):
        """ Event to setup SPM environment
        """
        # use compiled SPM
        if new_trait_value:
            if not isinstance(self.spm_exec_cmd, _Undefined):
                if spm is not None:
                    spm.SPMCommand.set_mlab_paths(
                        matlab_cmd=self.spm_exec_cmd + " run script",
                        use_mcr=True)
                # else: ?
            else:
                raise Exception("No SPM execution command specified. "
                                "It is impossible to configure SPM.")
        # use Matlab + SPM
        else:
            if spm is not None:
                spm.SPMCommand.set_mlab_paths(matlab_cmd="",
                                              use_mcr=False)
            # else: ?
            if not isinstance(self.matlab_exec, _Undefined):
                if matlab is not None:
                    matlab.MatlabCommand.set_default_matlab_cmd(
                        self.matlab_exec + " -nodesktop -nosplash")
                # else: ?
            else:
                raise Exception("No MATLAB binary specified. "
                                "It is impossible to configure MATLAB.")
            if isinstance(self.spm_directory, _Undefined):
                # automatic search of SPM
                self.spm_directory = find_spm(self.matlab_exec)
            if matlab is not None:
                matlab.MatlabCommand.set_default_paths(self.spm_directory)
            # else: ?

    def _use_fsl_changed(self, new_trait_value):
        """ Event tp setup FSL environment
        """
        if new_trait_value:
            fsl_config_file = self.get_trait_value('fsl_config')
            if not isinstance(fsl_config_file, _Undefined):
                envfsl = environment(fsl_config_file)
                if (not envfsl["LD_LIBRARY_PATH"] in
                   (os.environ.get("LD_LIBRARY_PATH") or [])):

                    for envname, envval in envfsl.items():
                        if envname in os.environ:
                            if envname.startswith("FSL"):
                                os.environ[envname] = envval
                            else:
                                os.environ[envname] += ":" + envval
                        else:
                            os.environ[envname] = envval
            else:
                raise Exception("No FSL configuration file specified. "
                                "It is impossible to configure FSL.")

    ##############
    # Methods    #
    ##############

    def run(self, process_or_pipeline):
        """ Function to execute a process or a pipline with the Study
        configuration

        Parameters
        ----------
        process_or_pipeline: Process or Pipeline (mandatory)
            the process or pipeline we want to execute
        """

        # Use soma worflow
        if self.get_trait_value("use_soma_workflow"):
            # Create soma workflow pipeline
            workflow = workflow_from_pipeline(process_or_pipeline)
            local_workflow_run(process_or_pipeline.id, workflow)
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

            # Execute each element
            for process_instance in execution_list:

                # Message
                logging.info("Study Config: executing process "
                             "'{0}'...".format(process_instance.id))

                # Run
                returncode, log_file = self._caller(
                    self.output_directory,
                    "{0}-{1}".format(self.process_counter,
                                     process_instance.name),
                    process_instance,
                    self.generate_logging,
                    self.spm_directory)

                # Increment
                self.process_counter += 1


if __name__ == "__main__":

    study = StudyConfig()
