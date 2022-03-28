# -*- coding: utf-8 -*-
'''
Attributes completion config module

Classes
=======
:class:`AttributesConfig`
-------------------------
'''

from __future__ import absolute_import
import os
import six
from traits.api import Bool, Str, Undefined, List, DictStrStr
from capsul.study_config.study_config import StudyConfigModule
from capsul.attributes.attributes_factory import AttributesFactory
from capsul.attributes.attributes_schema import AttributesSchema, \
    ProcessAttributes


class AttributesConfig(StudyConfigModule):
    '''Attributes-based completion configuration module for StudyConfig

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

    attributes_schema_paths: list of str (filenames)
        attributes shchema module name
    attributes_schemas: dict(str, str)
        attributes shchemas names
    process_completion: str (default:'builtin')
        process completion model name
    path_completion: str
        path completion model name
    '''

    dependencies = []

    def __init__(self, study_config, configuration):
        super(AttributesConfig, self).__init__(study_config, configuration)
        default_paths = ['capsul.attributes.completion_engine_factory']
        self.study_config.add_trait(
            'attributes_schema_paths',
            List(default_paths, Str(Undefined, output=False), output=False,
            desc='attributes shchema module name', groups=['attributes']))
        self.study_config.add_trait(
            'attributes_schemas',
            DictStrStr(output=False,
                desc='attributes shchemas names', groups=['attributes']))
        self.study_config.add_trait(
            'process_completion',
            Str('builtin', output=False,
                desc='process completion model name', groups=['attributes']))
        self.study_config.add_trait(
            'path_completion',
            Str(Undefined, output=False,
                desc='path completion model name', groups=['attributes'],
                optional=True))


    def initialize_module(self):
        '''
        '''
        from capsul.engine import CapsulEngine

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            # otherwise engine is "owned" by StudyConfig
            if 'capsul.engine.module.attributes' \
                    not in self.study_config.engine._loaded_modules:
                self.study_config.engine.load_module(
                    'capsul.engine.module.attributes')
            self.sync_to_engine()


    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.update_module,
            ['attributes_schemas', 'process_completion',
             'path_completion', 'attributes_schema_paths'])
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers.setdefault(
            'capsul.engine.module.attributes', []).append(
                self.sync_from_engine)


    def update_module(self, param=None, value=None):
        #if param == 'attributes_schema_paths':
            #factory = self.study_config.modules_data.attributes_factory
            #factory.module_path = self.study_config.attributes_schema_paths
        self.sync_to_engine(param, value)


    def sync_to_engine(self, param=None, value=None):
        with self.study_config.engine.settings as session:
            config = session.config('attributes', 'global')
            if config:
                if param is not None:
                    if value is Undefined:
                        value = None
                    setattr(config, param, value)
                else:
                    params = ['attributes_schemas', 'attributes_schema_paths',
                              'process_completion', 'path_completion']
                    for param in params:
                        value = getattr(self.study_config, param)
                        if value is Undefined:
                            value = None
                    setattr(config, param, value)


    def sync_from_engine(self, param=None, value=None):
        if param is not None:
            if value is None:
                value = Undefined
            setattr(self.study_config, param, value)
        else:
            with self.study_config.engine.settings as session:
                config = session.config('attributes', 'global')
                if config:
                    params = ['attributes_schemas', 'attributes_schema_paths',
                              'process_completion', 'path_completion']
                    for param in params:
                        value = getattr(config, param)
                        if value is None:
                            value = Undefined
                        setattr(self.study_config, param, value)
