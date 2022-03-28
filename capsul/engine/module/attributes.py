# -*- coding: utf-8 -*-
'''
Attributes completion config module

'''

from __future__ import absolute_import

import os
import six
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
    capsul_engine.settings.module_notifiers.setdefault(
        'capsul.engine.module.attributes', []).append(
            partial(_sync_attributes_factory, weakref.proxy(capsul_engine)))

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


def edition_widget(engine, environment, config_id='attributes'):
    ''' Edition GUI for attributes config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types
    import traits.api as traits

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            conf = session.config(config_id, widget.environment)
            values = {'config_id': config_id}
            values['attributes_schema_paths'] \
                = controller.attributes_schema_paths
            values['attributes_schemas'] = controller.attributes_schemas
            values['process_completion'] = controller.process_completion
            if controller.process_completion is traits.Undefined:
                values['process_completion'] = None
            values['path_completion'] = controller.path_completion
            if controller.path_completion is traits.Undefined:
                values['path_completion'] = None
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k in ('attributes_schema_paths', 'attributes_schemas',
                          'process_completion', 'path_completion'):
                    setattr(conf, k, values[k])

    controller = Controller()
    controller.add_trait(
        'attributes_schema_paths',
        traits.List(traits.Str(), desc='attributes shchemas modules names'))
    controller.add_trait(
        'attributes_schemas',
        traits.DictStrStr(desc='attributes shchemas names'))
    controller.add_trait(
        'process_completion',
        traits.Str(desc='process completion model name'))
    controller.add_trait(
        'path_completion',
        traits.Str(desc='path completion model name',
                   optional=True))

    conf = engine.settings.select_configurations(
        environment, {'attributes': 'any'})
    if conf:
        aconf = conf.get(
            'capsul.engine.module.attributes', {})
        controller.attributes_schema_paths = aconf.get(
            'attributes_schema_paths', [])
        controller.attributes_schemas = aconf.get(
            'attributes_schemas', {})
        controller.process_completion = aconf.get(
            'process_completion', 'builtin')
        controller.path_completion = aconf.get(
            'path_completion', traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
