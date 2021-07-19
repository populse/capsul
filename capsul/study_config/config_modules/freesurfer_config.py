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
from traits.api import File, Bool, Undefined, Directory

# Capsul import
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine


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
            desc="Path to 'FreeSurferEnv.sh'", groups=['freesurfer']))
        self.study_config.add_trait('freesurfer_subjectsdir', Directory(
            Undefined,
            desc='FreeSurfer subjects data directory', groups=['freesurfer']))
        self.study_config.add_trait("use_freesurfer", Bool(
            False,
            desc="If True, FreeSurfer configuration is set up on startup",
            groups=['freesurfer']))

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
            self.sync_to_engine,
            ['freesurfer_config', 'freesurfer_subjectsdir'])
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.freesurfer'] = [self.sync_from_engine]

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
                    params = {
                        'freesurfer_config': 'setup',
                        'freesurfer_subjectsdir': 'subjects_dir',
                    }
                    config = session.config('freesurfer', 'global')
                    if config is None:
                        values = {cif: 'freesurfer'}
                        for param, ceparam in six.iteritems(params):
                            val = getattr(self.study_config, param)
                            if val is Undefined:
                                val = None
                            values[ceparam] = val
                        session.new_config('freesurfer', 'global', values)
                    else:
                        for param, ceparam in six.iteritems(params):
                            val = getattr(self.study_config, param)
                            if val is Undefined:
                                val = None
                            setattr(config, ceparam, val)
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
                        params = {
                            'freesurfer_config': 'setup',
                            'freesurfer_subjectsdir': 'subjects_dir',
                        }
                        for param, ceparam in six.iteritems(params):
                            val = getattr(config, ceparam)
                            if val in (None, ''):
                                val = Undefined
                            setattr(self.study_config, param, val)

                        if self.study_config.freesurfer_config:
                            self.study_config.use_freesurfer = True
                        else:
                            self.study_config.use_freesurfer = False
        finally:
            del self._syncing
