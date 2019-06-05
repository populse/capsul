'''
This module defines the main API to interact with Capsul processes.
In order to execute a process, it is mandatory to have an instance of
:py:class:`CapsulEngine`. Such an instance can be created with factory
:py:func:`capsul_engine`
'''
import sys
import json
import os.path as osp
import re

from traits.api import Undefined, Dict, String, Undefined

from soma.controller import Controller
from soma.serialization import to_json, from_json

from .database_json import JSONDBEngine
from .execution_context import ExecutionContext

from capsul.study_config.study_config import StudyConfig

class CapsulEngine(Controller):
    '''
    A CapsulEngine is the mandatory entry point of all software using Capsul. It contains objects to store configuration and metadata, define execution environment (possibly remote) and perform pipelines execution.
    
    A CapsulEngine must be created using capsul.engine.capsul_engine function. For instance :
    
    from capsul.engine import capsul_engine
    ce = capsul_engine()
    
    By default, CapsulEngine only store necessary configuration. But it may be necessary to modify Python environment globally to apply this configuration. For instance, Nipype must be configured globally. If SPM is configured in CapsulEngine, it is necessary to explicitely activate the configuration in order to modify the global configuration of Nipype for SPM. This activation is done by explicitely activating the execution context of the capsul engine with the following code :
    
    from capsul.engine import capsul_engine
    ce = capsul_engine()
    # Nipype is not configured here
    with ce.execution_context():
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

        self._loaded_modules = {}
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

        self.init_modules()

        self.study_config = StudyConfig(engine=self)

    def config(self, name, computing_resource):
        result = getattr(self.computing_resource[computing_resource], name, None)
        if result in (None, Undefined):
            result = getattr(self.global_config, name)
        return result
    
    def add_computing_resource(self, computing_resource):
        self.computing_config[computing_resource] = self.global_config.copy(with_values=False)
        
        
    def remove_computing_resource(self, computing_resource):
        del self.computing_config[computing_resource]


    @property
    def database(self):
        return self._database

    @property
    def database_location(self):
        return self._database_location
    
    @property
    def execution_context(self):
        return self._execution_context

    @execution_context.setter
    def execution_context(self, execution_context):
        self._execution_context = execution_context
    
    @property
    def processing_engine(self):
        return self._processing_engine
    
    
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
        def init_module(capul_engine, module_name, loaded_module):

        load_module of each module is called once before reading and applyin
        the configuration. It can be used to add traits to the CapsulEngine
        in order to define the configuration options that are used by the
        module. Values of these traits are automatically stored in
        configuration in database when self.save() is used, and they are
        retrieved from database before initializing modules.
        
        init_module of each module is called once after the reading of
        configuration and the setting of capsul engine attributes defined in
        traits.
        
        A module may define the following functions:
        
        def enter_execution_context(execution_context)
        def exit_execution_context(execution_context)
        
        enter_execution_context (resp. exit_execution_context) is called each
        time the capsul engine's exection context is activated (resp.
        deactivated). 
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
    
    def init_modules(self):
        '''
        Call self.init_module for each required module. The list of modules
        to initialize is located in self.modules (if it is None,
        self.default_modules is used).
        '''
        if self.modules is None:
            modules = self.default_modules
        else:
            modules = self.modules
        for module in modules:
            self.init_module(module)
    
    def init_module(self, module):
        '''
        Initialize a module by calling its init_module function.
        '''
        python_module = sys.modules.get(module)
        if python_module is None:
            raise ValueError('Cannot find %s in Python modules' % module)
        initializer = getattr(python_module, 'init_module', None)
        if initializer is None:
            raise ValueError('No function init_module() defined in %s' % module)
        initializer(self, module, self._loaded_modules[module])
    
    def save(self):
        '''
        Save the full status of the CapsulEngine in the database.
        The folowing items are set in the database:
        
          'execution_context': a JSON serialization of self.execution_context
          'processing_engine': a JSON serialization of self.processing_engine
          'metadata_engine': a JSON serialization of self.metadata_engine
          'config': a dictionary containing configuration. This dictionary is
              obtained using traits defined on capsul engine (ignoring values
              that are undefined).
        '''
        if self._metadata_engine:
            self.database.set_json_value('metadata_engine', 
                                        to_json(self._metadata_engine))
        config = {}
        global_config = self.global_config.export_to_dict(exclude_undefined=True)
        if global_config:
            config['global_config'] = global_config
        computing_config = self.computing_config.export_to_dict(exclude_undefined=True)
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
        raise NotImplementedError()

    
    def disconnect(self):
        '''
        Disconnect from a computing ressource.
        '''
        raise NotImplementedError()


    def environment_builder(self):
        '''
        Return a string that contains a Python script that must be run in
        the computing environment in order to define the environment variables
        that must be given to all processes.
        '''
        raise NotImplementedError()
    
    
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
        
    
_populsedb_url_re = re.compile(r'^\w+(\+\w+)?://(.*)')
def database_factory(database_location):
    '''
    Create a DatabaseEngine from its location string. This location can be
    either a sqlite file path (ending with '.sqlite' or ':memory:' for an 
    in memory database for testing) or a populse_db URL.
    '''
    global _populsedb_url_re 
    
    engine = None
    engine_directory = None

    if database_location.endswith('.json'):
        engine_directory = osp.abspath(osp.dirname(database_location))
        engine = JSONDBEngine(database_location)
    else:
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
        from .database_populse import PopulseDBEngine
        engine = PopulseDBEngine(populse_db)
    if engine_directory:
        engine.set_named_directory('capsul_engine', engine_directory)
    return engine

def capsul_engine(database_location=None, config=None):
    '''
    User facrory for creating capsul engines.
    
    If no database_location is given, the default value is
    '~/.config/capsul/capsul_engine.sqlite' where ~ is replaced by the
    current use home directory (with os.path.expanduser).
    
    Configuration is read from a dictionary stored in the database with
    the key 'config' (i.e. using database.json_value('config')). Then,
    the content of the config parameter is recursively merged into the
    configuration (replacing items with the same name).
    
    Before initialization of the CapsulEngine, modules are loaded. The
    list of loaded modules is searched in the 'modules' value in the
    database (i.e. in database.json_value('modules')) ; if no list is
    defined in the database, CapsulEngine.default_modules is used.
    '''
    if database_location is None:
        database_location = osp.expanduser('~/.config/capsul/capsul_engine.sqlite')
    database = database_factory(database_location)
    capsul_engine = CapsulEngine(database_location, database, config=config)
    return capsul_engine
    
