# -*- coding: utf-8 -*-
from __future__ import absolute_import

import capsul.engine
import os
from soma.path import find_in_path
import os.path as osp
from capsul import engine
import six


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('fsl',
            [dict(name='directory',
                type='string',
                description='Directory where FSL is installed'),
            dict(name='config',
                type='string',
                description='path of fsl.sh file'),
            dict(name='prefix',
                type='string',
                description='Prefix to add to FSL commands')
            ])

        # init a single config
        config = settings.config('fsl', 'global')
        if not config:
            settings.new_config('fsl', 'global',
                                {capsul_engine.settings.config_id_field:
                                    'fsl'})

    
def check_configurations():
    '''
    Checks if the activated configuration is valid to run FSL and returns an
    error message if there is an error or None if everything is good.
    '''
    fsl_prefix = capsul.engine.configurations.get(
        'capsul.engine.module.fsl',{}).get('prefix', '')
    fsl_config = capsul.engine.configurations.get(
        'capsul.engine.module.fsl',{}).get('config')
    if not fsl_config:
        if not find_in_path('%sbet' % fsl_prefix):
            return 'FSL command "%sbet" cannot be found in PATH' % fsl_prefix
    else:
        if fsl_prefix:
            return 'FSL configuration must either use config or prefix but not both'
        if not osp.exists(fsl_config):
            return 'File "%s" does not exists' % fsl_config
        if not fsl_config.endswith('fsl.sh'):
            return 'File "%s" is not a path to fsl.sh script' % fsl_config
    return None


def complete_configurations():
    '''
    Try to automatically set or complete the capsul.engine.configurations for FSL.
    '''
    config = capsul.engine.configurations
    config = config.setdefault('capsul.engine.module.fsl', {})
    fsl_dir = config.get('directory', os.environ.get('FSLDIR'))
    fsl_prefix = config.get('prefix', '')
    if fsl_dir and not fsl_prefix:
        # Try to set fsl_config from FSLDIR environment variable
        fsl_config = '%s/etc/fslconf/fsl.sh' % fsl_dir
        if osp.exists(fsl_config):
            config['config'] = fsl_config
    elif not fsl_prefix:
        # Try to set fsl_prefix by searching fsl-*bet in PATH
        bet = find_in_path('fsl*-bet')
        if bet:
            config['prefix'] = os.path.basename(bet)[:-3]


def activate_configurations():
    '''
    Activate the FSL module (set env variables) from the global configurations,
    in order to use them via :mod:`capsul.in_context.fsl` functions
    '''
    conf = engine.configurations.get('capsul.engine.module.fsl', {})
    fsl_dir = conf.get('directory')
    if fsl_dir:
        os.environ['FSLDIR'] = six.ensure_str(fsl_dir)
    elif 'FSLDIR' in os.environ:
        del os.environ['FSLDIR']
    fsl_prefix = conf.get('prefix')
    if fsl_prefix:
        os.environ['FSL_PREFIX'] = six.ensure_str(fsl_prefix)
    elif 'FSL_PREFIX' in os.environ:
        del os.environ['FSL_PREFIX']
    fsl_conf = conf.get('config')
    if fsl_conf:
        os.environ['FSL_CONFIG'] = six.ensure_str(fsl_conf)
    elif 'FSL_CONFIG' in os.environ:
        del os.environ['FSL_CONFIG']


def edition_widget(engine, environment, config_id='fsl'):
    ''' Edition GUI for FSL config - see
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
            for k in ('directory', 'config', 'prefix'):
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
        desc='Directory where FSL is installed'))
    controller.add_trait('config', traits.File(
        traits.Undefined,
        output=False,
        desc='Parameter to specify the fsl.sh path'))
    controller.add_trait('prefix', traits.String(traits.Undefined,
        desc='Prefix to add to FSL commands'))

    conf = engine.settings.select_configurations(
        environment, {'fsl': 'any'})
    if conf:
        fconf = conf.get('capsul.engine.module.fsl', {})
        controller.directory = fconf.get('directory', traits.Undefined)
        controller.config = fconf.get('config', traits.Undefined)
        controller.prefix = fconf.get('prefix', traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
