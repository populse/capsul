# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import os.path as osp
import six
import uuid
import json

from capsul.engine.database import DatabaseEngine

class JSONDBEngine(DatabaseEngine):
    '''
    A JSON dictionary implementation of :py:class:`capsul.engine.database.DatabaseEngine`
    '''
    def __init__(self, json_filename):
        if json_filename is not None:
            self.json_filename = osp.normpath(osp.abspath(json_filename))
        else:
            self.json_filename = None
        self.read_json()
    
    def read_json(self):
        if self.json_filename is not None and osp.exists(self.json_filename):
            self.json_dict = json.load(open(self.json_filename))
            self.modified = False
        else:
            self.json_dict = {}
            self.modified = True
            
    def commit(self):
        if self.modified and self.json_filename is not None:
            parent = osp.dirname(self.json_filename)
            if not osp.exists(parent):
                os.makedirs(parent)
            json.dump(self.json_dict, open(self.json_filename, 'w'), indent=2)
            self.modified = False

    def rollback(self):
        self.read_json()
    
    
    def set_named_directory(self, name, path):
        if path:
            path = osp.normpath(osp.abspath(path))
            self.json_dict.setdefault('named_directory', {})[name] = {'name': name,
                                                                      'path': path}
            self.modified = True
        else:
            named_directory = self.json_dict.get('named_directory')
            if named_directory is not None:
                named_directory.pop(name, None)
                self.modified = True

    def named_directory(self, name):
        return self.json_dict.get('named_directory', {}).get(name, {}).get('path')
    
    def named_directories(self):
        return self.json_dict.get('named_directory', {}).values()
    
        
    def set_json_value(self, name, json_value):
        self.json_dict.setdefault('json_value', {})[name] = json_value
        self.modified = True

    def json_value(self, name):
        return self.json_dict.get('json_value', {}).get(name)
    
    
    def set_path_metadata(self, path, metadata, named_directory=None):
        metadata = self.check_path_metadata(path, metadata, named_directory)
        path = metadata['path']
        named_directory = metadata['named_directory']
        self.json_dict.setdefault('path_metadata', {})[
            (named_directory, path)] = metadata
        self.modified = True
            

    def path_metadata(self, path, named_directory=None):
        named_directory, path = self.check_path(path, named_directory)
        return self.json_dict.get('path_metadata', {}).get((named_directory, path))
