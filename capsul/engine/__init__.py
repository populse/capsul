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

from .database_json import JSONDBEngine
from .database_populse import PopulseDBEngine

from .settings import Settings
from .module import default_modules

class CapsulEngine(Controller):
    '''
    A CapsulEngine is the mandatory entry point of all software using Capsul. It contains objects to store configuration and metadata, define execution environment(s) (possibly remote) and perform pipelines execution.
    
    A CapsulEngine must be created using capsul.engine.capsul_engine function. For instance::
    
        from capsul.engine import capsul_engine
        ce = capsul_engine()

    Or::

        from capsul.api import capsul_engine
        ce = capsul_engine()

    By default, CapsulEngine only stores necessary configuration. But it may be necessary to modify the Python environment globally to apply this configuration. For instance, Nipype must be configured globally. If SPM is configured in CapsulEngine, it is necessary to explicitely activate the configuration in order to modify the global configuration of Nipype for SPM. This activation is done by explicitely activating the execution context of the capsul engine with the following code::
    
        from capsul.engine import capsul_engine
        ce = capsul_engine()
        # Nipype is not configured here
        with ce:
            # Nipype is configured here
        # Nipype may not be configured here

    .. note::

        CapsulEngine is the replacement of the older :class:`~capsul.study_config.study_config.StudyConfig`, which is still present in Capsul 2.2 for backward compatibility, but will disapear in later versions. In Capsul 2.2 both objects exist, and are synchronized internally, which means that a StudyConfig object will also ceate a CapsulEngine, and the other way, and modifications in the StudyConfig object will change the corresponding item in CapsulEngine and vice versa. Functionalities of StudyConfig are moving internally to CapsulEngine, StudyConfig being merely a wrapper.

    **Using CapsulEngine**

    It is used to store configuration variables, and to handle execution within the configured context. The configuration has 2 independent axes: configuration modules, which provide additional configutation variables, and computing resources.

    *Computing resources*

    Capsul is using :somaworkflow:`Soma-Workflow <index.html>` to run processes, and is thus able to connect and execute on a remote computing server. The remote computing resource may have a different configuration from the client one (paths for software or data, available external software etc). So configurations specific to different computing resources should be handled in CapsulEngine. For this, the configuration section is split into several configuration instances, one for each computing resource.

    As this is a little bit complex to handle at first, a "global" configuration is used to maintain all common configuration options. It is typically used to work on the local machine, especially for users who only work locally. This configuration object is found under the ``global_config`` object in a CapsulEngine instance. It is a :class:`~soma.controller.controller.Controller` object::

        >>> from capsul.api import capsul_engine
        >>> ce = capsul_engine()
        >>> config = ce.global_config
        >>> print(config.export_to_dict())
        OrderedDict([('fsl', OrderedDict([('config', <undefined>), ('directory', <undefined>), ('prefix', <undefined>), ('use', <undefined>)])), ('matlab', OrderedDict([('executable', <undefined>)])), ('spm', OrderedDict([('directory', <undefined>), ('standalone', <undefined>), ('use', <undefined>), ('version', <undefined>)])), ('axon', OrderedDict([('shared_directory', <undefined>)])), ('attributes', OrderedDict([('attributes_schema_paths', [u'capsul.attributes.completion_engine_factory']), ('attributes_schemas', OrderedDict()), ('path_completion', <undefined>), ('process_completion', 'builtin')]))])

    Whenever a new computing resource is used, it can be added as a new configuration using :meth:`add_computing_resource`. Configuration options for this resource are a merge of the global one, and the specific ones::

        >>> ce.add_computing_resource('computing_server')
        >>> ce.global_config.spm.directory = '/tmp'
        >>> print(ce.config('spm.directory', 'computing_server')
        '/tmp'
        >>> ce.set_config('spm.directory', '/home/myself', 'computing_server')
        >>> print(ce.config('spm.directory', 'computing_server')
        '/home/myself'
        >>> print(ce.config('spm.directory')
        '/tmp'

    *configuration modules*

    The configuration is handled through a set of configuration modules. Each is dedicated for a topic (for instance handling a specific external software paths, or managing process parameters completion,; etc). A module adds a configuration Controller, with its own variables, and is able to manage runtime configuration of programs, if needed, through environment variables. Capsul comes with a set of predefined modules:
    :class:`~capsul.engine.module.attributes.AttributesConfig`,
    :class:`~capsul.engine.module.axon.AxonConfig`,
    :class:`~capsul.engine.module.fom.FomConfig`,
    :class:`~capsul.engine.module.fsl.FSLConfig`,
    :class:`~capsul.engine.module.matlab.MatlabConfig`,
    :class:`~capsul.engine.module.spm.SPMConfig`

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
        CapsulEngine attibute `capsul_engine.spm.directory` would be
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

    def start(self, process, history=True):
        '''
        Asynchronously start the exection of a process in the connected 
        computing environment. Returns a string that is an identifier of the
        process execution and can be used to get the status of the 
        execution or wait for its termination.
        
        if history is True, an entry of the process execution is stored in
        the database. The content of this entry is to be defined but it will
        contain the process parameters (to restart the process) and will be 
        updated on process termination (for instance to store execution time
        if possible).
        '''
        raise NotImplementedError()

    def connect(self, computing_resource):
        '''
        Connect the capsul engine to a computing resource
        '''
        raise NotImplementedError()

    
    def connected_to(self):
        '''
        Return the name of the computing resource this capsul engine is
        connected to or None if it is not connected.
        '''
        return None

    
    def disconnect(self):
        '''
        Disconnect from a computing ressource.
        '''
        raise NotImplementedError()


    def environment_builder(self):
        '''
        Return a string that contains a Python script that must be run in
        the computing environment in order to define the environment variables
        that must be given to all processes. The code of this script must be
        executed in the processing context (i.e. on the, eventualy remote,
        machine that will run the process). This code is supposed to be executed
        in a new Python command and prints a JSON dictionary on standard output.
        This dictionary contain environment variables that must be given to any
        process using the environment of this capsul engine.
        '''
        environ = {}
        import_lines = []
        code_lines = []

        config = self.global_config.export_to_dict(exclude_undefined=True,
                                                   exclude_empty=True)
        connected_computing_resource = self.connected_to()
        if connected_computing_resource:
            computing_config = self.computing_config[connected_computing_resource]
            config.update(computing_config.export_to_dict(exclude_undefined=True,
                                                          exclude_empty=True))
        import_lines.append('from collections import OrderedDict')
        import_lines.append('import json')
        import_lines.append('import sys')
        code_lines.append('config = %s' % repr(config))
        code_lines.append('environ = {}')
        for module in self._loaded_modules:
            python_module = sys.modules[module]
            if getattr(python_module, 'set_environ', None):
                import_lines.append('import %s' % module)            
                code_lines.append('%s.set_environ(config, environ)' % module)
        code_lines.append('json.dump(environ, sys.stdout)')
        
        code = '\n'.join(import_lines) + '\n\n' + '\n'.join(code_lines)
        return code
    
    
    def executions(self):
        '''
        List the execution identifiers of all processes that have been started
        but not disposed in the connected computing ressource. Raises an
        exception if the computing resource is not connected.
        '''
        raise NotImplementedError()
        

    def dispose(self, execution_id):
        '''
        Update the database with the current state of a process execution and
        free the resources used in the computing resource (i.e. remove the 
        workflow from SomaWorkflow).
        '''
        raise NotImplementedError()
    
    
    def interrupt(self, execution_id):
        '''
        Try to stop the execution of a process. Does not wait for the process
        to be terminated.
        '''
        raise NotImplementedError()
    
    def wait(self, execution_id):
        '''
        Wait for the end of a process execution (either normal termination,
        interruption or error).
        '''
        raise NotImplementedError()
    
    def status(self, execution_id):
        '''
        Return a simple value with the status of an execution (queued, 
        running, terminated, error, etc.)
        '''
        raise NotImplementedError()


    def detailed_information(self, execution_id):
        '''
        Return complete (and possibly big) information about a process
        execution.
        '''
        raise NotImplementedError()

    
    def call(self, process, history=True):
        eid = self.start(process, history)
        return self.wait(eid)
    
    
    def check_call(self, process, history=True):
        eid = self.start(process, history)
        status = self.wait(eid)
        self.raise_for_status(status, eid)

    def raise_for_status(self, status, execution_id=None):
        '''
        Raise an exception if a process execution failed
        '''
        raise NotImplementedError()
        

    def __enter__(self):
        code = self.environment_builder()
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py')
        tmp.write(code)
        tmp.flush()
        json_environ = subprocess.check_output(
            [sys.executable, tmp.name]).decode('utf-8')
        environ = json.loads(json_environ)
        
        self._environ_backup = {}
        for n in environ.keys():
            v = os.environ.get(n)
            self._environ_backup[n] = v
            os.environ[n] = environ[n]
            
    def __exit__(self, exc_type, exc_value, traceback):        
        for n, v in self._environ_backup.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        del self._environ_backup
        
    
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
    
    If no database_location is given, the default value is
    '~/.config/capsul/capsul_engine.sqlite' where ~ is replaced by the
    current use home directory (with os.path.expanduser).
    
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
