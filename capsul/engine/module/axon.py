# -*- coding: utf-8 -*-

'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_
'''

from __future__ import absolute_import
import os
import six
from soma.controller import Controller
from traits.api import Directory, Undefined, Instance
import capsul.engine
import os.path as osp


def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('axon',
            [dict(name='shared_directory',
                type='string',
                description=
                  'Directory where BrainVisa shared data is installed'),
            ])

    with capsul_engine.settings as session:
        config = session.config('axon', 'global')
        if not config:
            values = {capsul_engine.settings.config_id_field: 'axon',
                      'shared_directory': None}
            session.new_config('axon', 'global', values)

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config'):
        if 'BrainVISAConfig' not in capsul_engine.study_config.modules:
            scmod = capsul_engine.study_config.load_module(
                'BrainVISAConfig', {})
            scmod.initialize_module()
            scmod.initialize_callbacks()
        else:
            scmod = capsul_engine.study_config.modules['BrainVISAConfig']
            scmod.sync_to_engine()

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

