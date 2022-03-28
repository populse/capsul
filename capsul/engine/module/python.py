# -*- coding: utf-8 -*-
''' Python configuration module for CAPSUL

This config module allows the customization of python executable and python path in process execution. It can (as every config module) assign specific config values for different environments (computing resources, typically).

Python configuration is slightly different from other config modules in the way that it cannot be handled during execution inside a python library: python executable and modules path have to be setup before starting python and loading modules. So the config here sometimes has to be prepared from client side and hard-coded in the job to run.

For this reason, what we call here "python jobs" have a special handling. "python jobs" are :class:`~capsul.process.process.Process` classes defining a :meth:`~capsul.process.process.Process._run_process` method, and not :meth:`~capsul.process.process.Process.get_commandline`. Processing are thus python functions or methods, and need the capsul library to run.

Python jobs are handled in workflow building (:mod:`capsul.pipeline.pipeline_workflow`), and jobs on engine side should not have to bother about it.

The python config module is not mandatory: if no specific configuration is needed, jobs are run using the python command from the path, following the client ``sys.executable`` short name (if the client runs ``/usr/bin/python3``, the engine will try to use ``python3`` from the ``PATH``.

The python config module is used optionally (if there is a config, it is used, otherwise no error is produced), and automatically for all jobs: no need to declare it in jobs :meth:`~capsul.process.process.Process.requirements` method.

Inside process execution, the module is otherwise handled like any other.
'''

from __future__ import absolute_import

import capsul.engine
import os
import sys


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('python',
        [dict(name='executable',
              type='string',
              description='Full path of the python executable'),
        dict(name='path',
              type='list_string',
              description='paths to prepend to sys.path'),
         ])


def activate_configurations():
    '''
    Activate the python module from the global configurations
    '''
    py_conf = capsul.engine.configurations.get('capsul.engine.module.python')
    if py_conf:
        py_path = py_conf.get('path')
        if py_path:
            sys.path = py_path + [p for p in sys.path if p not in py_path]

def edition_widget(engine, environment, config_id='python'):
    ''' Edition GUI for python config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.qt_backend import Qt
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types
    import traits.api as traits

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            conf = session.config(config_id, widget.environment)
            values = {'config_id': config_id,
                      'path': controller.path}
            if controller.executable in (None,
                                                traits.Undefined, ''):
                values['executable'] = None
            else:
                values['executable'] = controller.executable
            if conf is None:
                session.new_config(config_id, widget.environment, values)
            else:
                for k in ('path', 'executable'):
                    setattr(conf, k, values[k])

    controller = Controller()
    controller.add_trait('executable',
                         traits.Str(desc='Full path of the python executable'))
    controller.add_trait('path',
                         traits.List(traits.Directory(), [],
                                     desc='paths to prepend to sys.path'))

    conf = engine.settings.select_configurations(
        environment, {'python': 'any'})
    if conf:
        controller.executable = conf.get(
            'capsul.engine.module.python', {}).get('executable',
                                                   traits.Undefined)
        controller.path = conf.get(
            'capsul.engine.module.python', {}).get('path', [])

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.accept = types.MethodType(validate_config, widget)

    return widget
