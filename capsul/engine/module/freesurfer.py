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
        settings.ensure_module_fields('freesurfer',
            [dict(name='setup',
                  type='string',
                  description='path of FreeSurferEnv.sh file'),
             dict(name='subjects_dir',
                  type='string',
                  description='Freesurfer subjects data directory'),
            ])

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

