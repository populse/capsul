# -*- coding: utf-8 -*-

'''
This module provides classes to store CapsulEngine settings for several execution environment and choose a configuration for a given execution environment. Setting management in Capsul has several features that makes it different from classical ways to deal with configuration:

* CapsulEngine must be able to deal with several configurations for the same software. For instance, one can configure both SPM 8 and SPM 12 and choose later the one to use.
* A single pipeline may use various configurations of a software. For instance a pipeline could compare the results of SPM 8 and SPM 12.
* Settings definition must be modular. It must be possible to define possible settings values either in Capsul (for well known for instance) or in external modules that can be installed separately.
* Capsul must deal with module dependencies. For instance the settings of SPM may depends on the settings of Matlab. But this dependency exists only if a non standalone SPM version is used. Therefore, dependencies between modules may depends on settings values.
* CapsulEngine settings must provide the possibility to express a requirement on settings. For instance a process may require to have version of SPM greater or equal to 12.
* The configuration of a module can be defined for a specific execution environment. Settings must allow to deal with several executions environments (e.g. a local machine and a computing cluster). Each environment may have a different configuration (for instance the SPM installation directory is not the same on the local computer and on a computing cluster).

To implement all these features, it was necessary to have a settings storage system providing a query language to express requirements such as ``spm.version >= 12``. Populse_db was thus chosen as the storage and query system for settings. Some of the settings API choices have been influenced by populse_db API.

CapsulEngine settings are organized in modules. Each module defines and documents the schema of values that can be set for its configuration. Typically, a module is dedicated to a software. For instance the module for SPM accepts confiurations containing a version (a string), an install directory (a string), a standalone/matlab flag (a boolean), etc. This schema is used to record configuration documents for the module. There can be several configuration documents per module. Each document corresponds to a full configuration of the module (for instance a document for SPM 8 configuration and another for SPM 12, or one for SPM 12 standalone and another for SPM 12 with matlab).

Settings cannot be used directly to configure the execution of a software. It is necessary to first select a single configuration document for each module. This configurations selection step is done by the :meth:`Settings.select_configurations` method.

'''

#
# Questions about settings
# How to automatically build a GUI to input settings values ?
# * default values
# * mandatory / optional settings
# * dependencies between settings
#
# all these were "simple" using Controllers but are in a way "too free" now,
# and "too constrained" in another way (table columns: not dicts or structures)
#
# config modules might provide validation functions (check consistency,
# completeness of config values), and maybe a Controller to build a GUI ?
#
# How to store additional data indirectly linked with settings values ?
# Some modules were using objects shared through StudyConfig.modules_data
# (or CapsulEngine).
#
# doc on modules activation / use ?
#

import importlib
from uuid import uuid4


