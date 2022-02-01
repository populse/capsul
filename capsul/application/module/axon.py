# -*- coding: utf-8 -*-

'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_
'''

from __future__ import absolute_import
import capsul.engine


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('axon',
            [dict(name='shared_directory',
                type='string',
                description=
                    'Directory where BrainVisa shared data is installed'),
             dict(name='user_level',
                  type='int',
                  description=
                      '0: basic, 1: advanced, 2: expert, or more. '
                      'used to display or hide some advanced features or '
                      'process parameters that would be confusing to a novice '
                      'user'),
            ])

    with capsul_engine.settings as session:
        config = session.config('axon', 'global')
        if not config:
            values = {capsul_engine.settings.config_id_field: 'axon',
                      'shared_directory': None, 'user_level': 0}
            session.new_config('axon', 'global', values)

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
            values = {'config_id': 'axon', 'user_level': controller.user_level}
            if controller.shared_directory in (None, traits.Undefined, ''):
                values['shared_directory'] = None
            else:
                values['shared_directory'] = controller.shared_directory
            if conf is None:
                session.new_config('axon', widget.environment, values)
            else:
                for k in ('shared_directory', 'user_level'):
                    setattr(conf, k, values[k])

    controller = Controller()
    controller.add_trait('shared_directory',
                         traits.Directory(desc='Directory where BrainVisa '
                                          'shared data is installed'))
    controller.add_trait(
        'user_level',
        traits.Int(desc=
                   '0: basic, 1: advanced, 2: expert, or more. '
                    'used to display or hide some advanced features or '
                    'process parameters that would be confusing to a novice '
                    'user'))

    conf = engine.settings.select_configurations(
        environment, {'axon': 'any'})
    if conf:
        controller.shared_directory = conf.get(
            'capsul.engine.module.axon', {}).get('shared_directory',
                                                 traits.Undefined)
        controller.user_level = conf.get(
            'capsul.engine.module.axon', {}).get('user_level', 0)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget