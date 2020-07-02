# -*- coding: utf-8 -*-

'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_
'''

from __future__ import absolute_import
import os
import six
import capsul.engine
import os.path as osp


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('axon',
            [dict(name='shared_directory',
                type='string',
                description=
                  'Directory where BrainVisa shared data is installed'),
            ])

    with capsul_engine.settings as session:
        config = session.config('axon', 'global')
        if not config:
            values = {capsul_engine.settings.config_id_field: 'axon',
                      'shared_directory': None}
            session.new_config('axon', 'global', values)

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config'):
        if 'BrainVISAConfig' not in capsul_engine.study_config.modules:
            scmod = capsul_engine.study_config.load_module(
                'BrainVISAConfig', {})
            scmod.initialize_module()
            scmod.initialize_callbacks()
        else:
            scmod = capsul_engine.study_config.modules['BrainVISAConfig']
            scmod.sync_to_engine()

def check_configurations():
    '''
    Checks if the activated configuration is valid to use BrainVisa and returns
    an error message if there is an error or None if everything is good.
    '''
    shared_dir = capsul.engine.configurations.get(
        'axon', {}).get('shared_directory', '')
    if not shared_dir:
        return 'Axon shared_directory is not found'
    return None

def complete_configurations():
    '''
    Try to automatically set or complete the capsul.engine.configurations for
    Axon.
    '''
    config = capsul.engine.configurations
    config = config.setdefault('axon', {})
    shared_dir = config.get('shared_directory', None)
    if shared_dir is None:
        from soma import config as soma_config
        shared_dir = soma_config.BRAINVISA_SHARE
        if shared_dir:
            config['shared_directory'] = shared_dir


def edition_widget(engine, environment):
    ''' Edition GUI for axon config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types
    import traits.api as traits

    def validate_config(widget):
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            conf = session.config('axon', widget.environment)
            values = {'config_id': 'axon'}
            if controller.shared_directory in (None, traits.Undefined, ''):
                values['shared_directory'] = None
            else:
                values['shared_directory'] = controller.shared_directory
            if conf is None:
                session.new_config('axon', widget.environment, values)
            else:
                for k in ('shared_directory', ):
                    setattr(conf, k, values[k])

    controller = Controller()
    controller.add_trait('shared_directory',
                         traits.Directory(desc='Directory where BrainVisa '
                                          'shared data is installed'))

    conf = engine.settings.select_configurations(
        environment, {'axon': 'any'})
    if conf:
        controller.executable = conf.get(
            'capsul.engine.module.axon', {}).get('shared_directory',
                                                 traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget

