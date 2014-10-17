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
import json
import sys
if sys.version_info[:2] >= (2, 7):
    from collections import OrderedDict
else:
    from soma.sorted_dictionary import SortedDictionary as OrderedDict

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import Directory, File, Bool, Instance

# Soma import
from soma.controller import Controller
from soma.undefined import undefined

# Capsul import
from capsul.pipeline import Pipeline
from capsul.process import Process
from run import _run_process
from capsul.pipeline.pipeline_workflow import (
    workflow_from_pipeline, local_workflow_run)
from capsul.pipeline.pipeline_nodes import IterativeNode

# Import built-in configuration modules
from config_modules.brainvisa_config import BrainVISAConfig
from config_modules.fsl_config import FSLConfig
from config_modules.matlab_config import MatlabConfig
from config_modules.smartcaching_config import SmartCachingConfig
from config_modules.somaworkflow_config import SomaWorkflowConfig
from config_modules.spm_config import SPMConfig


default_config = OrderedDict([
    ("spm_directory", "/i2bm/local/spm8"),
    ("matlab_exec", "/neurospin/local/bin/matlab"),
    ("fsl_config", "/etc/fsl/4.1/fsl.sh"),
    ("spm_exec_cmd", "/i2bm/local/bin/spm8"),
    ("use_spm_mcr", False),
    ("use_fsl", True)
])


class StudyConfig(Controller):
    """ Class to store the study parameters and processing options.

    This in turn is used to evaluate a Process instance or a Pipeline.

    StudyConfig has modules (see BrainVISAConfig, FSLConfig, MatlabConfig,
    SmartCachingConfig, SomaWorkflowConfig, SPMConfig, FOMConfig).
    Modules are initialized in the constructor, so their list has to be setup
    before instantiating StudyConfig.

    A default modules list is used when no modules are specified:
    StudyConfig.default_modules

    ::

      from capsul.study_config import StudyConfig
      from capsul.study_config.config_modules.fom_config import SPMConfig
      from capsul.study_config.config_modules.fom_config import FomConfig

      study_config = StudyConfig(modules=[SPMConfig, FomConfig])
      # or:
      study_config = StudyConfig(modules=StudyConfig.default_modules + [FomConfig])

      study_file = '/home/bob/study_config.json'
      study_config.update_study_configuration(study_file)


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
    """

    default_modules = [BrainVISAConfig, FSLConfig, MatlabConfig, SmartCachingConfig, SomaWorkflowConfig, SPMConfig]
    
    input_directory = Directory(
        undefined,
        output=False,
        desc="Parameter to set the study input directory")
    
    output_directory = Directory(
        undefined,
        desc="Parameter to set the study output directory",
        output=False,
        exists=True)
    
    generate_logging = Bool(
        False,
        output=False,
        desc="Parameter to control the log generation")
    
    def __init__(self, init_config=None, modules=None):
        """ Initilize the StudyConfig class

        Parameters
        ----------
        modules: list of classes (default self.default_modules).
            the configuration module classes that will be included in this 
            study configuration.
        """
        
        # Inheritance
        super(StudyConfig, self).__init__()
        
        # Create modules
        if modules is None:
            modules = self.default_modules
        self.modules = tuple(config_class(self) for config_class in modules)
        
        # Intern identifier
        self.name = self.__class__.__name__

        # Parameter that is incremented at each process execution
        self.process_counter = 1

        # Set the caller
        self._caller = _run_process

        # Set the study configuration
        # If no configuration are passed as argument, use the default one
        if init_config is None:
            init_config = default_config
        self.set_study_configuration(init_config)
        # modules_data is a container for modules-specific internal data
        # each module is encouraged to prefix its variables there by its
        # module name
        self.modules_data = Controller()

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
                json_data, object_pairs_hook=OrderedDict)

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


if __name__ == '__main__':
    # Test the configuration time
    import timeit

    # Standard configuration
    tic = timeit.default_timer()
    study = StudyConfig()
    toc = timeit.default_timer()
    print "Standard configuration done in  {0} s.".format(toc - tic)

    # Empty configuration
    empty_config = OrderedDict([])
    tic = timeit.default_timer()
    study = StudyConfig(empty_config)
    toc = timeit.default_timer()
    print "Empty configuration done in  {0} s.".format(toc - tic)

