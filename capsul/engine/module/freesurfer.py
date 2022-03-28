# -*- coding: utf-8 -*-
from __future__ import absolute_import

import capsul.engine
import os
from soma.path import find_in_path
import os.path as osp
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('freesurfer',
            [dict(name='setup',
                  type='string',
                  description='path of FreeSurferEnv.sh file'),
             dict(name='subjects_dir',
                  type='string',
                  description='Freesurfer subjects data directory'),
            ])
        # init a single config
        config = settings.config('freesurfer', 'global')
        if not config:
            settings.new_config('freesurfer', 'global',
                                {capsul_engine.settings.config_id_field:
                                    'freesurfer'})

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'FreeSurferConfig' not in capsul_engine.study_config.modules:
        fsmod = capsul_engine.study_config.load_module('FreeSurferConfig', {})
        fsmod.initialize_module()
        fsmod.initialize_callbacks()


def check_configurations():
    '''
    Checks if the activated configuration is valid to run Freesurfer and
    returns an error message if there is an error or None if everything is
    good.
    '''
    fs_setup = capsul.engine.configurations.get(
        'capsul.engine.module.freesurfer', {}).get('setup')
    if not fs_setup:
        return 'Freesurfer setup script FreeSurferEnv.sh is not configured'
    return None


def complete_configurations():
    '''
    Try to automatically set or complete the capsul.engine.configurations for
    Freesurfer.
    '''
    config = capsul.engine.configurations
    config = config.setdefault('freesurfer', {})
    fs_setup = config.get('setup')
    if not fs_setup:
        fs_home = os.environ.get('FREESURFER_HOME')
        if fs_home:
            fs_setup = osp.join(fs_home, 'FreeSurferEnv.sh')
            if not osp.exists(fs_setup):
                fs_setup = None
        if not fs_setup:
            reconall = find_in_path('recon-all')
            if reconall:
                fs_setup = osp.join(osp.dirname(osp.dirname(reconall)),
                                    'FreeSurferEnv.sh')
                if not osp.exists(fs_setup):
                    fs_setup = None
        if fs_setup:
            config['setup'] = fs_setup


def edition_widget(engine, environment, config_id='freesurfer'):
    ''' Edition GUI for Freesurfer config - see
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
            for k in ('setup', 'subjects_dir'):
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

    controller.add_trait("setup", traits.File(
        traits.Undefined,
        desc="Path to 'FreeSurferEnv.sh'"))
    controller.add_trait('subjectsdir', traits.Directory(
        traits.Undefined,
        desc='FreeSurfer subjects data directory'))

    conf = engine.settings.select_configurations(
        environment, {'freesurfer': 'any'})
    if conf:
        controller.setup = conf.get(
            'capsul.engine.module.freesurfer', {}).get('setup',
                                                       traits.Undefined)
        controller.subjects_dir= conf.get(
            'capsul.engine.module.freesurfer', {}).get('subjects_dir',
                                                       traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
