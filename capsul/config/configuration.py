# -*- coding: utf-8 -*-

from soma.controller import (Controller, Directory, field,
                             OpenKeyDictController, File, undefined)
import os
import sys
import importlib


def full_module_name(module_name):
    '''
    Return a complete module name (which must be a valid Python module
    name) given a possibly abbreviated module name. This method must
    be used whenever a module name is written by a user (for instance
    in a configuration file.
    This method add the prefix `'capsul.engine.module.'` if the module
    name does not contain a dot.
    '''
    if '.' not in module_name:
        module_name = 'capsul.config.' + module_name
    return module_name


class ModuleConfiguration(Controller):
    ''' Module-level configuration object.

    This base class is meant to be inherited in specific modules
    (:class:`SPMConfiguration` etc).
    '''
    name = ''

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
    
    #modules: OpenKeyDictController[OpenKeyDictController[
        #ModuleConfiguration]] \
        #= field(default_factory=OpenKeyDictController[OpenKeyDictController[
            #ModuleConfiguration]])

    def add_module(self, module_name):
        # print('add_module:', module_name)
        full_mod = full_module_name(module_name)

        python_module = importlib.import_module(full_mod)
        if python_module is None:
            raise ValueError('Module %s cannot be loaded.' % full_mod)

        module_name = module_name.rsplit('.')[-1]
        classes = []
        for c in python_module.__dict__.values():
            if c is ModuleConfiguration:
                continue
            try:
                if issubclass(c, ModuleConfiguration):
                    classes.append(c)
            except TypeError:
                pass
        if len(classes) == 0:
            raise ValueError('No ModuleClass found in module %s' % module_name)
        if len(classes) > 1:
            raise ValueError('Several ModuleClass found (%d) in module %s: %s'
                             % (len(classes), module_name, repr(classes)))
        cls = classes[0]
        self.add_field(module_name, OpenKeyDictController[cls],
                       doc=cls.__doc__,
                       default_factory=OpenKeyDictController[cls])

    def remove_module(self, module_name):
        module_name = module_name.rsplit('.')[-1]
        if self.field(module_name) is not None:
            self.remove_field(module_name)

    def import_dict(self, conf_dict, clear=False):
        # insert modules before filling them in
        for mod in conf_dict:
            self.add_module(mod)
        super().import_dict(conf_dict, clear=clear)

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
                conf = json.load(f)
            except Exception as e:  # FIXME: find better exception filter
                import traceback
                traceback.print_exc()
                try:
                    import yaml
                    conf = yaml.safe_load(f)
                except ImportError:
                    raise e

        print('import config:', conf)
        self.import_dict(conf)

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
        '''
        self.import_dict(other_layer.asdict(), clear=False)

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
        if user_file is not undefined:
            try:
                self.user.load(user_file)
            except Exception as e:
                print('Loading user configuration file has failed:', e,
                      file=sys.stderr)

        self.merged_config = self.site.merged(self.user)
        self._loaded_modules = set()
    

    def available_modules(self):
        ...

    def add_module_in_all_configs(self, module_name):
        for layer in (self.site, self.user):
            for env_field in layer.fields():
                env = env_field.name
                econf = getattr(layer, env)
                if econf.field( module_name) is None:
                    econf.add_module(module_name)


    
## app_config -> engine_config -> module spm -> directory

#app_config.engines['local'].modules['spm']['12'].directory
# app_config.user.local = cf.EngineConfiguration()
