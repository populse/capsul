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
    section_id_field = 'section_id'
    
    def __init__(self, populse_db):
        self.populse_db = populse_db
        self._dbs = None
        
    def __enter__(self):
        dbs = self.populse_db.__enter__()
        return SettingsSession(dbs)

    def __exit__(self, *args):
        self.populse_db.__exit__(*args)
        self._dbs = None
    
    def config(self, environment, uses=None):
        config = {}
        with self as settings:
            normalized_uses = {}
            if isinstance(uses, dict):
                for k, v in uses.items():
                    normalized_uses[(k if '.' in k else 'capsul.engine.module.' + k)] = v
                config['capsul_engine'] = {'uses': normalized_uses}
            else:
                for collection in (i.collection_name for i in settings._dbs.get_collections()):
                    if collection.startswith(Settings.collection_prefix):
                        section = collection[len(Settings.collection_prefix):]
                        normalized_uses[(section if '.' in section else 'capsul.engine.module.' + section)] = 'ALL'
            for section, query in normalized_uses.items():
                full_query = '%s == "%s" AND (%s)' % (Settings.environment_field, environment, ('ALL' if query == 'any' else query))
                collection = '%s%s' % (Settings.collection_prefix, section)
                if settings._dbs.get_collection(collection):
                    docs = list(settings._dbs.filter_documents(collection, full_query))
                else:
                    docs = []
                if len(docs) == 1:
                    docs[0].pop(Settings.section_id_field)
                    config[section] = docs[0]
                elif len(docs) > 1:
                    if query == 'any':
                        docs[0].pop(Settings.section_id_field)
                        config[section] = docs[0]
                    else:
                        raise EnvironmentError('Cannot create config for environment "%s" because settings returned %d instances for section %s' % (environment, len(docs), section))
                else:
                    full_query = '%s == "%s" AND (%s)' % (Settings.environment_field,
                                                            Settings.global_environment,
                                                            ('ALL' if query == 'any' else query))
                    if settings._dbs.get_collection(collection):
                        docs = list(settings._dbs.filter_documents(collection, full_query))
                    else:
                        docs = []
                    if len(docs) == 1:
                        docs[0].pop(Settings.section_id_field)
                        config[section] = docs[0]
                    elif len(docs) > 1:
                        if query == 'any':
                            docs[0].pop(Settings.section_id_field)
                            config[section] = docs[0]
                        else:
                            raise EnvironmentError('Cannot create config for environment "%s" because global settings returned %d instances for section %s' % (environment, len(docs), section))
        return config
    
    
class SettingsSession:
    def __init__(self, populse_session):
        self._dbs = populse_session

    def new_section(self, environment, section, **kwargs):
        collection = '%s%s' % (Settings.collection_prefix, (section if '.' in section else 'capsul.engine.module.' + section))
        if self._dbs.get_collection(collection) is None:
            self._dbs.add_collection(collection, Settings.section_id_field)
            self._dbs.add_field(collection, Settings.environment_field, 'string', index=True)
        id = str(uuid4())
        document = {
            Settings.section_id_field: id,
            Settings.environment_field: environment}
        document.update(kwargs)
        self._dbs.add_document(collection, document)
        return SettingsSection(self._dbs, collection, id)


class SettingsSection(object):
    def __init__(self, populse_session, collection, id):
        super(SettingsSection, self).__setattr__('_dbs', populse_session)
        super(SettingsSection, self).__setattr__('_collection', collection)
        super(SettingsSection, self).__setattr__('_id', id)

    def __setattr__(self, name, value):
        self._dbs.ensure_field_for_value(self._collection, name, value)
        self._dbs.set_value(self._collection, self._id, name, value)

if __name__ == '__main__':
    from capsul.api import capsul_engine
    from pprint import pprint
    
    ce = capsul_engine()

    with ce.settings as settings:
        # Create a new section object for 'fsl' in 'global' environment
        fsl = settings.new_section('global', 'fsl')
        fsl.version = 5 # Set global FSL version
        
        # Create two global SPM configurations
        settings.new_section('global', 'spm', version=8)
        settings.new_section('global', 'spm', version=12)
        # Create one SPM configuration for 'my_machine'
        settings.new_section('my_machine', 'spm', version=20)
    
    pprint(ce.settings.config('my_machine')) # spm.version = 20, fsl.version = 5
    try:
        ce.settings.config('global')
    except EnvironmentError:
        pass
    else:
        raise RuntimeError('There should be an error here')
    pprint(ce.settings.config('global', uses={'fsl': 'any'}))   
    pprint(ce.settings.config('global', uses={'spm': 'any'}))
    pprint(ce.settings.config('global', uses={'spm': 'version==12'}))
    
    
