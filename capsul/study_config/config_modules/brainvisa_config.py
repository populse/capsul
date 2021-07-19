# -*- coding: utf-8 -*-
'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_

Classes
=======
:class:`BrainVISAConfig`
------------------------
'''

from __future__ import print_function
from __future__ import absolute_import
import os
from traits.api import Directory, Undefined
from soma import config as soma_config
from capsul.study_config.study_config import StudyConfigModule


class BrainVISAConfig(StudyConfigModule):
    '''
    Configuration module allowing to use `BrainVISA / Axon <http://brainvisa.info/axon/user_doc>`_ shared data in Capsul processes.

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

    shared_directory: str (filename)
        Study shared directory
     '''

    def __init__(self, study_config, configuration):
        super(BrainVISAConfig, self).__init__(study_config, configuration)
        study_config.add_trait('shared_directory',Directory(
            Undefined,
            output=False,
            desc='Study shared directory', groups=['brainvisa']))

        study_config.shared_directory = soma_config.BRAINVISA_SHARE
        # the following would be good but if Axon is not present, it will
        # use an unavailable FOM and cause an error.
        #if 'FomConfig' in self.study_config.modules \
                #and self.study_config.shared_fom in (None, ''):
            #self.study_config.shared_fom = 'shared-brainvisa-1.0'


    def initialize_module(self):
        '''
        '''
        from capsul.engine import CapsulEngine

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which should hold the reference values,
            # BUT values are actuallu defined from here...
            old_shared = self.study_config.shared_directory
            with self.study_config.engine.settings as session:
                config = session.config('axon', 'global')
                if config and config.shared_directory is Undefined:
                    config.shared_directory = old_shared
            self.sync_from_engine()
            self.sync_to_engine()
        else:
            # otherwise engine is "owned" by StudyConfig
            if 'capsul.engine.module.axon' \
                    not in self.study_config.engine._loaded_modules:
                self.study_config.engine.load_module(
                    'capsul.engine.module.axon')
            self.sync_to_engine()


    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.sync_to_engine,
                                          ['shared_directory', 'user_level'])
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers.setdefault(
            'capsul.engine.module.axon', []).append(self.sync_from_engine)


    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            return
        self._syncing = True
        try:
            with self.study_config.engine.settings as session:
                cif = self.study_config.engine.settings.config_id_field
                config = session.config('axon', 'global')
                shared_dir = self.study_config.shared_directory
                if shared_dir is Undefined:
                    shared_dir = None
                if config is None:
                    session.new_config(
                        'axon', 'global',
                        {'shared_directory': shared_dir,
                        'user_level': self.study_config.user_level,
                          cif: 'axon'})
                else:
                    config.shared_directory = shared_dir
                    config.user_level = self.study_config.user_level
        finally:
            del self._syncing


    def sync_from_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            return
        self._syncing = True
        try:
            with self.study_config.engine.settings as session:
                config = session.config('axon', 'global', any=True)
                if config:
                    shared_dir = config.shared_directory
                    if shared_dir is None:
                        shared_dir = Undefined
                    self.study_config.shared_directory = shared_dir
                    self.study_config.user_level = config.user_level
        finally:
            del self._syncing