class Settings:
    '''
    Main class for the management of CapsulEngine settings. Since these
    settings are always stored in a populse_db database, it is necessary to
    activate a settings session in order to read or modify settings. This is
    done by using a with clause::

        from capsul.api import capsul_engine

        # Create a CapsulEngine
        ce = capsul_engine()
        with ce.settings as settings:
            # Read or modify settings here
            conf = settings.new_config('spm', 'global',
                                       {'version': '12', 'standalone': True})
            # modify value
            conf.directory = '/usr/local/spm12-standalone'
    '''

    global_environment = 'global'
    collection_prefix = 'settings/'
    environment_field = 'config_environment'
    config_id_field = 'config_id'

    def __init__(self, populse_db):
        '''
        Create a settings instance using the given populse_db instance
        '''
        self.populse_db = populse_db
        self.module_notifiers = {}

    def __enter__(self):
        '''
        Starts a session to read or write settings
        '''
        dbs = self.populse_db.__enter__()
        return SettingsSession(dbs, module_notifiers=self.module_notifiers)

    def __exit__(self, *args):
        self.populse_db.__exit__(*args)

    @staticmethod
    def module_name(module_name):
        '''
        Return a complete module name (which must be a valid Python module
        name) given a possibly abbreviated module name. This method must
        be used whenever a module name is written by a user (for instance
        in a configuration file.
        This method add the prefix `'capsul.engine.module.'` if the module
        name does not contain a dot.
        '''
        if '.' not in module_name:
            module_name = 'capsul.engine.module.' + module_name
        return module_name
    
    def select_configurations(self, environment, uses=None):
        '''
        Select a configuration for a given environment. A configuration is
        a dictionary whose keys are module names and values are
        configuration documents. The returned set of configuration per module
        can be activaded with `capsul.api.activate_configuration()`.
        
        The `uses` parameter determine which modules
        must be included in the configuration. If not given, this method 
        considers all configurations for every module defined in settings.
        This parameter is a dictionary whose keys are a module name and
        values are populse_db queries used to select module.
        
        The environment parameter defines the execution environment in which
        the configurations will be used. For each module, configurations are
        filtered with the query. First, values are searched in the given
        environment and, if no result is found, the `'global'` environment
        (the value defined in `Settings.global_environment`) is used.
        
        example
        -------
        To select a SPM version greater than 8 for an environment called
        `'my_environment'` one could use the following code::

            config = ce.select_configurations('my_environment',
                                              uses={'spm': 'version > 8'})
        '''
        configurations = {}
        with self as settings:
            if uses is None:
                uses = {}
                for collection in (i.collection_name 
                                   for i in 
                                   settings._dbs.get_collections()):
                    if collection.startswith(Settings.collection_prefix):
                        module_name = \
                            collection[len(Settings.collection_prefix):]
                        uses[module_name] = 'ALL'
            uses_stack = list(uses.items())
            while uses_stack:
                module, query = uses_stack.pop(-1)
                module = self.module_name(module)
                if module in configurations:
                    continue
                configurations.setdefault('capsul_engine', 
                                          {}).setdefault('uses', 
                                                         {})[module] = query
                selected_config = None
                full_query = '%s == "%s" AND (%s)' % (
                    Settings.environment_field, environment, (
                        'ALL' if query == 'any' else query))
                collection = '%s%s' % (Settings.collection_prefix, module)
                if settings._dbs.get_collection(collection):
                    docs = list(settings._dbs.filter_documents(collection, 
                                                               full_query))
                else:
                    docs = []
                if len(docs) == 1:
                    selected_config = docs[0]
                elif len(docs) > 1:
                    if query == 'any':
                        selected_config = docs[0]
                    else:
                        raise EnvironmentError('Cannot create configurations '
                            'for environment "%s" because settings returned '
                            '%d instances for module %s' % (environment, 
                                                            len(docs), module))
                else:
                    full_query = '%s == "%s" AND (%s)' % (Settings.environment_field,
                                                          Settings.global_environment,
                                                          ('ALL' if query == 'any' 
                                                           else query))
                    if settings._dbs.get_collection(collection):
                        docs = list(settings._dbs.filter_documents(collection, 
                                                                   full_query))
                    else:
                        docs = []
                    if len(docs) == 1:
                        selected_config = docs[0]
                    elif len(docs) > 1:
                        if query == 'any':
                            selected_config = docs[0]
                        else:
                            raise EnvironmentError('Cannot create '
                                'configurations for environment "%s" because '
                                'global settings returned %d instances for '
                                'module %s' % (environment, len(docs),
                                               module))
                if selected_config:
                    # Remove values that are None
                    items = getattr(selected_config, '_items', None)
                    if items is None:
                        # older populse_db 1.x
                        items = selected_config.items
                    selected_config = dict(items())
                    for k, v in list(items()):
                        if v is None:
                            del selected_config[k]
                    configurations[module] = selected_config
                    python_module = importlib.import_module(module)
                    config_dependencies = getattr(python_module, 
                                                  'config_dependencies', 
                                                  None)
                    if config_dependencies:
                        d = config_dependencies(selected_config)
                        if d:
                            uses_stack.extend(
                                [(Settings.module_name(k), v)
                                 for k, v in d.items()])

        return configurations

    def import_configs(self, environment, config_dict):
        '''
        Import config values from a dictionary as given by
        :meth:`select_configurations`.

        Compared to :meth:`CapsulEngine.import_configs` this method (at
        :class:`Settings` level) does not load the required modules.
        '''
        modules = config_dict.get('capsul_engine', {}).get('uses', {})

        with self as session:
            for module in modules:
                mod_dict = config_dict.get(module, {})
                if mod_dict:
                    config_id = mod_dict.get('config_id', '')
                    conf = session.config(
                        module, environment, 'config_id == "%s"' % config_id)
                    if conf:
                        values = {k: v for k, v in mod_dict.items()
                                  if k not in ('config_id',
                                               'config_environment')}
                        conf.set_values(values)
                    else:
                        session.new_config(module, environment, mod_dict)

    def get_all_environments(self):
        '''
        Get all environment values in the database
        '''
        with self as session:
            return session.get_all_environments()
    
    
class SettingsSession:
    '''
    Settings use/modifiction session, returned by "with settings as session:"
    '''

    def __init__(self, populse_session, module_notifiers=None):
        '''
        SettingsSession are created with Settings.__enter__ using a `with`
        statement.
        '''
        self._dbs = populse_session
        if module_notifiers is None:
            self.module_notifiers = {}
        else:
            self.module_notifiers = module_notifiers

    @staticmethod
    def collection_name(module):
        '''
        Return the name of the populse_db collection corresponding to a
        settings module. The result is the full name of the module 
        prefixed by Settings.collection_prefix (i.e. `'settings/'`).
        '''
        module = Settings.module_name(module)
        collection = '%s%s' % (Settings.collection_prefix, module)
        return collection
    
    def ensure_module_fields(self, module, fields):
        '''
        Make sure that the given module exists in settings and create the given fields if they do not exist. `fields` is a list of dictionaries with three items:
        - name: the name of the key
        - type: the data type of the field (in populse_db format)
        - description: the documentation of the field
        '''
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is None:
            self._dbs.add_collection(collection, Settings.config_id_field)
            self._dbs.add_field(collection, 
                                Settings.environment_field, 
                                'string', index=True)
        for field in fields:
            name = field['name']
            if self._dbs.get_field(collection, name) is None:
                self._dbs.add_field(collection, name=name,
                                    field_type=field['type'],
                                    description=field['description'])
        return collection
    
    def new_config(self, module, environment, values):
        '''
        Creates a new configuration document for a module in the given 
        environment. Values is a dictionary used to set values for the 
        document. The document mut have a unique string identifier in 
        the `Settings.config_id_field` (i.e. `'config_id'`), if None is
        given in `values` a unique random value is created (with 
        `uuid.uuid4()`).
        '''
        document = {
            Settings.environment_field: environment}
        document.update(values)
        id = document.get(Settings.config_id_field)
        if id is None:
            id = str(uuid4())
            document[Settings.config_id_field] = id
        collection = self.collection_name(module)
        self._dbs.add_document(collection, document)
        config = SettingsConfig(
            self._dbs, collection, id,
            notifiers=self.module_notifiers.get(Settings.module_name(module),
                                                []))
        config.notify()
        return config

    def remove_config(self, module, environment, config_id):
        '''
        Removes a configuration (document in the database) for a given module /
        environment, idenfified by its `Settings.config_id_field` value.
        '''
        collection = self.collection_name(module)
        self._dbs.remove_document(collection, config_id)

    def configs(self, module, environment, selection=None):
        '''
        Returns a generator that iterates over all configuration
        documents created for the given module and environment.
        '''
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is not None:
            if selection:
                full_query = '%s == "%s" AND (%s)' % (
                    Settings.environment_field, environment, selection)
                docs = self._dbs.filter_documents(collection, full_query)
            else:
                docs = self._dbs.filter_documents(
                    collection,
                    '%s=="%s"' % (Settings.environment_field, environment))
            for d in docs:
                id = d[Settings.config_id_field]
                yield SettingsConfig(
                    self._dbs, collection, id,
                    notifiers=self.module_notifiers.get(Settings.module_name(
                        module), []))

    def config(self, module, environment, selection=None, any=True):
        '''
        Selects configurations (like in :meth:`congigs`) and ensures at most
        one one is selected

        Parameters
        ----------
        module: str
            module name
        environment: str
            environment id ('global' etc)
        selection: str (optional)
            to select the configuration
        any: bool (optional)
            When more than one config is found, if ``any`` is True (default),
            return any of them (the first one). If ``any`` is False, return
            None.

        Returns
        -------
        config: SettingsConfig instance or None
            None if no matching config is found or more than one if any is
            False
        '''
        configs = list(self.configs(module, environment, selection))
        if len(configs) == 0:
            return None
        if len(configs) == 1 or any:
            return configs[0]
        return None

    def get_all_environments(self):
        '''
        Get all environment values in the database
        '''
        # TODO FIXME
        # this function uses low-level SQL requests on the sql engine of
        # populse_db 2, because I don't know how to perform requests with the
        # "DISTINCT" keyword using the high level requests language. It will
        # not work using populse_db 1 nor using another (non-SQL)
        # implementation of the database engine.
        environments = set()
        for collection in (i.collection_name
                           for i in self._dbs.get_collections()):
            if collection.startswith(Settings.collection_prefix):
                #collection = collection[len(Settings.collection_prefix):]
                table = self._dbs.engine.collection_table[collection]
                #full_query = '%s == "%s"' % (
                    #Settings.environment_field, environment)
                #docs = self._dbs.filter_documents(collection, full_query)
                query = 'SELECT DISTINCT %s FROM "%s"' \
                    % (Settings.environment_field, table)
                res = self._dbs.engine.cursor.execute(query)
                environments.update([r[0] for r in res])
        return environments

class SettingsConfig(object):
    def __init__(self, populse_session, collection, id, notifiers=[]):
        super(SettingsConfig, self).__setattr__('_dbs', populse_session)
        super(SettingsConfig, self).__setattr__('_collection', collection)
        super(SettingsConfig, self).__setattr__('_id', id)
        super(SettingsConfig, self).__setattr__('_notifiers', notifiers)

    def __setattr__(self, name, value):
        if getattr(self, name) != value:
            self._dbs.set_value(self._collection, self._id, name, value)
            # notify change for listeners
            self.notify(name, value)

    def __getattr__(self, name):
        return self._dbs.get_value(self._collection, self._id, name)

    def set_values(self, values):
        old = self._dbs.get_document(self._collection, self._id,
                                     fields=values.keys(), as_list=True)
        mod_values = {k: v for o, (k, v) in zip(old, values.items()) if o != v}
        if mod_values:
            self._dbs.set_values(self._collection, self._id, mod_values)
            for name, value in mod_values.items():
                self.notify(name, value)

    def notify(self, name=None, value=None):
        for notifier in self._notifiers:
            notifier(name, value)
    
