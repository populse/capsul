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

import sys
import json
import os
import os.path as osp
import re
import tempfile
import subprocess

from traits.api import Undefined, Dict, String, Undefined

from soma.controller import Controller, controller_to_dict
from soma.serialization import to_json, from_json
from soma.sorted_dictionary import SortedDictionary

from .database_json import JSONDBEngine

from capsul.study_config.study_config import StudyConfig

class CapsulEngine(Controller):
    '''
    A CapsulEngine is the mandatory entry point of all software using Capsul. It contains objects to store configuration and metadata, define execution environment(s) (possibly remote) and perform pipelines execution.
    
    A CapsulEngine must be created using capsul.engine.capsul_engine function. For instance :
    
    from capsul.engine import capsul_engine
    ce = capsul_engine()
    
    By default, CapsulEngine only store configuration. But it may be necessary to modify Python environment globally to apply this configuration. For instance, Nipype must be configured globally. If SPM is configured in CapsulEngine, it is necessary to explicitely activate the configuration in order to modify the global configuration of Nipype for SPM. This activation is done by explicitely activating the capsul engine with the following code :
    
    from capsul.engine import capsul_engine
    ce = capsul_engine()
    # Nipype is not configured here
    with ce.:
        # Nipype is configured here
    # Nipype may not be configured here
    '''
    
    default_modules = ['capsul.engine.module.spm',
                       'capsul.engine.module.fsl']
    
    computing_config = Dict(String, Controller)
    
    def __init__(self, 
                 database_location,
                 database,
                 config=None):
        '''
        CapsulEngine constructor should not be called directly.
        Use capsul_engine() factory function instead.
        '''
        super(CapsulEngine, self).__init__()
        
        self._database_location = database_location
        self._database = database

        self.global_config = Controller()
        self.computing_config = {}
        
        db_config = database.json_value('config')
        if db_config is None:
            db_config = {}

        self._loaded_modules = SortedDictionary()
        self.modules = database.json_value('modules')
        if self.modules is None:
            self.modules = self.default_modules
        self.load_modules()
        
        self._metadata_engine = from_json(database.json_value('metadata_engine'))
        
        for cfg in (db_config.get('global_config', {}), config):
            if cfg:
                for n, v in cfg.items():
                    if isinstance(v, dict):
                        o = getattr(self.global_config, n)
                        if isinstance(o, Controller):
                            o.import_from_dict(v)
                            continue
                    setattr(self.global_config, n, v)
        
        for computing_resource, computing_config in db_config.get('computing_config', {}).items():
            self.computing_config[computing_resource] = self.global_config.copy(with_values=False)
            if computing_config:
                for n, v in computing_config.items():
                    if isinstance(v, dict):
                        o = getattr(self.computing_config[computing_resource], n)
                        if isinstance(o, Controller):
                            o.import_from_dict(v)
                            continue
                    setattr(self.computing_config[computing_resource], n, v)

        self.study_config = StudyConfig(engine=self)

    def config(self, name, computing_resource):
        '''
        Return a configuration attribute for a selected computing resource
        name. If the attribute does not exist in the computing resource
        configuration, it is searched in global configuration.
        '''
        result = getattr(self.computing_resource[computing_resource], name, None)
        if result in (None, Undefined):
            result = getattr(self.global_config, name)
        return result
    
    def add_computing_resource(self, computing_resource):
        '''
        Add a new computing ressource in this capsul engine. Each computing
        resouce can have its own configuration values that override gobal
        configuration.
        '''
        self.computing_config[computing_resource] = self.global_config.copy(with_values=False)
        
        
    def remove_computing_resource(self, computing_resource):
        '''
        Remove a computing resource configuration from this capsul engine
        '''
        del self.computing_config[computing_resource]


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
    
    def load_modules(self):
        '''
        Call self.load_module for each required module. The list of modules
        to load is located in self.modules (if it is None,
        self.default_modules is used).
        '''
        if self.modules is None:
            modules = self.default_modules
        else:
            modules = self.modules
        
        for module in modules:
            self.load_module(module)
            
    def load_module(self, module):
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
        
        set__environ is called in the context of the processing (i.e. on 
        he, possibly remote, machine that runs the pipelines). It receives
        the configuration as a JSON compatible dictionary (for instance a
        CapsulEngine attibute `capsul_engine.spm.directory` would be
        config['spm']['directory']). The function must modify the environ
        dictionary to set the environment variables that must be defined
        for pipeline configuration. These variables are typically used by
        modules in capsul.in_context module to manage running external
        software with appropriate configuration. 
        '''
        if module not in self._loaded_modules:
            __import__(module)
            python_module = sys.modules.get(module)
            if python_module is None:
                raise ValueError('Cannot find %s in Python modules' % module)
            loader = getattr(python_module, 'load_module', None)
            if loader is None:
                raise ValueError('No function load_module() defined in %s' % module)
            self._loaded_modules[module] = loader(self, module)
            return True
        return False
    

    def save(self):
        '''
        Save the full status of the CapsulEngine in the database.
        The folowing items are set in the database:
        
          'metadata_engine': a JSON serialization of self.metadata_engine
          'config': a dictionary containing configuration. This dictionary is
              obtained using traits defined on capsul engine (ignoring values
              that are undefined).
        '''
        if self._metadata_engine:
            self.database.set_json_value('metadata_engine', 
                                        to_json(self._metadata_engine))
        config = {}
        global_config = controller_to_dict(self.global_config, exclude_undefined=True)
        if global_config:
            config['global_config'] = global_config
        computing_config = controller_to_dict(self.computing_config, exclude_undefined=True)
        if computing_config:
            config['computing_config'] = computing_config
        
        self.database.set_json_value('config', config)
        self.database.commit()
    
    
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
        return self.database.set_path_metadata(name, path, metadata, named_directory)
    
    def path_metadata(self, path, named_directory=None):
        return self.database.set_path_metadata(name, path, named_directory)


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

    def connect(self, computing_ressource):
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
        tmp = tempfile.NamedTemporaryFile(suffix='.py')
        tmp.write(code)
        tmp.flush()
        json_environ = subprocess.check_output([sys.executable, tmp.name])
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
    
    engine = None
    engine_directory = None

    if database_location is not None and database_location.endswith('.json'):
        engine_directory = osp.abspath(osp.dirname(database_location))
        engine = JSONDBEngine(database_location)
    else:
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
        
        # Import populse_db related module only
        # if used in order to add a mandatory
        # dependency on the project
        try:
            from .database_populse import PopulseDBEngine
            engine = PopulseDBEngine(populse_db)
        except ImportError:
            # database is not available, fallback to json
            if database_location != ':memory':
                engine_directory = osp.abspath(osp.dirname(database_location))
                if database_location.endswith('.sqlite'):
                    database_location = database_location[:-6] + 'json'
            engine = JSONDBEngine(database_location)
    if engine_directory:
        engine.set_named_directory('capsul_engine', engine_directory)
    return engine

def capsul_engine(database_location=None, config=None):
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
    defined in the database, CapsulEngine.default_modules is used.
    '''
    #if database_location is None:
        #database_location = osp.expanduser('~/.config/capsul/capsul_engine.sqlite')
    database = database_factory(database_location)
    capsul_engine = CapsulEngine(database_location, database, config=config)
    return capsul_engine
    
