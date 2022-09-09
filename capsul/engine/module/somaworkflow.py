# -*- coding: utf-8 -*-
from __future__ import absolute_import

from capsul import engine
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
            #dict(name='path_translations',
                 #type='dict',
                 #description='Soma-workflow paths translations mapping: '
                    #'{local_path: (identifier, uuid)}'),
            ])


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
    import traits.api as traits

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
                         traits.Str(
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
                         traits.ListStr(
                            [], output=False,
                            desc=''))
    #controller.add_trait('path_translations',
                         #traits.Dict(
                            #traits.Undefined, output=False,
                            #desc=''))

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
        controller.directory = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('use', True)
        controller.computing_resource = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('computing_resource',
                                                         traits.Undefined)
        controller.config_file = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('config_file',
                                                         traits.Undefined)
        config_id = conf.get(
            'capsul.engine.module.somaworkflow', {}).get('config_id', config_id)

    # TODO handle several configs

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.config_id = config_id
    widget.accept = types.MethodType(validate_config, widget)

    return widget
