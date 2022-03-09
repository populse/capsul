# -*- coding: utf-8 -*-
'''
ANTS configuration module

Classes
=======
:class:`ANTSConfig`
------------------
'''

from __future__ import absolute_import
from traits.api import File, Bool, Undefined

from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
from capsul.subprocess.ants import check_ants_configuration

class ANTSConfig(StudyConfigModule):
    '''
    `ANTS <http://stnava.github.io/ANTs/>`_ configuration module
    '''

    def __init__(self, study_config, configuration):
        super(ANTSConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('ants_path', File(
            Undefined,
            output=False,
            desc='Parameter to specify the ANTS path', groups=['ants']))
        self.study_config.add_trait('use_ants', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure ANTS',
            groups=['ants']))

    def __del__(self):
        try:
            self.study_config.engine.settings.module_notifiers.get(
                'capsul.engine.module.ants', []).remove(self.sync_from_engine)
        except (ValueError, ReferenceError):
            pass

    def initialize_module(self):
        """ Set up ANTS environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.ants' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.ants')
        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # this test aims to raise an exception in case of incorrect setting,
        # complying to capsul 2.x behavior.
        if self.study_config.use_ants is True:
            check_ants_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, '[ants_path, use_ants]')
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.ants'] = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'ANTSConfig' in self.study_config.modules \
                    and 'capsul.engine.module.ants' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    config = session.config('ants', 'global')
                    ants_path = self.study_config.ants_path
                    if ants_path is Undefined:
                        ants_path = None

                    if config is None:
                        session.new_config(
                            'ants', 'global',
                            {'directory': ants_path,
                             cif: 'ants'})
                    else:
                        config.directory = ants_path
                    del config
                del session
        finally:
            del self._syncing

    def sync_from_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'ANTSConfig' in self.study_config.modules \
                    and 'capsul.engine.module.ants' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    config = session.config('ants', 'global')
                    if config:
                        directory = config.directory \
                            if config.directory not in (None, '') \
                            else Undefined
                        self.study_config.ants_path = directory
                        if self.study_config.ants_path not in (None,
                                                                   Undefined):
                            self.study_config.use_ants = True
                        else:
                            self.study_config.use_ants = False

        except ReferenceError:
            pass
        finally:
            del self._syncing
