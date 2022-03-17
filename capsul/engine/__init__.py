# -*- coding: utf-8 -*-
'''
This module defines the main API to interact with Capsul processes.
In order to execute a process, it is mandatory to have an instance of
:py:class:`CapsulEngine`. Such an instance can be created with factory
:py:func:`capsul_engine`

Classes
=======
:class:`CapsulEngine`
---------------------

Functions
=========
:func:`database_factory`
------------------------
:func:`capsul_engine`
---------------------
:func:`activate_configuration`
------------------------------
'''

from __future__ import absolute_import
from __future__ import print_function
import importlib
import json
import os
import os.path as osp
import re
import tempfile
import subprocess
import sys

from traits.api import Dict, String, Undefined

from soma.controller import Controller, controller_to_dict
from soma.serialization import to_json, from_json
from soma.sorted_dictionary import SortedDictionary
from soma.utils.weak_proxy import get_ref

from .database_json import JSONDBEngine
from .database_populse import PopulseDBEngine

from .settings import Settings
from .module import default_modules
from . import run
from .run import WorkflowExecutionError

# FIXME TODO: OBSOLETE

#Questions about API/implementation:

#* execution:
  #* workflows are not exposed, they are running a possibly different pipeline (single process case), thus we need to keep track on it
  #* logging / history / provenance, databasing
  #* retrieving output files with transfers: when ? currently in wait(), should it be a separate method ? should it be asynchronous ?
  #* setting output parameters: currently in wait(), should it be a separate method ?
  #* disconnections / reconnections client / server
  #* actually connect computing resource[s]
#* settings / config:
  #* see comments in settings.py
  #* GUI and constraints on parameters ?
  #* how to handle optional dependencies: ie nipype depends on spm if spm is installed / configured, otherwise we can run other nipype interfaces, but no spm ones
  #* integrate soma-workflow config + CE.computing_resource


class CapsulEngine(Controller):
    '''
    A CapsulEngine is the mandatory entry point of all software using Capsul.
    It contains objects to store configuration and metadata, defines execution
    environment(s) (possibly remote) and performs pipelines execution.

    A CapsulEngine must be created using capsul.engine.capsul_engine function.
    For instance::

        from capsul.engine import capsul_engine
        ce = capsul_engine()

    Or::

        from capsul.api import capsul_engine
        ce = capsul_engine()

    By default, CapsulEngine only stores necessary configuration. But it may be
    necessary to modify the Python environment globally to apply this
    configuration. For instance, Nipype must be configured globally. If SPM is
    configured in CapsulEngine, it is necessary to explicitly activate the
    configuration in order to modify the global configuration of Nipype for
    SPM. This activation is done by explicitly activating the execution
    context of the capsul engine with the following code, inside a running
    process::

        from capsul.engine import capsul_engine, activate_configuration
        ce = capsul_engine()
        # Nipype is not configured here
        config = capsul_engine.settings.select_configurations(
            'global', {'nipype': 'any'})
        activate_configuration(config)
        # Nipype is configured here

    .. note::

        CapsulEngine is the replacement of the older
        :class:`~capsul.study_config.study_config.StudyConfig`, which is still
        present in Capsul 2.2 for backward compatibility, but will disappear in
        later versions. In Capsul 2.2 both objects exist, and are synchronized
        internally, which means that a StudyConfig object will also create a
        CapsulEngine, and the other way, and modifications in the StudyConfig
        object will change the corresponding item in CapsulEngine and vice
        versa. Functionalities of StudyConfig are moving internally to
        CapsulEngine, StudyConfig being merely a wrapper.

    **Using CapsulEngine**

    It is used to store configuration variables, and to handle execution within
    the configured context. The configuration has 2 independent axes:
    configuration modules, which provide additional configuration variables,
    and "environments" which typically represent computing resources.

    *Computing resources*

    Capsul is using :somaworkflow:`Soma-Workflow <index.html>` to run
    processes, and is thus able to connect and execute on a remote computing
    server. The remote computing resource may have a different configuration
    from the client one (paths for software or data, available external
    software etc). So configurations specific to different computing resources
    should be handled in CapsulEngine. For this, the configuration section is
    split into several configuration entries, one for each computing resource.

    As this is a little bit complex to handle at first, a "global"
    configuration (what we call "environment") is used to maintain all common
    configuration options. It is typically used to work on the local machine,
    especially for users who only work locally.

    Configuration is stored in a database (either internal or persistent),
    through the :class:`~capsul.engine.settings.Settings` object found in
    ``CapsulEngine.settings``.
    Access and modification of settings should occur within a session block
    using ``with capsul_engine.settings as session``. See the
    :class:`~capsul.engine.settings.Settings` class for details.

    ::

        >>> from capsul.api import capsul_engine
        >>> ce = capsul_engine()
        >>> config = ce.settings.select_configurations('global')
        >>> config = ce.global_config
        >>> print(config)
        {'capsul_engine': {'uses': {'capsul.engine.module.fsl': 'ALL',
          'capsul.engine.module.matlab': 'ALL',
          'capsul.engine.module.spm': 'ALL'}}}

    Whenever a new computing resource is used, it can be added as a new
    environment key to all configuration operations.

    Note that the settings store all possible configurations for all
    environments (or computing resources), but are not "activated": this is
    only done at runtime in specific process execution functions: each process
    may need to select and use a different configuration from other ones, and
    activate it individually.

    :class:`~capsul.process.process.Process` subclasses or instances may
    provide their configuration requirements via their
    :meth:`~capsul.process.process.Process.requirements` method. This method
    returns a dictionary of request strings (one element per needed module)
    that will be used to select one configuration amongst the available
    settings entries of each required module.

    *configuration modules*

    The configuration is handled through a set of configuration modules. Each
    is dedicated for a topic (for instance handling a specific external
    software paths, or managing process parameters completion, etc). A module
    adds a settings table in the database, with its own variables, and is able
    to manage runtime configuration of programs, if needed, through its
    ``activate_configurations`` function. Capsul comes with a
    set of predefined modules:
    :class:`~capsul.engine.module.attributes`,
    :class:`~capsul.engine.module.axon`,
    :class:`~capsul.engine.module.fom`,
    :class:`~capsul.engine.module.fsl`,
    :class:`~capsul.engine.module.matlab`,
    :class:`~capsul.engine.module.spm`

    **Methods**
    '''

    def __init__(self, 
                 database_location,
                 database,
                 require):
        '''
        CapsulEngine.__init__(self, database_location, database, config=None)

        The CapsulEngine constructor should not be called directly.
        Use :func:`capsul_engine` factory function instead.
        '''
        super(CapsulEngine, self).__init__()
        
        self._settings = None
        
        self._database_location = database_location
        self._database = database        

        self._loaded_modules = set()
        self.load_modules(require)
        
        from capsul.study_config.study_config import StudyConfig
        self.study_config = StudyConfig(engine=self)

        self._metadata_engine = from_json(database.json_value('metadata_engine'))

        self._connected_resource = ''
        

    @property
    def settings(self):
        if self._settings is None:
            self._settings = Settings(self.database.db)
        return self._settings

    @property
    def database(self):
        return self._database

    @property
    def database_location(self):
        return self._database_location
        
    
    @property
    def metadata_engine(self):
        return self._metadata_engine
    
    @metadata_engine.setter
    def metadata_engine(self, metadata_engine):
        self._metadata_engine = metadata_engine
        self.database.set_json_value('metadata_engine', 
                                     to_json(self._metadata_engine))
    
    def load_modules(self, require):
        '''
        Call self.load_module for each required module. The list of modules
        to load is located in self.modules (if it is None,
        capsul.module.default_modules is used).
        '''
        if require is None:
            require = default_modules
        
        for module in require:
            self.load_module(module)

    def load_module(self, module_name):
        '''
        Load a module if it has not already been loaded (is this case,
        nothing is done)
        
        A module is a fully qualified name of a Python module (as accepted
        by Python import statement). Such a module must define the two
        following functions (and may define two others, see below):
        
        def load_module(capsul_engine, module_name):        
        def set_environ(config, environ):
        
        load_module of each module is called once before reading and applying
        the configuration. It can be used to add traits to the CapsulEngine
        in order to define the configuration options that are used by the
        module. Values of these traits are automatically stored in
        configuration in database when self.save() is used, and they are
        retrieved from database before initializing modules.
        
        set_environ is called in the context of the processing (i.e. on
        the, possibly remote, machine that runs the pipelines). It receives
        the configuration as a JSON compatible dictionary (for instance a
        CapsulEngine attribute `capsul_engine.spm.directory` would be
        config['spm']['directory']). The function must modify the environ
        dictionary to set the environment variables that must be defined
        for pipeline configuration. These variables are typically used by
        modules in capsul.in_context module to manage running external
        software with appropriate configuration. 
        '''
        module_name = self.settings.module_name(module_name)
        if module_name not in self._loaded_modules:
            self._loaded_modules.add(module_name)
            python_module = importlib.import_module(module_name)
            init_settings = getattr(python_module, 'init_settings', None)
            if init_settings is not None:
                init_settings(self)
            return True
        return False

    #
    # Method imported from self.database
    #

    # TODO: take computing resource in account in the following methods

    def set_named_directory(self, name, path):
        return self.database.set_named_directory(name, path)

    def named_directory(self, name):
        return self.database.named_directory(name)

    def named_directories(self):
        return self.database.set_named_directories()

    def set_json_value(self, name, json_value):
        return self.database.set_json_value(name, json_value)

    def json_value(self, name):
        return self.database.json_value(name)

    def set_path_metadata(self, path, metadata, named_directory=None):
        return self.database.set_path_metadata(path, metadata, named_directory)

    def path_metadata(self, path, named_directory=None):
        return self.database.set_path_metadata(path, named_directory)

    def import_configs(self, environment, config_dict, cont_on_error=False):
        '''
        Import config values from a dictionary as given by
        :meth:`Settings.select_configurations`.

        Compared to :meth:`Settings.import_configs` this method (at
        :class:`CapsulEngine` level) also loads the required modules.
        '''
        modules = config_dict.get('capsul_engine', {}).get('uses', {})
        for module in modules:
            self.load_module(module)
        self.settings.import_configs(environment, config_dict, cont_on_error)

    #
    # Processes and pipelines related methods
    #
    def get_process_instance(self, process_or_id, **kwargs):
        '''
        The only official way to get a process instance is to use this method.
        For now, it simply calls self.study_config.get_process_instance
        but it will change in the future.
        '''
        instance = self.study_config.get_process_instance(process_or_id,
                                                          **kwargs)
        return instance

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
        from capsul.pipeline.pipeline import Pipeline

        pipeline = Pipeline()
        pipeline.name = pipeline_name
        pipeline.set_study_config(get_ref(self.study_config))
        pipeline.add_iterative_process(node_name, process_or_id,
                                       iterative_plugs, do_not_export,
                                       **kwargs)
        pipeline.autoexport_nodes_parameters(include_optional=True)
        return pipeline

    def start(self, process, workflow=None, history=True, get_pipeline=False, **kwargs):
        '''
        Asynchronously start the execution of a process or pipeline in the
        connected computing environment. Returns an identifier of
        the process execution and can be used to get the status of the
        execution or wait for its termination.

        TODO:
        if history is True, an entry of the process execution is stored in
        the database. The content of this entry is to be defined but it will
        contain the process parameters (to restart the process) and will be
        updated on process termination (for instance to store execution time
        if possible).

        Parameters
        ----------
        process: Process or Pipeline instance
        workflow: Workflow instance (optional - if already defined before call)
        history: bool (optional)
            TODO: not implemented yet.
        get_pipeline: bool (optional)
            if True, start() will return a tuple (execution_id, pipeline). The
            pipeline is normally the input pipeline (process) if it is actually
            a pipeline. But if the input process is a "single process", it will
            be inserted into a small pipeline for execution. This pipeline will
            be the one actually run, and may be passed to :meth:`wait` to set
            output parameters.

        Returns
        -------
        execution_id: int
            execution identifier (actually a soma-workflow id)
        pipeline: Pipeline instance (optional)
            only returned if get_pipeline is True.
        '''
        return run.start(self, process, workflow, history, get_pipeline, **kwargs)

    def connect(self, computing_resource):
        '''
        Connect the capsul engine to a computing resource
        '''
        self._connected_resource = computing_resource


    def connected_to(self):
        '''
        Return the name of the computing resource this capsul engine is
        connected to or None if it is not connected.
        '''
        return self._connected_resource

    def disconnect(self):
        '''
        Disconnect from a computing resource.
        '''
        self._connected_resource = None

    def executions(self):
        '''
        List the execution identifiers of all processes that have been started
        but not disposed in the connected computing resource. Raises an
        exception if the computing resource is not connected.
        '''
        raise NotImplementedError()

    def dispose(self, execution_id, conditional=False):
        '''
        Update the database with the current state of a process execution and
        free the resources used in the computing resource (i.e. remove the 
        workflow from SomaWorkflow).

        If ``conditional`` is set to True, then dispose is only done if the
        configuration does not specify to keep succeeded / failed workflows.
        '''
        run.dispose(self, execution_id, conditional=conditional)

    def interrupt(self, execution_id):
        '''
        Try to stop the execution of a process. Does not wait for the process
        to be terminated.
        '''
        return run.interrupt(self, execution_id)

    def wait(self, execution_id, timeout=-1, pipeline=None):
        '''
        Wait for the end of a process execution (either normal termination,
        interruption or error).
        '''
        return run.wait(self, execution_id, timeout=timeout, pipeline=pipeline)

    def status(self, execution_id):
        '''
        Return a simple value with the status of an execution (queued, 
        running, terminated, error, etc.)
        '''
        return run.status(self, execution_id)

    def detailed_information(self, execution_id):
        '''
        Return complete (and possibly big) information about a process
        execution.
        '''
        return run.detailed_information(self, execution_id)

    def call(self, process, history=True, *kwargs):
        return run.call(self, process, history=history, **kwargs)

    def check_call(self, process, history=True, **kwargs):
        return run.check_call(self, process, history=history, **kwargs)

    def raise_for_status(self, status, execution_id=None):
        '''
        Raise an exception if a process execution failed
        '''
        run.raise_for_status(self, status, execution_id)


_populsedb_url_re = re.compile(r'^\w+(\+\w+)?://(.*)')


def database_factory(database_location):
    '''
    Create a DatabaseEngine from its location string. This location can be
    either a sqlite file path (ending with '.sqlite' or ':memory:' for an 
    in memory database for testing) or a populse_db URL, or None.
    '''
    global _populsedb_url_re 

    engine_directory = None

    if database_location is None:
        database_location = ':memory:'
    match = _populsedb_url_re.match(database_location)
    if match:
        path = match.groups(2)
        _, path = osp.splitdrive(path)
        if path.startswith(os.apth.sep):
            engine_directory = osp.abspath(osp.dirname(path))
        populse_db = database_location
    elif database_location.endswith('.sqlite'):
        populse_db = 'sqlite:///%s' % database_location
        engine_directory = osp.abspath(osp.dirname(database_location))
    elif database_location == ':memory:':
        populse_db = 'sqlite:///:memory:'
    else:
        raise ValueError('Invalid database location: %s' % database_location)

    engine = PopulseDBEngine(populse_db)
    if engine_directory:
        engine.set_named_directory('capsul_engine', engine_directory)
    return engine

def capsul_engine(database_location=None, require=None):
    '''
    User facrory for creating capsul engines.

    If no database_location is given, it will default to an internal (in-
    memory) database with no persistent settings or history values.

    Configuration is read from a dictionary stored in two database entries.
    The first entry has the key 'global_config' (i.e.
    database.json_value('global_config')), it contains the configuration
    values that are shared by all processings engines. The secon entry is 
    computing_config`. It contains a dictionary with one item per computing
    resource where the key is the resource name and the value is configuration 
    values that are specific to this computing resource.

    Before initialization of the CapsulEngine, modules are loaded. The
    list of loaded modules is searched in the 'modules' value in the
    database (i.e. in database.json_value('modules')) ; if no list is
    defined in the database, capsul.module.default_modules is used.
    '''
    #if database_location is None:
        #database_location = osp.expanduser('~/.config/capsul/capsul_engine.sqlite')
    database = database_factory(database_location)
    capsul_engine = CapsulEngine(database_location, database, require=require)
    return capsul_engine


configurations = None
activated_modules = set()

def activate_configuration(selected_configurations):
    '''
    Activate a selected configuration (set of modules) for runtime.
    '''
    global configurations

    configurations = selected_configurations
    modules = configurations.get('capsul_engine', {}).get('uses', {}).keys()
    for m in modules:
        activate_module(m)

def activate_module(module_name):
    '''
    Activate a module configuration for runtime. This function is called by
    activate_configuration() and assumes the global variable
    ``capsul.engine.configurations`` is properly setup.
    '''
    global activated_modules

    if module_name not in activated_modules:
        activated_modules.add(module_name)
        module = importlib.import_module(module_name)
        check_configurations = getattr(module, 'check_configurations', None)
        complete_configurations = getattr(module, 'complete_configurations', None)
        if check_configurations:
            error = check_configurations()
            if error:
                if complete_configurations:
                    complete_configurations()
                    error = check_configurations()
            if error:
                raise EnvironmentError(error)
        activate_configurations = getattr(module, 'activate_configurations', None)
        if activate_configurations:
            activate_configurations()
