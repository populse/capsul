# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from capsul import engine
from capsul.engine import activate_module
from capsul.engine.settings import Settings
import os
import sys


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('nipype',[])
    pass


#def config_dependencies(config):
    #return {'spm': 'version == "12"'}


def activate_configurations():
    '''
    Activate the nipype module from the global configurations
    '''
    from capsul.in_context import nipype

    # activate optional dependencies first
    for module in ('matlab', 'spm', 'fsl', 'freesurfer'):
        module_name = Settings.module_name(module)
        mod_conf = engine.configurations.get(module_name)
        if mod_conf:
            try:
                activate_module(module_name)
            except Exception as e:
                # the module couldn't be activated, just don't use it
                print('error activating module %s for nipype:' % module_name,
                      e, file=sys.stderr)
                pass

    nipype.configure_all()


