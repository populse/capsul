import os.path as osp
import six
import uuid

from soma.serialization import JSONSerializable

from populse_db.database import Database

class PopulseDBEngine(JSONSerializable):
    def __init__(self, database_engine, base_directory=None):
        if base_directory:
            self.base_directory = osp.normpath(osp.abspath(base_directory))
        else:
            self.base_directory = None
        self. db = Database(database_engine)
        with self.db as dbs:
            if not dbs.get_collection('path_metadata'):
                # Create the schema if it does not exists
                dbs.add_collection('path_metadata', 'path')
                dbs.add_field('path_metadata', 'named_directory', 'string', 
                              description='Reference to a base directory whose '
                              'path is stored in named_directory collection')
                
                dbs.add_collection('named_directory', 'name')
                dbs.add_field('named_directory', 'path', 'string')
            
    def set_named_directory(self, name, path):
        with self.db as dbs:
            if path:
                path = osp.normpath(osp.abspath(path))
            doc = dbs.get_document('named_directory', name)
            if doc is None:
                if path:
                    doc = {'name': name,
                           'path': path}
                    dbs.add_document('named_directory', doc)
            else:
                if path:
                    dbs.set_value('named_directory', name, 'path', path)
                else:
                    dbs.remove_documen('named_directory', name)
    
    def named_directory(self, name):
        with self.db as dbs:
            return dbs.get_value('named_directory', name, 'path')
    
    def named_directories(self):
        with self.db as dbs:
            return dbs.filter_documents('named_directory', 'all')
    
        
    def set_path_metadata(self, path, metadata):
        named_directory = metadata.get('named_directory')
        if named_directory:
            base_path = self.named_directory('capsul_engine')
            if base_path:
                if not path.startswith(named_directory):
                    raise ValueError('Path "%s" is defined as relative to named directory %s but it does not start with "%s"' % (path, named_directory, base_path))
                path = path[len(base_path)+1:]
            else:
                if osp.isabs(path):
                    raise ValueError('Cannot determine relative path for "%s" because its base named directory "%s" is unknown' % (path, named_directory))
        else:
            if osp.isabs(path):
                for nd in self.named_directories():
                    if path.startswith(nd.path):
                        named_directory = nd.name()
                        path = path[len(nd.path)+1]
                        break
                else:
                    named_directory = None
            else:
                # capsul_engine is the default named directory for relative paths
                named_directory = 'capsul_engine'

        doc = metadata.copy()
        doc['path'] = path
        if named_directory:
            doc['named_directory'] = named_directory
        with self.db as dbs:
            dbs.add_document('path_metadata', doc)
            

    def path_metadata(self, path):
        if osp.isabs(path):
            for nd in self.named_directories():
                if path.startswith(nd.path):
                    path = path[len(nd.path)+1:]
                    break
        with self.db as dbs:
            return dbs.get_document('path_metadata', path)
