'''
This module defines the main API to interact with Capsul processes.
In order to execute a process, it is mandatory to have an instance of
:py:class:`Platform`. Such an instance can be created with constructor
or by using a JSON representation of the instance (created by 
:py:meth:`Platform.to_json`) with
:py:func:`soma.serialization.from_json`
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
    default_modules = ['capsul.engine.module.spm',
                       'capsul.engine.module.fsl']
        
    def __init__(self, 
                 database_location,
                 database,
                 config=None):
        '''
        CapsulEngine constructor should not be called directly.
        Use engine() factory function instead.
        '''
        super(CapsulEngine, self).__init__()
        
        self._database_location = database_location
        self._database = database

        self.study_config = StudyConfig()
        
        db_config = database.json_value('config')
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
        if self.modules is None:
            modules = self.default_modules
        else:
            modules = self.modules
        
        self._loaded_modules = {}
        for module in modules:
            self.load_module(module)
            
    def load_module(self, module):
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
        if self.modules is None:
            modules = self.default_modules
        else:
            modules = self.modules
        for module in modules:
            self.init_module(module)
    
    def init_module(self, module):
        python_module = sys.modules.get(module)
        if python_module is None:
            raise ValueError('Cannot find %s in Python modules' % module)
        initializer = getattr(python_module, 'init_module', None)
        if initializer is None:
            raise ValueError('No function init_module() defined in %s' % module)
        initializer(self, module, self._loaded_modules[module])
    
    def save(self):
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



    def get_process_instance(self, process_or_id, **kwargs):
        '''
        The supported way to get a process instance is to use this method.
        For now, it simply calls self.study_config.get_process_instance
        but it will change in the future.
        '''
        instance = self.study_config.get_process_instance(process_or_id,
                                                          **kwargs)
        return instance


_populsedb_url_re = re.compile(r'^\w+(\+\w+)?://(.*)')
def database_factory(database_location):
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
    User facrory for creating capsul engines
    '''
    if database_location is None:
        database_location = osp.expanduser('~/.config/capsul/capsul_engine.json')
    database = database_factory(database_location)
    capsul_engine = CapsulEngine(database_location, database, config=config)
    return capsul_engine
    
