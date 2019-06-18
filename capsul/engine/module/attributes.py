'''
Attributes completion config module

Classes
=======
:class:`AttributesConfig`
-------------------------
'''

import os
import six
from soma.controller import Controller
from traits.api import Bool, Str, Undefined, List, DictStrStr, Instance
from capsul.attributes.attributes_factory import AttributesFactory
from capsul.attributes.attributes_schema import AttributesSchema, \
    ProcessAttributes
from capsul.attributes.completion_engine \
    import ProcessCompletionEngineFactory, PathCompletionEngineFactory


class AttributesConfig(Controller):
    '''Attributes-based completion configuration module for StudyConfig
    '''

    default_paths = ['capsul.attributes.completion_engine_factory']
    attributes_schema_paths = \
        List(default_paths, Str(Undefined, output=False),
             output=False,
             desc='attributes shchema module name')
    attributes_schemas = \
        DictStrStr(output=False,
                   desc='attributes shchemas names')
    process_completion = \
        Str('builtin', output=False,
            desc='process completion model name')
    path_completion = \
        Str(Undefined, output=False,
            desc='path completion model name')


    def __init__(self):
        super(AttributesConfig, self).__init__()
        self.attributes_factory = AttributesFactory()

        factory = self.attributes_factory
        factory.class_types['schema'] = AttributesSchema
        factory.class_types['process_completion'] \
            = ProcessCompletionEngineFactory
        factory.class_types['path_completion'] \
            = PathCompletionEngineFactory
        factory.class_types['process_attributes'] \
            = ProcessAttributes

        factory.module_path = self.attributes_schema_paths


def load_module(capsul_engine, module_name):
    capsul_engine.global_config.add_trait('attributes',
                                          Instance(AttributesConfig))
    capsul_engine.global_config.attributes = AttributesConfig()

    if hasattr(capsul_engine, 'study_config'):
    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'AttributesConfig' not in capsul_engine.study_config.modules:
        scmod = capsul_engine.study_config.load_module('AttributesConfig', {})
        scmod.initialize_module()
        scmod.initialize_callbacks()

