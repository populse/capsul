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
from traits.api import Directory, Bool, String, Undefined

# Soma import
from soma.controller import Controller

# Capsul import
from capsul.pipeline import Pipeline
from capsul.process import Process
from run import run_process
from capsul.pipeline.pipeline_workflow import (
    workflow_from_pipeline, local_workflow_run)
from capsul.pipeline.pipeline_nodes import Node


class StudyConfig(Controller):
    """ Class to store the study parameters and processing options.

    This in turn is used to evaluate a Process instance or a Pipeline.

    StudyConfig has modules (see BrainVISAConfig, FSLConfig, MatlabConfig,
    SmartCachingConfig, SomaWorkflowConfig, SPMConfig, FOMConfig).
    Modules are initialized in the constructor, so their list has to be setup
    before instantiating StudyConfig. A default modules list is used when no
    modules are specified: StudyConfig.default_modules

    StudyConfig configuration is loaded from a global file and then from a
    study specific file (based on study_name parameter). The global
    configuration file name is either in os.environ['CAPSUL_CONFIG'] or
    in "~/.config/capsul/config.json". The study specific configuration
    file name is either defined in the global configuration or in
    "~/.config/capsul/<study_name>/config.json".
    ::

      from capsul.study_config import StudyConfig

      study_config = StudyConfig(modules=['SPMConfig', 'FomConfig'])
      # or:
      study_config = StudyConfig(modules=StudyConfig.default_modules +
      ['FomConfig'])


    Attributes
    ----------
    `input_directory` : str
        parameter to set the study input directory
    `output_directory` : str
        parameter to set the study output directory
    `generate_logging` : bool (default False)
        parameter to control the log generation

    Methods
    -------
    run
    reset_process_counter
    set_trait_value
    get_trait
    get_trait_value
    update_study_configuration
    set_study_configuration
    """

    default_modules = ['FSLConfig', 'MatlabConfig', 'SmartCachingConfig',
                       'SomaWorkflowConfig', 'SPMConfig']
    _user_config_directory = os.path.join("~", ".config", "capsul")

    study_name = String(
        None,
        desc="Name of the study to configure",
        # traits with transient=True will not be saved in configuration
        # see  http://code.enthought.com/projects/traits/docs/html/
        # traits_user_manual/advanced.html#pickling-hastraits-objects
        transient=True)

    input_directory = Directory(
        Undefined,
        desc="Parameter to set the study input directory")

    output_directory = Directory(
        Undefined,
        desc="Parameter to set the study output directory")

    generate_logging = Bool(
        False,
        desc="Parameter to control the log generation")

    automatic_configuration = Bool(
        False,
        desc="If True, tries to automatically setup configuration on startup")

    def __init__(self, study_name=None, init_config=None, modules=None,
                 **override_config):
        """ Initilize the StudyConfig class

        Parameters
        ----------
        study_name: Name of the study to configure. This name is used to
            identify specific configuration for a study.
        init_config: if not None, must contain a dictionary that will be used
            to configure this StudyConfig (instead of reading configuration
            from configuration files).
        modules: list of string (default self.default_modules).
            the names of configuration module classes that will be included
            in this study configuration.
        override_config: dictionary
            The content of these keyword parameters will be set on the
            configuration after it has been initialized from configuration
            files (or from init_config).
        """

        # Inheritance
        super(StudyConfig, self).__init__()

        if study_name:
            self.study_name = study_name

        # Read the configuration for the given study
        if init_config is None:
            config = self.read_configuration()
            config.update(override_config)
        else:
            self.global_config_file = None
            self.study_config_file = None
            if override_config:
                config = init_config.copy()
                config.update(override_config)
            else:
                config = init_config

        # Create modules
        if modules is None:
            # Make it possible for a study to define its own set of modules
            modules = config.pop('config_modules', self.default_modules)

        # 'modules_data' is a container for modules-specific internal data
        # each module is encouraged to prefix its variables there by its
        # module name
        self.modules_data = Controller()

        self.modules = {}
        for module in modules:
            self.load_module(module, config)

        # Set self attributes according to configuration values
        for k, v in config.iteritems():
            setattr(self, k, v)
        self.initialize_modules()

    def initialize_modules(self):
        """
        Modules initialization, calls initialize_module on each config module.
        This is not done during module instanciation to allow interactions
        between modules (e.g. Matlab configuration can influence Nipype
        configuration). Modules dependencies are taken into account in
        initialization.
        """
        already_initialized = set()
        # Use a stack to allow to manage module dependencies
        stack = self.modules.keys()
        while stack:
            module_name = stack.pop(0)
            if module_name in already_initialized:
                continue
            module = self.modules.get(module_name)
            if not module:
                raise EnvironmentError('Required StudyConfig module %s is '
                                       'missing' % module_name)
            # Check if there are dependent modules that must be initilaized
            # before the current one
            initialize_first = [m for m in module.dependencies
                                if m not in already_initialized]
            if initialize_first:
                stack = initialize_first + [module_name] + stack
                continue
            # Intitialize a module
            module.initialize_module()
            module.initialize_callbacks()
            already_initialized.add(module_name)

        # Intern identifier
        self.name = self.__class__.__name__

        # Parameter that is incremented at each process execution
        self.process_counter = 1

    ####################################################################
    # Methods
    ####################################################################

    def load_module(self, config_module_name, config):
        """
        Load an optional StudyConfig module.

        Parameters
        ----------
        config_module_name: Name of the module to load (e.g. "FSLConfig").
        config: dictionary containing the configuration of the study.
        """
        if config_module_name not in self.modules:
            python_module = (
                "capsul.study_config.config_modules.{0}_config".format(
                    config_module_name[:-6].lower()))
            python_module = __import__(python_module,
                                       fromlist=[config_module_name])
            config_module_class = getattr(python_module, config_module_name)
            module = config_module_class(self, config)
            self.modules[config_module_name] = module
            return module

    def run(self, process_or_pipeline, executer_qc_nodes=True, verbose=1,
            **kwargs):
        """ Method to execute a process or a pipline in a study configuration
         environment.

         Only pipeline nodes can be filtered on the 'executer_qc_nodes'
         attribute.

         A valid output directory is exepcted to execute the process or the
         pepeline without soma-workflow.

        Parameters
        ----------
        process_or_pipeline: Process or Pipeline instance (mandatory)
            the process or pipeline we want to execute
        execute_qc_nodes: bool (optional, default False)
            if True execute process nodes that are taged as qualtity control
            process nodes.
        verbose: int
            if different from zero, print console messages.
        """
        # Use soma worflow to execute the pipeline or porcess in parallel
        # on the local machine
        if self.get_trait_value("use_soma_workflow"):

            # Create soma workflow pipeline
            workflow = workflow_from_pipeline(process_or_pipeline)
            controller, wf_id = local_workflow_run(process_or_pipeline.id,
                                                   workflow)
            workflow_status = controller.workflow_status(wf_id)
            elements_status = controller.workflow_elements_status(wf_id)
            # FIXME: it would be better if study_config does not require
            # soma_workflow modules.
            from soma_workflow import constants as swconstants
            self.failed_jobs = [
                element for element in elements_status[0]
                if element[1] != swconstants.DONE
                or element[3][0] != swconstants.FINISHED_REGULARLY]
            # if execution was OK, delete the workflow
            if workflow_status == swconstants.WORKFLOW_DONE \
                    and len(self.failed_jobs) == 0:
                controller.delete_workflow(wf_id)
            else:
                # something went wrong: return the controller and workflow id
                # so that one can handle them if needed
                # WARNING: return values not very consistent. We should find
                # a better way to return the status.
                return controller, wf_id

        # Use the local machine to execute the pipeline or process
        else:

            # Check the output directory is valid
            if (self.output_directory is Undefined or
                    not isinstance(self.output_directory, basestring)):
                raise ValueError(
                    "'{0}' is not a valid directory. A valid output "
                    "directory is expected to run the process or "
                    "pipeline.".format(self.output_directory))
            try:
                if not os.path.isdir(self.output_directory):
                    os.makedirs(self.output_directory)
            except:
                raise ValueError(
                    "Can't create folder '{0}', please investigate.".format(
                        self.output_directory))

            # Generate ordered execution list
            execution_list = []
            if isinstance(process_or_pipeline, Pipeline):
                execution_list = process_or_pipeline.workflow_ordered_nodes()
                # Filter process nodes if necessary
                if not executer_qc_nodes:
                    execution_list = [node for node in execution_list
                                      if node.node_type != "view_node"]
            elif isinstance(process_or_pipeline, Process):
                execution_list.append(process_or_pipeline)
            else:
                raise Exception(
                    "Unknown instance type. Got {0}and expect Process or "
                    "Pipeline instances".format(
                        process_or_pipeline.__module__.name__))

            # Execute each process node element
            for process_node in execution_list:
                # Execute the process instance contained in the node
                if isinstance(process_node, Node):
                    self._run(process_node.process, verbose, **kwargs)

                # Execute the process instance
                else:
                    self._run(process_node, verbose, **kwargs)

    def _run(self, process_instance, verbose, **kwargs):
        """ Method to execute a process in a study configuration environment.

        Parameters
        ----------
        process_instance: Process instance (mandatory)
            the process we want to execute
        verbose: int
            if different from zero, print console messages.
        """
        # Message
        logger.info("Study Config: executing process '{0}'...".format(
            process_instance.id))

        # Run
        destination_folder = os.path.join(
            self.output_directory,
            "{0}-{1}".format(self.process_counter, process_instance.name))
        if self.get_trait_value("use_smart_caching") in [None, False]:
            cachedir = None
        else:
            cachedir = self.output_directory
        returncode, log_file = run_process(
            destination_folder,
            process_instance,
            cachedir,
            self.generate_logging,
            **kwargs)

        # Increment the number of executed process count
        self.process_counter += 1

    def reset_process_counter(self):
        """ Method to reset the process counter to one.
        """
        self.process_counter = 1

    def read_configuration(self):
        """Find the configuration for the current study (whose name is defined
        in self study_name) and returns a dictionary that is a merge between
        global options and study specific options.

        Global option are taken from environment variable CAPSUL_CONFIG if
        it is defined, otherwise from "~/.config/capsul/config.json" if it
        exists.

        The configuration for a study can be defined the global configuration
        if it contains a dictionary in it "studies_config" option and if there
        is a key corresponding to self.study_name in this dictionary. If the
        corresponding value is a string, it must be a valid json configuration
        file name (either absolute or relative to the global configuration
        file). Otherwise, the corresponding value must be a dictionary
        containing study specific configuration values.
        If no study configuration is found from global configuration, then
        a file named "~/.config/capsul/%s/config.json" (where %s is
        self.study_name) is used if it exists.
        """

        # First read global options
        global_config_file = os.environ.get("CAPSUL_CONFIG")
        if (isinstance(global_config_file, basestring) and
            os.path.isfile(global_config_file)):

            config = json.load(open(global_config_file))
            self.global_config_file = global_config_file
        else:
            global_config_file = \
                os.path.expanduser(os.path.join(self._user_config_directory,
                                                "config.json"))
            if os.path.isfile(global_config_file):
                config = json.load(open(global_config_file))
                self.global_config_file = global_config_file
            else:
                config = {}
                self.global_config_file = None

        # Look for study specific configuration file
        study_config = \
            config.pop('studies_config', {}).get(self.study_name)
        if isinstance(study_config, basestring):
            if self.global_config_file:
                study_config = \
                    os.path.join(os.path.dirname(self.global_config_file),
                                 study_config)
            self.study_config_file = study_config
            study_config = json.load(open(study_config))
        elif study_config is None:
            study_config_file = \
                os.path.expanduser(
                    os.path.join(self._user_config_directory,
                                 "%s", "config.json") % str(self.study_name))
            if os.path.exists(study_config_file):
                study_config = json.load(open(study_config_file))
                self.study_config_file = study_config_file
            else:
                study_config = {}
                self.study_config_file = None
        else:
                self.study_config_file = self.global_config_file

        # Merge study configuration file with global configuration
        config.update(study_config)

        return config

    def get_configuration_dict(self):
        """ Returns a json compatible dictionary containing current
        configuration.
        """
        config = self.export_to_dict(exclude_transient=True,
                                     exclude_undefined=True,
                                     exclude_none=True)
        return config

    def save_configuration(self, file):
        """ Save study configuration as json file.

        Parameters
        ----------
        file: file or str (mandatory)
            either a writable opened file or the path to the output json file.
        """
        # Dump the study configuration elements
        config = self.get_configuration_dict()
        if isinstance(file, basestring):
            file = open(file, "w")
        json.dump(config, file,
                  indent=4, separators=(",", ": "))

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
        # Go through the configuration structure, respecting the traits
        # declaration order
        for trait_name in self.user_traits():
            try:
                trait_value = new_config[trait_name]
            except KeyError:
                # not specified in new_config
                continue
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
        if trait_name in self.user_traits():
            setattr(self, trait_name, trait_value)

    def get_trait(self, trait_name):
        """ Method to access the 'trait_name' study configuration element.

        Notes
        -----
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
        if trait_name in self.user_traits():
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
        if trait_name in self.user_traits():
            return getattr(self, trait_name)
        else:
            return None


class StudyConfigModule(object):
    @property
    def name(self):
        """The name of a module that can be used in configuration to select
        modules to load.
        """
        return self.__class__.__name__

    # List of modules that must be initialized before this one. It can be
    # overrriden be derived module classes.
    dependencies = []

    def __init__(self, study_config, configuration):
        self.study_config = study_config

    def initialize_module(self):
        """Method called to initialize selected study configuration modules
        on startup. This method does nothing but can be overriden by modules.
        """

    def initialize_callbacks(self):
        """Method called just after the first call to initialize_modules.
        """


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
