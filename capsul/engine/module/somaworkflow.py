# -*- coding: utf-8 -*-
from __future__ import absolute_import

from capsul import engine
import traits.api as traits
from traits.api import Undefined
import os
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('somaworkflow',
            [dict(name='use',
                type='boolean',
                description='Use soma workflow for the execution (not always '
                    'optional, actually)'),
            dict(name='computing_resource',
                type='string',
                description='Soma-workflow computing resource to be used to '
                    'run processing'),
            dict(name='config_file',
                type='string',
                description='Soma-Workflow configuration file. '
                  'Default: $HOME/.soma_workflow.cfg'),
            dict(name='keep_failed_workflows',
                 type='boolean',
                 description='Keep failed workflows after pipeline execution '
                    'through StudyConfig'),
            dict(name='keep_succeeded_workflows',
                 type='boolean',
                 description='Keep succeeded workflows after pipeline '
                    'execution through StudyConfig'),

            dict(name='queue',
                 type='string',
                 description='Jobs queue to be used on the computing resource '
                    'for workflow submissions'),
            dict(name='transfer_paths',
                 type='list_string',
                 description='list of paths where files have to be transferred '
                    'by soma-workflow'),
            dict(name='path_translations',
                 type='json',
                 description='Soma-workflow paths translations mapping: '
                    '{local_path: (identifier, uuid)}'),
            ])
    initialize_callbacks(capsul_engine)


def activate_configurations():
    '''
    Activate the SPM module (set env variables) from the global configurations,
    in order to use them via :mod:`capsul.in_context.spm` functions
    '''
    conf = engine.configurations.get('capsul.engine.module.somaworkflow', {})


def edition_widget(engine, environment, config_id='any'):
    ''' Edition GUI for SPM config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            values = {}
            for key in ('computing_resource', 'config_file', 'queue'):
                if getattr(controller, key) in (None, traits.Undefined, ''):
                    values[key] = None
                else:
                    values[key] = getattr(controller, key)
            for key in ('use', 'keep_failed_workflows',
                        'keep_succeeded_workflows', 'transfer_paths',
                        #'path_translations',
                        ):
                values[key] = getattr(controller, key)
            id = 'somaworkflow'
            values['config_id'] = id
            query = 'config_id == "%s"' % id
            conf = session.config('somaworkflow', widget.environment,
                                  selection=query)
            if conf is None:
                session.new_config('somaworkflow', widget.environment, values)
            else:
                for k in ('computing_resource', 'config_file', 'queue', 'use',
                          'keep_failed_workflows', 'keep_succeeded_workflows',
                          'transfer_paths',
                          #'path_translations'
                          ):
                    setattr(conf, k, values[k])
            if id != widget.config_id:
                try:
                    session.remove_config('somaworkflow', widget.environment,
                                          widget.config_id)
                except Exception:
                    pass
                widget.config_id = id

    controller = Controller()
    controller.add_trait('use',
                         traits.Bool(
                            True, output=False,
                            desc='Use soma workflow for the execution (not always optional, actually)'))
    controller.add_trait('computing_resource',
                         traits.Str(
                            traits.Undefined, output=False,
                            desc='Soma-workflow computing resource to be used '
                            'to run processing'))
    controller.add_trait('config_file',
                         traits.File(
                            traits.Undefined, output=False,
                            desc=''))
    controller.add_trait('keep_failed_workflows',
                         traits.Bool(
                            True, output=False,
                            desc=''))
    controller.add_trait('keep_succeeded_workflows',
                         traits.Bool(
                            False, output=False,
                            desc=''))

    controller.add_trait('queue',
                         traits.Str(
                            traits.Undefined, output=False,
                            desc=''))
    controller.add_trait('transfer_paths',
                         traits.List(traits.Directory,
                            [], output=False,
                            desc=''))
    controller.add_trait('path_translations',
                         traits.Dict(
                            key_trait=traits.Directory,
                            value_trait=traits.ListStr(['', ''], minlen=2,
                                                       maxlen=2),
                            value={}, output=False,
                            desc=''))

    conf = None
    if config_id == 'any':
        conf = engine.settings.select_configurations(
            environment, {'somaworkflow': 'any'})
    else:
        try:
            conf = engine.settings.select_configurations(
                environment, {'somaworkflow': 'config_id=="%s"' % config_id})
        except Exception:
            pass
    if conf:
        controller.use = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('use', True)
        controller.computing_resource = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('computing_resource',
                                                         traits.Undefined)
        controller.config_file = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('config_file',
                                                         traits.Undefined)
        config_id = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('config_id', config_id)
        controller.keep_failed_workflows = conf.get(
            'capsul.engine.module.somaworkflow',
            {}).get('keep_failed_workflows', True)
        controller.keep_succeeded_workflows = conf.get(
            'capsul.engine.module.somaworkflow',
            {}).get('keep_succeeded_workflows', False)
        controller.queue = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('queue', Undefined)
        controller.transfer_paths = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('transfer_paths', [])
        controller.path_translations = conf.get(
            'capsul.engine.module.somaworkflow', {}).get(
                'path_translations', {})

    # TODO handle several configs

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.config_id = config_id
    widget.accept = types.MethodType(validate_config, widget)

    return widget


def initialize_callbacks(engine):
    #  WARNING ref to engine in callback
    engine.study_config.on_trait_change(
        lambda param=None, value=None: sync_from_sc(engine, param, value),
        '[use_soma_workflow, somaworkflow_computing_resource, '
        'somaworkflow_config_file, somaworkflow_keep_failed_workflows, '
        'somaworkflow_keep_succeeded_workflows, '
        'somaworkflow_computing_resources_config]')
    #  WARNING ref to engine in callback
    engine.study_config.engine.settings.module_notifiers[
        'capsul.engine.module.somaworkflow'] \
            = [lambda param=None, value=None: sync_to_sc(engine, param, value)]


def sync_from_sc(engine, param=None, value=None):
    # print('sync_from_sc')
    if getattr(engine, '_swf_syncing', False):
        # manage recursive calls
        return
    engine._swf_syncing = True
    sc = engine.study_config
    try:
        if 'SomaWorkflowConfig' in sc.modules \
                and 'capsul.engine.module.somaworkflow' \
                    in engine._loaded_modules:
            with engine.settings as session:
                cif = engine.settings.config_id_field
                config = session.config('somaworkflow', 'global')
                params = {
                    'use_soma_workflow': 'use',
                    'somaworkflow_computing_resource': 'computing_resource',
                    'somaworkflow_config_file': 'config_file',
                    'somaworkflow_keep_failed_workflows':
                        'keep_failed_workflows',
                    'somaworkflow_keep_succeeded_workflows':
                        'keep_succeeded_workflows',
                }
                values = {}
                for sc_param, param in params.items():
                    value = getattr(sc, sc_param, None)
                    if value is Undefined:
                        value = None
                    values[param] = value
                if config is None:
                    values[cif] = 'somaworkflow'
                    session.new_config('somaworkflow', 'global', values)
                else:
                    for param, value in values.items():
                        setattr(config, param, value)
                del config
            del session
    finally:
        del engine._swf_syncing


def sync_to_sc(engine, param=None, value=None):
    # print('sync_to_sc')
    if getattr(engine, '_swf_syncing', False):
        # manage recursive calls
        return
    engine._swf_syncing = True
    sc = engine.study_config
    try:
        if 'SomaWorkflowConfig' in sc.modules \
                and 'capsul.engine.module.somaworkflow' \
                    in engine._loaded_modules:
            with engine.settings as session:
                config = session.config('somaworkflow', 'global')
                if config:
                    params = {
                        'use': 'use_soma_workflow',
                        'computing_resource':
                            'somaworkflow_computing_resource',
                        'config_file': 'somaworkflow_config_file',
                        'keep_failed_workflows':
                            'somaworkflow_keep_failed_workflows',
                        'keep_succeeded_workflows':
                            'somaworkflow_keep_succeeded_workflows',
                    }
                    for param, sc_param in params.items():
                        value = getattr(config, param, Undefined)
                        if value is None:
                            value = Undefined
                        setattr(sc, sc_param, value)
    except ReferenceError:
        pass
    finally:
        del engine._swf_syncing
