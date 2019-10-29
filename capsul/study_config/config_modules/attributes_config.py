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
        #self.study_config.modules_data.attributes_factory = AttributesFactory()


    def initialize_module(self):
        '''
        '''
        from capsul.engine import CapsulEngine

        #factory = self.study_config.modules_data.attributes_factory
        #factory.class_types['schema'] = AttributesSchema
        #factory.class_types['process_completion'] \
          #= ProcessCompletionEngineFactory
        #factory.class_types['path_completion'] \
          #= PathCompletionEngineFactory
        #factory.class_types['process_attributes'] \
          #= ProcessAttributes

        #factory.module_path = self.study_config.attributes_schema_paths

        # Comment the following code to make tests work before removing StudyConfig
        pass
        #if type(self.study_config.engine) is not CapsulEngine:
            ## engine is a proxy, thus we are initialized from a real
            ## CapsulEngine, which holds the reference values
            #self.study_config.modules_data.attributes_factory \
                #= self.study_config.engine.global_config.attributes \
                    #.attributes_factory
            #self.sync_from_engine()
        #else:
            ## otherwise engine is "owned" by StudyConfig
            #if 'capsul.engine.module.attributes' \
                    #not in self.study_config.engine.modules:
                #self.study_config.engine.modules.append(
                    #'capsul.engine.module.attributes')
                #self.study_config.engine.load_modules()
            #self.study_config.modules_data.attributes_factory \
                #= self.study_config.engine.global_config.attributes \
                    #.attributes_factory

            #self.sync_to_engine()


    # Comment the following code to make tests work before removing StudyConfig
    #def initialize_callbacks(self):
        #self.study_config.on_trait_change(
            #self.update_module,
            #['attributes_schemas', 'process_completion',
             #'path_completion', 'attributes_schema_paths'])

        #self.study_config.engine.global_config.attributes.on_trait_change(
            #self.sync_from_engine,
            #['attributes_schemas', 'process_completion',
             #'path_completion', 'attributes_schema_paths'])


    def update_module(self, param=None, value=None):
        if param == 'attributes_schema_paths':
            factory = self.study_config.modules_data.attributes_factory
            factory.module_path = self.study_config.attributes_schema_paths
        self.sync_to_engine(param, value)


    def sync_to_engine(self, param=None, value=None):
        if param is not None:
            setattr(self.study_config.engine.global_config.attributes, param,
                    value)
        else:
            self.study_config.engine.global_config.attributes \
                .attributes_schemas \
                    = self.study_config.attributes_schemas
            self.study_config.engine.global_config.attributes \
                  .attributes_schema_paths \
                      = self.study_config.attributes_schema_paths
            self.study_config.engine.global_config.attributes \
                .process_completion \
                    = self.study_config.process_completion
            self.study_config.engine.global_config.attributes.path_completion \
                = self.study_config.path_completion


    def sync_from_engine(self, param=None, value=None):
        if param is not None:
            setattr(self.study_config, param, value)
        else:
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
                = self.study_config.engine.global_config.attributes \
                    .path_completion

