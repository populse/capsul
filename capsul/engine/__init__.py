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

from traits.api import Undefined

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

        db_config = database.json_value('config')

        self._loaded_modules = {}
        self.modules = database.json_value('modules')
        if self.modules is None:
            self.modules = self.default_modules
        self.load_modules()
        
        execution_context = from_json(database.json_value('execution_context'))
        if execution_context is None:
            execution_context = ExecutionContext()
        self._execution_context = execution_context
            
        self._processing_engine = from_json(database.json_value('processing_engine'))        
        self._metadata_engine = from_json(database.json_value('metadata_engine'))
        
        for cfg in (db_config, config):
            if cfg:
                for n, v in cfg.items():
                    if isinstance(v, dict):
                        o = getattr(self, n)
                        if isinstance(o, Controller):
                            o.import_from_dict(v)
                            continue
                    setattr(self, n, v)

        self.init_modules()

        self.study_config = StudyConfig(engine=self)

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
        self.database.set_json_value('execution_context', 
                                     to_json(self._execution_context))
        if self._processing_engine:
            self.database.set_json_value('processing_engine', 
                                        to_json(self._processing_engine))
        if self._metadata_engine:
            self.database.set_json_value('metadata_engine', 
                                        to_json(self._metadata_engine))
        config = {}
        for n in self.user_traits().keys():
            v = getattr(self, n)
            if v is Undefined:
                continue
            if isinstance(v, Controller):
                v = v.export_to_dict(exclude_undefined=True)
                if not v:
                    continue
            config[n] = v
        self.database.set_json_value('config', config)
        self.database.commit()
    
    
    #
    # Method imported from self.database
    #
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
        Asynchronously start the exection of a process in the environment
        defined by self.processing_engine. Returns a string that is an uuid
        of the process execution and can be used to get the status of the 
        execution or wait for its termination.
        
        if history is True, an entry of the process execution is stored in
        the database. The content of this entry is to be defined but it will
        contain the process parameters (to restart the process) and will be 
        updated on process termination (for instance to store execution time
        if possible).
        '''
        raise NotImplementedError()

    def executions(self):
        
        
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
        Return information about a process execution. The content of this
        information is still to be defined.
        '''
        raise NotImplementedError()

    def detailed_information(self, execution_id):
        
    
    def call(self, process, history=True):
        eid = self.start(process, history)
        return self.wait(eid)
    
    def check_call(self, process, history=True):
        eid = self.start(process, history)
        status = self.wait(eid)
        self.raise_for_status(status, eid)

    def raise_for_status(self, status, execution_id=None):
        ...
        
    
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
    
