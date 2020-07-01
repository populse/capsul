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


