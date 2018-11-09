import os.path as osp

class DatabaseEngine:            
    def check_path_metadata(self, path, metadata, named_directory=None):
        named_directory = metadata.get('named_directory')
        named_directory, path = self.check_path(path, named_directory)
        
        doc = metadata.copy()
        doc['path'] = path
        doc['named_directory'] = named_directory
        return doc

    def check_path(self, path, named_directory=None):
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
    
    
    def set_named_directory(self, name, path):
        raise NotImplementedError()
    
    def named_directory(self, name):
        raise NotImplementedError()
    
    def named_directories(self):
        raise NotImplementedError()
    
    
    def set_json_value(self, name, json_value):
        raise NotImplementedError()

    def json_value(self, name):
        raise NotImplementedError()
        
    
    def set_path_metadata(self, path, metadata, named_directory=None):
        raise NotImplementedError()
    
    def path_metadata(self, path, named_directory=None):
        raise NotImplementedError()

