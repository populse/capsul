# -*- coding: utf-8 -*-
'''
Main :class:`StudyConfig` class for configuration of Capsul software, directories etc.

Classes
========
:class:`StudyConfig`
--------------------
:class:`StudyConfigModule`
--------------------------

Functions
=========
:func:`default_study_config`
----------------------------
'''

# System import
from __future__ import print_function
from __future__ import absolute_import

import os
import logging
import json
import sys
import six
import weakref
import threading
if sys.version_info[:2] >= (2, 7):
    from collections import OrderedDict
else:
    from soma.sorted_dictionary import SortedDictionary as OrderedDict

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import File, Directory, Bool, String, Undefined, Int

# Soma import
from soma.controller import Controller

# Capsul import
from capsul.pipeline.pipeline import Pipeline
from capsul.process.process import Process
from capsul.study_config.run import run_process
from capsul.pipeline.pipeline_nodes import Node
from capsul.study_config.process_instance import get_process_instance


class StudyConfig(Controller):
    """ Class to store the study parameters and processing options.

    StudyConfig is deprecated and will probably be removed in Capsul 3.
    Please use :class:`~capsul.engine.CapsulEngine` instead and its
    construction function, :func:`~capsul.engine.capsul_engine` when possible.

    This in turn is used to evaluate a Process instance or a Pipeline.

    StudyConfig has modules (see BrainVISAConfig, AFNIConfig, FSLConfig,
    MatlabConfig, ANTSConfig, SmartCachingConfig, SomaWorkflowConfig,
    SPMConfig, FOMConfig).
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

      from capsul.api import StudyConfig

      study_config = StudyConfig(modules=['SPMConfig', 'FomConfig'])
      # or:
      study_config = StudyConfig(modules=StudyConfig.default_modules +
      ['FomConfig'])


    Attributes
    ----------
    input_directory : str
        parameter to set the study input directory
    output_directory : str
        parameter to set the study output directory
    generate_logging : bool (default False)
        parameter to control the log generation
    create_output_directories : bool (default True)
        Create parent directories of all output File or Directory before
        running a process
    process_output_directory : bool (default False)
        Create a process specific output_directory by appending a
        subdirectory to output_directory. This subdirectory is named 
        '<count>-<name>' where <count> if self.process_counter and <name> 
        is the name of the process.

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

    default_modules = ['AFNIConfig', 'ANTSConfig', 'FSLConfig', 'MatlabConfig', 'SmartCachingConfig',
                       'SomaWorkflowConfig', 'SPMConfig']
    _user_config_directory = os.path.join("~", ".config", "capsul")

    study_name = String(
        None,
        desc="Name of the study to configure",
        # traits with transient=True will not be saved in configuration
        # see  http://code.enthought.com/projects/traits/docs/html/
        # traits_user_manual/advanced.html#pickling-hastraits-objects
        transient=True, groups=['study'])

    user_level = Int(
        0,
        desc="0: basic, 1: advanced, 2: expert... used to display or hide "
             "some advanced features or process parameters that would be "
             "confusing to a novice user",
        groups=['study'])

    input_directory = Directory(
        Undefined,
        desc="Parameter to set the study input directory",
        groups=['study'])

    output_directory = Directory(
        Undefined,
        desc="Parameter to set the study output directory",
        groups=['study'])

    generate_logging = Bool(
        False,
        desc="Parameter to control the log generation",
        groups=['study'])

    create_output_directories = Bool(
        True,
        desc="Create parent directories of all output File or Directory before running a process",
        groups=['study'])

    process_output_directory = Bool(
        False,
        desc="Create a process specific output_directory by appending a "
             "subdirectory to output_directory. This subdirectory is named "
             "'<count>-<name>' where <count> if self.process_counter and "
             "<name> is the name of the process.",
        groups=['study'])

    def __init__(self, study_name=None, init_config=None, modules=None,
                 engine=None, **override_config):
        """ Initialize the StudyConfig class

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
        engine: CapsulEngine
            this parameter is temporary, it just helps to handle the transition
            to :class:`capsul.engine.CapsulEngine`. Don't use it in client code.
        override_config: dictionary
            The content of these keyword parameters will be set on the
            configuration after it has been initialized from configuration
            files (or from init_config).
        """

        super(StudyConfig, self).__init__()
        
        if study_name:
            self.study_name = study_name

        if engine is None:
            from capsul.engine import capsul_engine
            self.engine = capsul_engine()
            self.engine.study_config = weakref.proxy(self)
        else:
            self.engine = weakref.proxy(engine)

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

        self.visible_groups = set(['study'])

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
        for k, v in six.iteritems(config):
            setattr(self, k, v)
        self.initialize_modules()
        self.run_lock = threading.RLock()
        self.run_interruption_request = False

    def initialize_modules(self):
        """
        Modules initialization, calls initialize_module on each config module.
        This is not done during module instantiation to allow interactions
        between modules (e.g. Matlab configuration can influence Nipype
        configuration). Modules dependencies are taken into account in
        initialization.
        """
        already_initialized = set()
        # Use a stack to allow to manage module dependencies
        stack = list(self.modules.keys())
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
            # Initialize a module
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
            # load dependencies
            for dep_module_name in module.dependencies:
                if dep_module_name not in self.modules:
                    self.load_module(dep_module_name, config)
            return module

    def run(self, process_or_pipeline, output_directory= None,
            execute_qc_nodes=True, verbose=0, configuration_dict=None,
            **kwargs):
        """Method to execute a process or a pipline in a study configuration
         environment.

         Depending on the studies_config settings, it may be a sequential run,
         or a parallel run, which can involve remote execution (through soma-
         workflow).

         Only pipeline nodes can be filtered on the 'execute_qc_nodes'
         attribute.

         A valid output directory is expected to execute the process or the
         pepeline without soma-workflow.

        Parameters
        ----------
        process_or_pipeline: Process or Pipeline instance (mandatory)
            the process or pipeline we want to execute
        output_directory: Directory name (optional)
            the output directory to use for process execution. This replaces
            self.output_directory but left it unchanged.
        execute_qc_nodes: bool (optional, default False)
            if True execute process nodes that are tagged as qualtity control
            process nodes.
        verbose: int
            if different from zero, print console messages.
        configuration_dict: dict (optional)
            configuration dictionary
        """


        # Use soma workflow to execute the pipeline or process in parallel
        # on the local machine. This has now moved to CapsulEngine.
        if self.get_trait_value("use_soma_workflow"):
            return self.engine.check_call(process_or_pipeline, **kwargs)

        # here we only deal with the (obsolete) local execution mode.

        with self.run_lock:
            self.run_interruption_request = False

        # set parameters values
        for k, v in six.iteritems(kwargs):
            setattr(process_or_pipeline, k, v)
        # output_directory cannot be in kwargs
        if output_directory not in (None, Undefined) \
                and 'output_directory' in process_or_pipeline.traits():
            process_or_pipeline.output_directory = output_directory

        missing = process_or_pipeline.get_missing_mandatory_parameters()
        if len(missing) != 0:
            ptype = 'process'
            if isinstance(process_or_pipeline, Pipeline):
                ptype = 'pipeline'
            raise ValueError('In %s %s: missing mandatory parameters: %s'
                             % (ptype, process_or_pipeline.name,
                                ', '.join(missing)))


        # Use the local machine to execute the pipeline or process
        if output_directory is None or output_directory is Undefined:
            if 'output_directory' in process_or_pipeline.traits():
                output_directory = getattr(process_or_pipeline,
                                            'output_directory')
            if output_directory is None or output_directory is Undefined:
                output_directory = self.output_directory
         # Not all processes need an output_directory defined on
        # StudyConfig
        if output_directory is not None \
                and output_directory is not Undefined:
            # Check the output directory is valid
            if not isinstance(output_directory, six.string_types):
                raise ValueError(
                    "'{0}' is not a valid directory. A valid output "
                    "directory is expected to run the process or "
                    "pipeline.".format(output_directory))
            try:
                if not os.path.isdir(output_directory):
                    os.makedirs(output_directory)
            except OSError:
                raise ValueError(
                    "Can't create folder '{0}', please investigate.".format(
                        output_directory))

        # Temporary files can be generated for pipelines
        temporary_files = []
        result = None
        try:
            # Generate ordered execution list
            execution_list = []
            if isinstance(process_or_pipeline, Pipeline):
                execution_list = \
                    process_or_pipeline.workflow_ordered_nodes()
                # Filter process nodes if necessary
                if not execute_qc_nodes:
                    execution_list = [node for node in execution_list
                                      if node.node_type
                                          == "processing_node"]
                for node in execution_list:
                    # check temporary outputs and allocate files
                    process_or_pipeline._check_temporary_files_for_node(
                        node, temporary_files)
            elif isinstance(process_or_pipeline, Process):
                execution_list.append(process_or_pipeline)
            else:
                raise Exception(
                    "Unknown instance type. Got {0}and expect Process or "
                    "Pipeline instances".format(
                        process_or_pipeline.__module__.name__))

            with self.run_lock:
                if self.run_interruption_request:
                    self.run_interruption_request = False
                    raise RuntimeError('Execution interruption requested')

            # Execute each process node element
            for process_node in execution_list:
                # Execute the process instance contained in the node
                if isinstance(process_node, Node):
                    result, log_file = run_process(
                        output_directory,
                        process_node.process,
                        generate_logging=self.generate_logging,
                        verbose=verbose,
                        configuration_dict=configuration_dict)

                # Execute the process instance
                else:
                    result, log_file = run_process(
                        output_directory,
                        process_node,
                        generate_logging=self.generate_logging,
                        verbose=verbose,
                        configuration_dict=configuration_dict)

                with self.run_lock:
                    if self.run_interruption_request:
                        self.run_interruption_request = False
                        raise RuntimeError('Execution interruption requested')

        finally:
            # Destroy temporary files
            if temporary_files:
                # If temporary files have been created, we are sure that
                # process_or_pipeline is a pipeline with a method
                # _free_temporary_files.
                process_or_pipeline._free_temporary_files(temporary_files)
        return result

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
        if (isinstance(global_config_file, six.string_types) and
            os.path.isfile(global_config_file)):

            with open(global_config_file) as f:
                config = json.load(f)
            self.global_config_file = global_config_file
        else:
            global_config_file = \
                os.path.expanduser(os.path.join(self._user_config_directory,
                                                "config.json"))
            if os.path.isfile(global_config_file):
                with open(global_config_file) as f:
                    config = json.load(f)
                self.global_config_file = global_config_file
            else:
                config = {}
                self.global_config_file = None

        # Look for study specific configuration file
        study_config = \
            config.pop('studies_config', {}).get(self.study_name)
        if isinstance(study_config, six.string_types):
            if self.global_config_file:
                study_config = \
                    os.path.join(os.path.dirname(self.global_config_file),
                                 study_config)
            self.study_config_file = study_config
            with open(study_config) as f:
                study_config = json.load(f)
        elif study_config is None:
            study_config_file = \
                os.path.expanduser(
                    os.path.join(self._user_config_directory,
                                 "%s", "config.json") % str(self.study_name))
            if os.path.exists(study_config_file):
                with open(study_config_file) as f:
                    study_config = json.load(f)
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
        if isinstance(file, six.string_types):
            with open(file, "w") as f:
                json.dump(config, f, indent=4, separators=(",", ": "))
        else:
            json.dump(config, file, indent=4, separators=(",", ": "))

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
            self.trait_get(name)

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
            except Exception:
                logger.debug(
                    "Could not set value for config variable {0}: "
                    "{1}".format(trait_name, repr(trait_value)))

    def set_trait_value(self, trait_name, trait_value):
        """ Method to set the value of a parameter.

        Parameters
        ----------
        trait_name: str (mandatory)
            the trait name we want to modify
        trait_value: object (mandatory)
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

    def get_process_instance(self, process_or_id, **kwargs):
        """ Return a Process instance given an identifier.

        The identifier is either:

            * a derived Process class.
            * a derived Process class instance.
            * a Nipype Interface instance.
            * a Nipype Interface class.
            * a string description of the class `<module>.<class>`.
            * a string description of a function to warp `<module>.<function>`.
            * a string description of a pipeline `<module>.<fname>.xml`.
            * an XML filename for a pipeline

        Default values of the process instance are passed as additional
        parameters.

        .. note:

            If no process is found an ImportError is raised.

        .. note:

            If the 'process_or_id' parameter is not valid a ValueError is
            raised.

        .. note:

            If the function to warp does not contain a process description in
            its decorator or docstring ('<process>...</process>') a ValueError
            is raised.

        Parameters
        ----------
        process_or_id: instance or class description (mandatory)
            a process/nipype interface instance/class or a string description.
        kwargs:
            default values of the process instance parameters.

        Returns
        -------
        result: Process
            an initialized process instance.

        """
        return get_process_instance(process_or_id, study_config=self,
                                    **kwargs)

    def get_iteration_pipeline(self, pipeline_name, node_name, process_or_id,
                               iterative_plugs=None, do_not_export=None,
                               make_optional=None, **kwargs):
        """ Create a pipeline with an iteration node iterating the given
        process.

        Parameters
        ----------
        pipeline_name: str
            pipeline name
        node_name: str
            iteration node name in the pipeline
        process_or_id: process description
            as in :meth:`get_process_instance`
        iterative_plugs: list (optional)
            passed to :meth:`Pipeline.add_iterative_process`
        do_not_export: list
            passed to :meth:`Pipeline.add_iterative_process`
        make_optional: list
            passed to :meth:`Pipeline.add_iterative_process`

        Returns
        -------
        pipeline: :class:`Pipeline` instance
        """
        return self.engine.get_iteration_pipeline(
            pipeline_name, node_name, process_or_id,
            iterative_plugs=iterative_plugs, do_not_export=do_not_export,
            make_optional=make_optional, **kwargs)


_default_study_config = None

def default_study_config():
    """
    On the first call create a StudyConfig instance with default configuration
    (eventually reading configuration files). Then returns this instance on all
    subsequent calls.
    """
    global _default_study_config
    if _default_study_config is None:
        _default_study_config = StudyConfig()
    return _default_study_config

    

class StudyConfigModule(object):
    '''
    :class:`StudyConfig` module base class (abstract)
    '''
    @property
    def name(self):
        """The name of a module that can be used in configuration to select
        modules to load.
        """
        return self.__class__.__name__

    # List of modules that must be initialized before this one. It can be
    # overridden be derived module classes.
    dependencies = []

    def __init__(self, study_config, configuration):
        self.study_config = study_config

    def initialize_module(self):
        """Method called to initialize selected study configuration modules
        on startup. This method does nothing but can be overridden by modules.
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
    print("Standard configuration done in  {0} s.".format(toc - tic))

    # Empty configuration
    empty_config = OrderedDict([])
    tic = timeit.default_timer()
    study = StudyConfig(empty_config)
    toc = timeit.default_timer()
    print("Empty configuration done in  {0} s.".format(toc - tic))
