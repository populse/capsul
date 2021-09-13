# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os.path as osp

class DatabaseEngine(object):
    '''
    A :py:class:`DatabaseEngine` is the base class for all engines 
    allowing to store, retrieve and search metadata associated with
    a key that can be either a string or a path (i.e. a file or directory
    name).
    
    To instantiate a :py:class:`DatabaseEngine` one must use the factory 
    To date, two concrete :py:class:`DatabaseEngine` implementations exist:

    - :py:class:`capsul.engine.database_json.JSONDBEngine`
    - :py:class:`capsul.engine.database_populse.PopulseDBEngine`
    
    '''
    
    def check_path_metadata(self, path, metadata, named_directory=None):
        named_directory = metadata.get('named_directory')
        named_directory, path = self.check_path(path, named_directory)
        
        doc = metadata.copy()
        doc['path'] = path
        doc['named_directory'] = named_directory
        return doc

    def check_path(self, path, named_directory=None):
        '''
        Find a pair (named_directory, path) given a path and eventually a
        named_directory.
        
        If named_directory is not given, path must be absolute or a 
        ValueError is raised. Then, either the corresponding named 
        directory is found or 'absolute' is used.
        
        If name_directory is given, the path must be relative (unless
        named_directory == 'absolute') or begin with the path of the 
        named directory.
        '''
        if named_directory is None:
            if osp.isabs(path):
                for nd in self.named_directories():
                    base_path = nd['path']
                    if path.startswith(base_path):
                        named_directory = nd['name']
                        path = path[len(base_path)+1:]
                        break
                else:
                    named_directory = 'absolute'
            else:
                raise ValueError('Cannot determine base named directory for relative path "%s"' % path)
        else:
            if named_directory == 'absolute':
                if not osp.isabs(path):
                    raise ValueError('Using "absolute" named directory requires an absolute path, not "%s"' % path)
            else:
                base_path = self.named_directory(named_directory)
                if base_path is None:
                    raise ValueError('Unknown named directory "%s"' % named_directory)
                if osp.isabs(path):
                    if not path.startswith(base_path):
                        raise ValueError('Path "%s" is defined as relative to named directory %s but it does not start with "%s"' % (path, named_directory, base_path))
                    path = path[len(base_path)+1:]
        return (named_directory, path)
    
    
    def set_json_value(self, name, json_value):
        '''
        Store a json value and associate it with a key given in "name".
        The value can be retrieved with method json_value().
        
        @param name: unique key used to identify and retrieve the value
        @type name: C{string}
        @param json_value: a value to store in the database
        @type  name: any JSON compatible value
        '''
        raise NotImplementedError()

    def json_value(self, name):
        '''
        Retrieve a value previously stored with set_json_value()
        '''
        raise NotImplementedError()
        
    
    def set_named_directory(self, name, path):
        '''
        Associate an absolute path to a generic name. This allow to always
        use a location independent name for a directory such as 'spm_template'
        and to customize the real absolute path in the configuration. These 
        named directories are used when setting/retrieving path metadata with 
        set_path_metadata() and path_metadata().
        '''
        raise NotImplementedError()
    
    def named_directory(self, name):
        '''
        Return the absolute path of a named directory.
        '''
        raise NotImplementedError()
    
    def named_directories(self):
        '''
        List the names of all named directories. This method may return any
        iterable value (list, generator, etc.)
        '''
        raise NotImplementedError()
    
    
    def set_path_metadata(self, path, metadata, named_directory=None):
        '''
        Set metadata associated to a path. The metadata are associated to the
        result of self.check_path(path, named_directory). metadata can be any
        JSON serializable value.
        '''
        raise NotImplementedError()
    
    def path_metadata(self, path, named_directory=None):
        '''
        Retrieve metadata associated with a path.
        '''
        raise NotImplementedError()
