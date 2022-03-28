# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from capsul import engine
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('ants',
                                      [dict(name='directory',
                                            type='string',
                                            description='Directory where ANTS is installed')
                                       ])

        # init a single config
        config = settings.config('ants', 'global')
        if not config:
            settings.new_config('ants', 'global',
                                {capsul_engine.settings.config_id_field:
                                     'ants'})


def activate_configurations():
    '''
    Activate the ANTS module (set env variables) from the global configurations,
    in order to use them via :mod:`capsul.in_context.ants` functions
    '''
    conf = engine.configurations.get('capsul.engine.module.ants', {})
    ants_dir = conf.get('directory')
    if ants_dir:
        os.environ['ANTSPATH'] = six.ensure_str(ants_dir)
    elif 'ANTSPATH' in os.environ:
        del os.environ['ANTSPATH']


def edition_widget(engine, environment, config_id='ants'):
    ''' Edition GUI for ANTS config - see
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
            for k in ['directory']:
                value = getattr(controller, k)
                if value is traits.Undefined:
                    value = None
                values[k] = value
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k, value in values.items():
                    if k == 'config_id':
                        continue
                    setattr(conf, k, values[k])

    controller = Controller()

    controller.add_trait('directory', traits.Directory(traits.Undefined,
                                                       desc='Directory where ANTS is installed'))

    conf = engine.settings.select_configurations(
        environment, {'ants': 'any'})
    if conf:
        fconf = conf.get('capsul.engine.module.ants', {})
        controller.directory = fconf.get('directory', traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
