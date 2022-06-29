# -*- coding: utf-8 -*-

import json
import os
import sys
import importlib

from soma.controller import (Controller, field,
                             OpenKeyDictController, File)
from soma.undefined import undefined

from ..dataset import Dataset

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


def get_config_class(module_name, exception=True):
    full_mod = full_module_name(module_name)

    try:
        python_module = importlib.import_module(full_mod)
    except ModuleNotFoundError:
        if exception:
            raise
        else:
            return None

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
        if exception:
            raise ValueError(f'No ModuleClass found in module {module_name}')
        else:
            return None
    if len(classes) > 1:
        if exception:
            raise ValueError(f'Several ModuleClass found {len(classes)} in module {module_name}: {classes}')
        else:
            return None
    return classes[0]


class ModuleConfiguration(Controller):
    ''' Module-level configuration object.

    This base class is meant to be inherited in specific modules
    (:class:`~spm.SPMConfiguration` etc).

    A configuration module should be written this way:

    - be in a python module file which contains one, and only one, subclass of
      ``ModuleConfiguration``.

    - the subclass should declare its own configuration parameters using
      fields, and overload the method :meth:`is_valid_config` to check if a
      requirements dictionary matches the current config module parameterss.

    - the subclass may declare an attribute ``module_dependencies`` which is a
      list of other module names which it depends on: these modules will be
      also added to the configuration.

    - declare a static method ``init_execution_context(execution_context)``
      which takes an :class:`~capsul.execution_context.ExecutionContext`
      object. It should extract from the context configuration dict
      (execution_context.config) its own module config, and do whatever is
      needed to configure things and/or add in the context itself things that
      can be used during execution.
    '''
    name = ''

    def is_valid_config(self, requirements):
        ''' Checks validity of this config in regard to given requirements
        '''
        raise NotImplementedError('A subclass of ModuleConfiguration must '
                                  'define is_valid_config()')


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

    dataset: OpenKeyDictController[Dataset]
    config_modules: list[str]
    python_modules: list[str]
    engine_type: str = 'builtin'

    def add_module(self, module_name, allow_existing=False):
        ''' Loads a modle and adds it in the engine configuration.

        This operation is performed automatically, thus should not need to be
        called manually.
        '''
        cls = get_config_class(module_name)
        old_module_name = module_name
        module_name = getattr(cls, 'name', module_name.rsplit('.')[-1])
        if not module_name:
            # fallback
            module_name = old_module_name.rsplit('.')[-1]

        if allow_existing:
            field = self.field(module_name)
            if field is not None and field.type is OpenKeyDictController[cls]:
                return

        self.add_field(module_name, OpenKeyDictController[cls],
                       doc=cls.__doc__,
                       default_factory=OpenKeyDictController[cls])

        if hasattr(cls, 'module_dependencies'):
            module_dependencies = getattr(cls, 'module_dependencies')
            for dependency in module_dependencies:
                self.add_module(dependency, allow_existing=True)

    def remove_module(self, module_name):
        ''' Remove the given module
        '''
        module_name = module_name.rsplit('.')[-1]
        if self.field(module_name) is not None:
            self.remove_field(module_name)

    def import_dict(self, conf_dict, clear=False):
        # Load Python modules
        # These modules are typically used to register a class
        # such as a MetadataSchema when they are loaded
        python_modules = conf_dict.get('python_modules')
        if python_modules:
            for module_name in python_modules:
                __import__(module_name)
        
        # Load config modules
        config_modules = conf_dict.get('config_modules')
        if config_modules:
            for module_name in config_modules:
                self.add_module(module_name, allow_existing=True)

        # Set configuration values
        for mod in conf_dict:
            if mod in ('python_modules', 'config_modules'):
                continue
            if not self.has_field(mod):
                self.add_module(mod, allow_existing=True)
        super().import_dict(conf_dict, clear=clear)


class ConfigurationLayer(OpenKeyDictController[EngineConfiguration]):
    ''' Configuration "layer", which represents a config file (site config or
    user config, typically).

    A ConfigurationLayer contains sub-configs corresponding to computing
    resources, which are keys in this :class:`Controller`. A "default" config
    resource could be named "local".
    '''

    def __init__(self):
        super().__init__()
        self.add_field(
            'local', EngineConfiguration, default_factory=EngineConfiguration,
            doc='Default local computing resource config. Elements are config '
            'modules which should be registered in the application (spm, fsl, '
            '...)')

    def load(self, filename):
        ''' Load configuration from a JSON or YAML file
        '''
        with open(filename) as f:
            if filename.endswith('.yaml'):
                # YAML support is optional, yaml module may not
                # be installed
                import yaml
                conf = yaml.safe_load(f)
            else:
                conf = json.load(f)
        self.import_dict(conf)

    def add_field(self, name, *args, **kwargs):
        if 'doc' not in kwargs:
            kwargs = dict(kwargs)
            if name == 'local':
                kwargs['doc'] = 'Default local computing resource config. ' \
                    'Elements are config modules which should be registered ' \
                    'in the application (spm, fsl, ...)'
            else:
                kwargs['doc'] = 'Computing resource config. Elements are ' \
                    'config modules which should be registered in the ' \
                    'application (spm, fsl, ...)'
        super().add_field(name, *args, **kwargs)

    def save(self, filename, format=None):
        ''' Save configuration to a JSON or YAML file
        '''
        if format is None:
            if filename.endswith('.yaml'):
                format = 'yaml'
            else:
                format = 'json'
        if format == 'json':
            with open(filename, 'w') as f:
                json.dump(self.asdict(), f)
        elif format == 'yaml':
            # YAML support is optional, yaml module may not
            # be installed
            import yaml
            with open(filename, 'w') as f:
                yaml.dump(self.asdict(), f)
        else:
            raise ValueError(f'Unsupported format: {format}')

    def merge(self, other_layer):
        ''' Merge in-place: other_layer is "added" to self.
        '''
        self.import_dict(other_layer.asdict(), clear=False)

    def merged(self, other_layer):
        ''' Returns a merged copy of self and another ConfigurationLayer layer
        '''
        merged = ConfigurationLayer()
        merged.import_dict(self.asdict())
        merged.merge(other_layer)
        return merged


class ApplicationConfiguration(Controller):
    ''' Application-wide configuration class.

    It contains a "site" and a "user" configuration, and a merge of both.

    Merging is not automatic: after modifying either the site or user configs,
    :meth:`merge_configs` should be called to rebuild the merged configuration.

    It is used like this::

        app_config = ApplicationConfiguration(
            'my_app_name', site_file='/usr/local/etc/my_app_name.json')
        user_conf_dict = {
            'local': {
                'spm': {
                    'spm12_standalone': {
                        'directory': '/usr/local/spm12_standalone',
                        'standalone': True},
                    }}}
        app_config.user = user_conf_dict
        app_config.merge_configs()
        print('merged:', app_config.merged_config.asdict())

    ApplicationConfiguration contains actually 3 configuration objects:

    * the "site" config
    * the "user" config, which are the personal settings and take priority over
      site settings.
    * the "merged_config" which is the resulting merged configuration. This one
      should never be modified by hand, as it is built by the
      :meth:`merge_configs` method.

    In each configuration (``user``, ``site``,, ``merged_config``):

    * The first level, "environment" corresponds to a "computing resource"
      name. The default (and always existing) is "local" and means the local
      computer configuration. Additional configs may be added to store settings
      for remote computing resources.

    * the second level corresponds to configuration modules. Each module has to
      be known in the Capsul config system, and is accessed as a module. The
      default search path for modules is capsul.config.<module_name>. Each
      config module should contain one class inheriting the
      :class:`ModuleConfiguration` class, and a static method
      ``init_execution_context(execution_context)``. Otherwise loading and
      initialization of modules is automatic when inserting items in the config
      object.

    * the third level corresponds to config modules instances. Several
      instances of the same module can exist (for instance a config for SPM8
      and one for SPM12 may coexist and are both instances of the SPM config
      module class, :class:`~spm.SPMConfiguration`). They are indexed by an
      identifier (a name) which may represent an identifiable config (for
      instance, "spm12_standalone" or "spm8").

    * the forth level contains module configuration options (fields of the
      config module class).

    Configurations are based on the
    :class:`~soma.controller.controller.Controller` class, which allows typed
    fields, used to store configurations values. Some levels ("environment",
    modules) are "open keys" in the Controller fields. We have implemented them
    using the :class:`~soma.controller.controller.OpenKeyController`, or more
    precisely :class:`~soma.controller.controller.OpenKeyDictController` class,
    which allows a complete control and validation at every level, contrarily
    to a ``dict[str, ModuleConfiguration]`` for instance.
    '''
    site_file: File = field(doc='site configuration file')
    site: ConfigurationLayer = field(
        default_factory=ConfigurationLayer,
        doc='Site-wise configuration, set by the software admin or installer. '
        'Elements represent computing resources configs.')
    user_file: File = field(doc='user configuration file')
    user: ConfigurationLayer = field(
        default_factory=ConfigurationLayer,
        doc='Personal user config: overrides or completes the site config. '
        'Elements represent computing resources configs.')
    app_name: str = field(default='capsul', doc='Application name')
    
    # read-only modified by merge
    merged_config: ConfigurationLayer = field(
        default_factory=ConfigurationLayer, user_level=2)
    
    def __init__(self, app_name, user_file=undefined, site_file=None):
        '''
        Parameters
        ----------
        app_name: str
            name of the application / config
        user_file: str
            file name for the user config file. If `̀`undefined`` (the default), it
            will be looked for in ``~/.config/{app_name}.json``. If
            ``None``, then no user config will be loaded.
        site_file: str
            file name for the site config file. If `̀`None`` (the default), then
            no config will be loaded.

        '''
        super().__init__()

        self.app_name = app_name

        if site_file is not None:
            self.site_file = site_file
            self.site.load(site_file)

        if user_file is undefined:
            user_file = os.path.expanduser(f'~/.config/{app_name}.json')
            if not os.path.exists(user_file):
                user_file = None
        if user_file is not None:
            self.user_file = user_file
            self.user.load(user_file)
        self.merge_configs()
    

    def merge_configs(self):
        ''' Merge site and user configs into the ``merged_config``
        configuration. This ``merged_config`` will be erased and rebuilt during
        the operation, so *never modify the merged_config*, but site or user
        configs instead.
        '''
        self.merged_config = self.site.merged(self.user)

    @staticmethod
    def available_modules():
        module = sys.modules.get(__name__)
        mod_base = module.__name__.rsplit('.', 1)[0]
        mod_path = getattr(module, '__file__')
        if mod_path is None:
            mod_path = getattr(module, '__path__')
        mod_dir = os.path.dirname(mod_path)
        modules = []
        for p in os.listdir(mod_dir):
            if not p.endswith('.py'):
                continue
            if p in ('configuration.py', '__init__.py'):
                continue
            modules.append('.'.join((mod_base, p[:-3])))
        return sorted(modules)



    