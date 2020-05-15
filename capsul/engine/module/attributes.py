# -*- coding: utf-8 -*-
'''
Attributes completion config module

'''

from __future__ import absolute_import

import os
import six
from soma.controller import Controller
from traits.api import Bool, Str, Undefined, List, DictStrStr, Instance
from capsul.attributes.attributes_factory import AttributesFactory
from capsul.attributes.attributes_schema import AttributesSchema, \
    ProcessAttributes
from capsul.attributes.completion_engine \
    import ProcessCompletionEngineFactory, PathCompletionEngineFactory
from capsul.engine import settings
import capsul.engine
import os.path as osp
from functools import partial
import weakref


def init_settings(capsul_engine):
    default_paths = ['capsul.attributes.completion_engine_factory']

    init_att = {
        'attributes_schema_paths': default_paths,
        'attributes_schemas': {},
        'process_completion': 'builtin',
        capsul_engine.settings.config_id_field: 'attributes',
    }

    with capsul_engine.settings as session:
        session.ensure_module_fields('attributes',
            [dict(name='attributes_schema_paths',
                  type='list_string',
                  description='attributes shchemas modules names'),
             dict(name='attributes_schemas',
                  type='json',
                  description='attributes shchemas names'),
             dict(name='process_completion',
                  type='string',
                  description='process completion model name'),
             dict(name='path_completion',
                  type='string',
                  description='path completion model name'),
            ])
        config = session.config('attributes', 'global')
        if not config:
            session.new_config('attributes', 'global', init_att)

    if not hasattr(capsul_engine, '_modules_data'):
        capsul_engine._modules_data = {}
    data = capsul_engine._modules_data.setdefault('attributes', {})
    factory = AttributesFactory()
    data['attributes_factory'] = factory

    factory.class_types['schema'] = AttributesSchema
    factory.class_types['process_completion'] \
        = ProcessCompletionEngineFactory
    factory.class_types['path_completion'] \
        = PathCompletionEngineFactory
    factory.class_types['process_attributes'] \
        = ProcessAttributes

    factory.module_path = default_paths
    capsul_engine.settings.module_notifiers['attributes'] \
            = [partial(_sync_attributes_factory, weakref.proxy(capsul_engine))]

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'AttributesConfig' not in capsul_engine.study_config.modules:
        scmod = capsul_engine.study_config.load_module('AttributesConfig', {})
        scmod.initialize_module()
        scmod.initialize_callbacks()

#def check_configurations():
    #'''
    #Checks if the activated configuration is valid to use BrainVisa and returns
    #an error message if there is an error or None if everything is good.
    #'''
    #return None

#def complete_configurations():
    #'''
    #Try to automatically set or complete the capsul.engine.configurations for
    #the attributes module.
    #'''
    #config = capsul.engine.configurations
    #config = config.setdefault('attributes', {})
    #attributes_schema_paths = config.get('attributes_schema_paths', None)
    #if attributes_schema_paths is None:
        #config['attributes_schema_paths'] \
            #= ['capsul.attributes.completion_engine_factory']
    #attributes_schemas = config.get('attributes_schemas', None)
    #if attributes_schemas is None:
        #config['attributes_schemas'] = {}


def _sync_attributes_factory(capsul_engine, param=None, value=None):
    factory = capsul_engine._modules_data['attributes']['attributes_factory']
    with capsul_engine.settings as session:
        config = session.config('attributes', 'global')
        if config:
            factory.module_path = config.attributes_schema_paths


