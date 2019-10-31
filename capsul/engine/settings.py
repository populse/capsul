import importlib
from uuid import uuid4

class Settings:
    '''
    CapsulEngine settings are stored in a populse_db database. This
    class manage all interactions with configuration providing Pythonic
    API and hiding details used to store elements in populse_db (such as
    collection names).
    '''
    
    global_environment = 'global'
    collection_prefix = 'settings/'
    environment_field = 'config_environment'
    config_id_field = 'config_id'
    
    def __init__(self, populse_db):
        self.populse_db = populse_db
        self._dbs = None
        
    def __enter__(self):
        dbs = self.populse_db.__enter__()
        return SettingsSession(dbs)

    def __exit__(self, *args):
        self.populse_db.__exit__(*args)
        self._dbs = None
    
    @staticmethod
    def module_name(module_name):
        if '.' not in module_name:
            module_name = 'capsul.engine.module.' + module_name
        return module_name
    
    def select_configurations(self, environment, uses=None):
        configurations = {}
        with self as settings:
            if uses is None:
                uses = {}
                for collection in (i.collection_name for i in settings._dbs.get_collections()):
                    if collection.startswith(Settings.collection_prefix):
                        module_name = collection[len(Settings.collection_prefix):]
                        uses[module_name] = 'ALL'
            uses_stack = list(uses.items())
            while uses_stack:
                module, query = uses_stack.pop(-1)
                module = self.module_name(module)
                if module in configurations:
                    continue
                configurations.setdefault('capsul_engine', {}).setdefault('uses', {})[module] = query
                selected_config = None
                full_query = '%s == "%s" AND (%s)' % (Settings.environment_field, environment, ('ALL' if query == 'any' else query))
                collection = '%s%s' % (Settings.collection_prefix, module)
                if settings._dbs.get_collection(collection):
                    docs = list(settings._dbs.filter_documents(collection, full_query))
                else:
                    docs = []
                if len(docs) == 1:
                    selected_config = docs[0]
                elif len(docs) > 1:
                    if query == 'any':
                        selected_config = docs[0]
                    else:
                        raise EnvironmentError('Cannot create configurations for environment "%s" because settings returned %d instances for module %s' % (environment, len(docs), module))
                else:
                    full_query = '%s == "%s" AND (%s)' % (Settings.environment_field,
                                                          Settings.global_environment,
                                                          ('ALL' if query == 'any' else query))
                    if settings._dbs.get_collection(collection):
                        docs = list(settings._dbs.filter_documents(collection, full_query))
                    else:
                        docs = []
                    if len(docs) == 1:
                        selected_config = docs[0]
                    elif len(docs) > 1:
                        if query == 'any':
                            selected_config = docs[0]
                        else:
                            raise EnvironmentError('Cannot create configurations for environment "%s" because global settings returned %d instances for module %s' % (environment, len(docs), module))
                if selected_config:
                    # Remove values that are None
                    for k, v in list(selected_config.items()):
                        if v is None:
                            del selected_config[k]
                    configurations[module] = selected_config
                    python_module = importlib.import_module(module)
                    config_dependencies = getattr(python_module, 'config_dependencies', None)
                    if config_dependencies:
                        d = config_dependencies(selected_config)
                        if d:
                            uses_stack.extend(list(d.items()))
        return configurations
    
    
class SettingsSession:
    def __init__(self, populse_session):
        self._dbs = populse_session

    @staticmethod
    def collection_name(module):
        module = Settings.module_name(module)
        collection = '%s%s' % (Settings.collection_prefix, module)
        return collection
    
    def ensure_module_fields(self, module, fields):
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is None:
            self._dbs.add_collection(collection, Settings.config_id_field)
            self._dbs.add_field(collection, Settings.environment_field, 'string', index=True)
        for field in fields:
            name = field['name']
            if self._dbs.get_field(collection, name) is None:
                self._dbs.add_field(collection, name=name,
                                    field_type=field['type'],
                                    description=field['description'])
        return collection
    
    def new_config(self, module, environment, values):
        document = {
            Settings.environment_field: environment}
        document.update(values)
        id = document.get(Settings.config_id_field)
        if id is None:
            id = str(uuid4())
            document[Settings.config_id_field] = id
        collection = self.collection_name(module)
        self._dbs.add_document(collection, document)
        return SettingsConfig(self._dbs, collection, id)

    def configs(self, module, environment):
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is not None:
            for d in self._dbs.find_documents(collection, 
                                              '%s=="%s"' % (Settings.environment_field, environment)):
                id = d[Settings.config_id_field]
                yield SettingsConfig(self._dbs, collection, id)


class SettingsConfig(object):
    def __init__(self, populse_session, collection, id):
        super(SettingsConfig, self).__setattr__('_dbs', populse_session)
        super(SettingsConfig, self).__setattr__('_collection', collection)
        super(SettingsConfig, self).__setattr__('_id', id)

    def __setattr__(self, name, value):
        self._dbs.set_value(self._collection, self._id, name, value)
    
    def __getattr__(self, name):
        return self._dbs.get_value(self._collection, self._id, name)
    
