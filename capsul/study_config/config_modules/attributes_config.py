##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Attributes completion config module

Classes
=======
:class:`AttributesConfig`
-------------------------
'''

import os
import six
from traits.api import Bool, Str, Undefined, List, DictStrStr
from capsul.study_config.study_config import StudyConfigModule
from capsul.attributes.attributes_factory import AttributesFactory
from capsul.attributes.attributes_schema import AttributesSchema, \
    ProcessAttributes
from capsul.attributes.completion_engine \
    import ProcessCompletionEngineFactory, PathCompletionEngineFactory


class AttributesConfig(StudyConfigModule):
    '''Attributes-based completion configuration module for StudyConfig
    '''

    dependencies = []

    def __init__(self, study_config, configuration):
        super(AttributesConfig, self).__init__(study_config, configuration)
        default_paths = ['capsul.attributes.completion_engine_factory']
        self.study_config.add_trait(
            'attributes_schema_paths',
            List(default_paths, Str(Undefined, output=False), output=False,
            desc='attributes shchema module name'))
        self.study_config.add_trait(
            'attributes_schemas',
            DictStrStr(output=False,
                desc='attributes shchemas names'))
        self.study_config.add_trait(
            'process_completion',
            Str('builtin', output=False,
                desc='process completion model name'))
        self.study_config.add_trait(
            'path_completion',
            Str(Undefined, output=False,
                desc='path completion model name'))
        self.study_config.modules_data.attributes_factory = AttributesFactory()


    def initialize_module(self):
        '''
        '''
        from capsul.engine import CapsulEngine

        factory = self.study_config.modules_data.attributes_factory
        factory.class_types['schema'] = AttributesSchema
        factory.class_types['process_completion'] \
          = ProcessCompletionEngineFactory
        factory.class_types['path_completion'] \
          = PathCompletionEngineFactory
        factory.class_types['process_attributes'] \
          = ProcessAttributes

        factory.module_path = self.study_config.attributes_schema_paths

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            # otherwise engine is "owned" by StudyConfig
            if 'capsul.engine.module.attributes' \
                    not in self.study_config.engine.modules:
                self.study_config.engine.modules.append(
                    'capsul.engine.module.attributes')
                self.study_config.engine.load_modules()
            self.sync_to_engine()


    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.update_module,
            ['attributes_schemas', 'process_completion',
             'path_completion', 'attributes_schema_paths'])

        self.study_config.engine.global_config.attributes.on_trait_change(
            self.sync_from_engine,
            ['attributes_schemas', 'process_completion',
             'path_completion', 'attributes_schema_paths'])


    def update_module(self):
        factory = self.study_config.modules_data.attributes_factory
        factory.module_path = self.study_config.attributes_schema_paths
        self.sync_to_engine()


    def sync_to_engine(self):
        self.study_config.engine.global_config.attributes.attributes_schemas \
            = self.study_config.attributes_schemas
        self.study_config.engine.global_config.attributes \
              .attributes_schema_paths \
                  = self.study_config.attributes_schema_paths
        self.study_config.engine.global_config.attributes.process_completion \
            = self.study_config.process_completion
        self.study_config.engine.global_config.attributes.path_completion \
            = self.study_config.path_completion


    def sync_from_engine(self):
        self.study_config.attributes_schemas \
            = self.study_config.engine.global_config.attributes \
                .attributes_schemas
        self.study_config.attributes_schema_paths \
            = self.study_config.engine.global_config.attributes \
                .attributes_schema_paths
        self.study_config.process_completion \
            = self.study_config.engine.global_config.attributes \
                .process_completion
        self.study_config.path_completion \
            = self.study_config.engine.global_config.attributes.path_completion

