# -*- coding: utf-8 -*-
from __future__ import absolute_import

import capsul.engine
import os

#from soma.controller import Controller
#from traits.api import File, Undefined, Instance

    
def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('matlab',
        [dict(name='executable',
              type='string',
              description='Full path of the matlab executable'),
         dict(name='mcr_directory',
              type='string',
              description='Full path of the matlab MCR directory, for use '
                  'with standalone binaries'),
         ])


def check_configurations():
    '''
    Check if the activated configuration is valid for Matlab and return
    an error message if there is an error or None if everything is good.
    '''
    matlab_executable = capsul.engine.configurations.get(
        'capsul.engine.module.matlab', {}).get('executable')
    if not matlab_executable:
        return 'matlab.executable is not defined'
    if not os.path.exists(matlab_executable):
        return 'Matlab executable is defined as "%s" but this path does not exist' % matlab_executable
    return None


def edition_widget(engine, environment, config_id='matlab'):
    ''' Edition GUI for matlab config - see
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
            if controller.executable in (None, traits.Undefined, ''):
                values['executable'] = None
            else:
                values['executable'] = controller.executable
            if controller.mcr_directory in (None, traits.Undefined, ''):
                values['mcr_directory'] = None
            else:
                values['mcr_directory'] = controller.mcr_directory
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k in ('executable', 'mcr_directory', ):
                    if (k == 'mcr_directory' and
                                   values[k] and
                                   not os.path.isdir(values[k])):
                        raise NotADirectoryError('\nMatlab mcr_directory '
                                                 'was not updated:\n{} is '
                                                 'not existing!'.format(
                                                                values[k]))
                    elif (k == 'executable' and
                                  values[k] and
                                  not os.path.isfile(values[k])):
                        raise FileNotFoundError('\nMatlab executable '
                                                 'was not updated:\n{} is '
                                                 'not existing!'.format(
                                                                values[k]))
                    else:
                        setattr(conf, k, values[k])

    controller = Controller()
    controller.add_trait('executable',
                         traits.File(desc=
                                     'Full path of the matlab executable'))
    controller.add_trait('mcr_directory',
                         traits.Directory(desc='Full path of the matlab MCR '
                                          'directory, or use with standalone '
                                          'binaries'))

    conf = engine.settings.select_configurations(
        environment, {'matlab': 'any'})
    if conf:
        controller.executable = conf.get(
            'capsul.engine.module.matlab', {}).get('executable',
                                                   traits.Undefined)
        controller.mcr_directory = conf.get(
            'capsul.engine.module.matlab', {}).get('mcr_directory',
                                                   traits.Undefined)

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
