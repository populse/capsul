# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from capsul import engine
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('afni',
                                      [dict(name='directory',
                                            type='string',
                                            description='Directory where AFNI is installed')
                                       ])

        # init a single config
        config = settings.config('afni', 'global')
        if not config:
            settings.new_config('afni', 'global',
                                {capsul_engine.settings.config_id_field:
                                     'afni'})


def activate_configurations():
    '''
    Activate the AFNI module (set env variables) from the global configurations,
    in order to use them via :mod:`capsul.in_context.afni` functions
    '''
    conf = engine.configurations.get('capsul.engine.module.afni', {})
    afni_dir = conf.get('directory')
    if afni_dir:
        os.environ['AFNIPATH'] = six.ensure_str(afni_dir)
    elif 'AFNIPATH' in os.environ:
        del os.environ['AFNIPATH']


def edition_widget(engine, environment, config_id='afni'):
    ''' Edition GUI for AFNI config - see
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
                                                       desc='Directory where AFNI is installed'))

    conf = engine.settings.select_configurations(
        environment, {'afni': 'any'})
    if conf:
        fconf = conf.get('capsul.engine.module.afni', {})
        controller.directory = fconf.get('directory', traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
