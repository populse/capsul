# -*- coding: utf-8 -*-

from soma.controller import (Controller, Directory, field,
                             OpenKeyDictController, File)
import os
import sys


class ModuleConfiguration(Controller):
    ''' Module-level configuration object.

    This base class is meant to be inherited in specific modules
    (:class:`SPMConfiguration` etc).
    '''
    name: str

    def is_valid_config(self, requirements):
        ''' Checks validity of this config in regard to given requirements
        '''
        raise NotImplementedError('A subclass of ModuleConfiguration must '
                                  'define is_valid_config()')

    def init_execution_context(execution_context):
        '''
        Configure an execution context given a capsul_engine and some
        requirements.
        '''
        raise NotImplementedError('A subclass of ModuleConfiguration must '
                                  'define init_execution_context()')


class EngineConfiguration(Controller):
    ''' Engine-level configuration object

    It corresponds to a given computing resource in the
    :class:`ApplicationConfiguration`. It contains modules and instances of
    :class:`ModuleConfiguration` for each module config. A module may contain
    several config instances (for instance SPM12 and SPM8 may be configured).

    Modules keys should correspond to their module name, however it should not
    include dots as they are field names, so we either take the "short name",
    or replace dots with underscores.
    '''
    # maybe modules should be replaced by indiviudual fields for each module,
    # in order to:
    # - have a constrained list of modules (keys)
    # - force each module dict/controller to use its own ModuleConfiguration
    #   subclass and no other

    # key -> nom du fichier de module. spm -> capsul.config.spm
    #modules: dict[str, dict[str, ModuleConfiguration]] \
        #= field(default_factory=dict)
    
    modules: OpenKeyDictController[OpenKeyDictController[
        ModuleConfiguration]] \
        = field(default_factory=OpenKeyDictController[OpenKeyDictController[
            ModuleConfiguration]])

    #modules = {'capsul.config.spm': {
        #'12': {
            #'version': 12,
            #'directory': '/somewhere'
            #'standalone'},
        #'12_bis': {
            #'version': 12,
            #'directory': '/elsewhere'
            #'standalone'},
        #'8': {'version': 8,
         #'directory': '/nowhere'},
    #}}

    def connect():
        ...


class ConfigurationLayer(OpenKeyDictController[EngineConfiguration]):
    ''' Configuration "layer", which represents a config file (site config or
    user config, typically).

    A ConfigurationLayer contains sub-configs corresponding to computing
    resources, which are keys in this :class:`Controller`. A "default" config
    resource could be named "local".
    '''
    #engines: dict[str, EngineConfiguration]
    #engines: OpenKeyDictController[EngineConfiguration]

    def load(self, filename):
        ''' Load configuration from a JSON or YAML file
        '''
        import json
        with open(filename) as f:
            try:
                site_conf = json.load(f)
            except Exception as e:  # FIXME: find better exception filter
                try:
                    import yaml
                    site_conf = yaml.safe_load(f)
                except ImportError:
                    raise e

        self.import_dict(site_conf)

    def save(self, filename, format='json'):
        ''' Save configuration to a JSON or YAML file
        '''
        if format == 'json':
            import json
            with open(filename, 'w') as f:
                json.dump(self.asdict(), f)
        elif format == 'yaml':
            import yaml
            with open(filename, 'w') as f:
                yaml.dump(self.asdict(), f)
        else:
            raise ValueError('Unsupported format: %s' % format)

    def merge(self, other_layer):
        ''' Merge in-place: other_layer is "added" to self.
        TODO
        '''
        ...

    def merged(self, other_layer):
        ''' Returns a merged copy of self and another ConfigurationLayer layer
        '''
        merged = self.copy()
        merged.merge(other_layer)
        return merged


class ApplicationConfiguration(Controller):
    ''' Application-wide configuration class.

    It contains a "site" and a "user" configuration, and a merge of both (TODO)
    '''
    site_file: File
    site: ConfigurationLayer = field(default_factory=ConfigurationLayer)
    user_file: File
    user: ConfigurationLayer = field(default_factory=ConfigurationLayer)
    app_name: str = 'capsul'
    
    # read-only modified by merge
    merged_config: ConfigurationLayer = field(
        default_factory=ConfigurationLayer)
    
    def __init__(self, app_name, user_file=None, site_file=None):
        super().__init__()

        self.app_name = app_name

        if site_file is not None:
            self.site_file = site_file
            try:
                self.site.load(site_file)
            except Exception as e:
                print('Loading site configuration file has failed:', e,
                      file=sys.stderr)

        if user_file is None:
            user_file = os.path.expanduser('~/.config/%s.conf' % app_name)
        try:
            self.user.load(user_file)
        except Exception as e:
            print('Loading user configuration file has failed:', e,
                  file=sys.stderr)

        self.merged_config = self.site.merged(self.user)
    

    def available_modules(self):
        ...

    
## app_config -> engine_config -> module spm -> directory

#app_config.engines['local'].modules['spm']['12'].directory
# app_config.user.local = cf.EngineConfiguration()
