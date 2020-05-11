# -*- coding: utf-8 -*-
'''
FreeSurfer configuration module

Classes
=======
:class:`FreeSurferConfig`
-------------------------
'''

# System import
from __future__ import absolute_import
import os
import six

# Trait import
from traits.api import File, Bool, Undefined

# Capsul import
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
from capsul.engine import settings


class FreeSurferConfig(StudyConfigModule):
    """ Class to set up freesurfer configuration.

    Parse the 'SetUpFreeSurfer.sh' file and update dynamically the system
    environment.
    """
    def __init__(self, study_config, configuration):
        """ Initilaize the FreeSurferConfig class.

        Parameters
        ----------
        study_config: StudyConfig object
            the study configuration we want to update in order to deal with 
            freesurfer functions.
        """
        super(FreeSurferConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait("freesurfer_config", File(
            Undefined,
            desc="Path to 'FreeSurferEnv.sh'"))
        self.study_config.add_trait("use_freesurfer", Bool(
            Undefined,
            desc="If True, FreeSurfer configuration is set up on startup"))

    def initialize_module(self):
        """ Set up FSL environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.freesurfer' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module(
                'capsul.engine.module.freesurfer')
        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, 'freesurfer_config')
        settings.SettingsSession.module_notifiers['freesurfer'] \
            = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'FreeSurferConfig' in self.study_config.modules \
                    and 'capsul.engine.module.freesurfer' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    config = session.config('freesurfer', 'global')
                    fs_setup = self.study_config.freesurfer_config
                    if fs_setup is Undefined:
                        fs_setup = None
                    if config is None:
                        session.new_config(
                            'freesurfer', 'global',
                            {'setup': fs_setup,
                             cif: 'freesurfer'})
                    else:
                        val = self.study_config.fs_setup
                        if val is Undefined:
                            val = None
                        setattr(config, 'setup', val)
        finally:
            del self._syncing

    def sync_from_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'FreeSurferConfig' in self.study_config.modules \
                    and 'capsul.engine.module.freesurfer' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    config = session.config('freesurfer', 'global')
                    if config:
                        fs_setup = config.setup \
                            if config.setup not in (None, '') \
                            else Undefined

                        self.study_config.freesurfer_config = fs_setup
                        if fs_setup:
                            self.study_config.use_freesurfer = True
                        else:
                            self.study_config.use_freesurfer = False
        finally:
            del self._syncing


