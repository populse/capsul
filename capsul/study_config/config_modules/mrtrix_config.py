# -*- coding: utf-8 -*-
'''
mrtrix configuration module

Classes
=======
:class:`MRTRIXConfig`
------------------
'''

from __future__ import absolute_import
from traits.api import File, Bool, Undefined

from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
# from capsul.subprocess.mrtrix import check_mrtrix_configuration


class MRTRIXConfig(StudyConfigModule):
    '''
    `mrtrix <https://www.mrtrix.org/>`_ configuration module
    '''

    def __init__(self, study_config, configuration):
        super(MRTRIXConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('mrtrix_path', File(
            Undefined,
            output=False,
            desc='Parameter to specify the mrtrix path', groups=['mrtrix']))
        self.study_config.add_trait('use_mrtrix', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure mrtrix',
            groups=['mrtrix']))

    def __del__(self):
        try:
            self.study_config.engine.settings.module_notifiers.get(
                'capsul.engine.module.mrtrix', []).remove(
                    self.sync_from_engine)
        except (ValueError, ReferenceError):
            pass

    def initialize_module(self):
        """ Set up mrtrix environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.mrtrix' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.mrtrix')
        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # TODO : do we need to add this tets for mrtrix as for afni/ants/fsl ?
        # # this test aims to raise an exception in case of incorrect setting,
        # # complying to capsul 2.x behavior.
        # if self.study_config.use_mrtrix is True:
        #     check_mrtrix_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, '[mrtrix_path, use_mrtrix]')
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.mrtrix'] = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'MRTRIXConfig' in self.study_config.modules \
                    and 'capsul.engine.module.mrtrix' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    config = session.config('mrtrix', 'global')
                    mrtrix_path = self.study_config.mrtrix_path
                    if mrtrix_path is Undefined:
                        mrtrix_path = None

                    if config is None:
                        session.new_config(
                            'mrtrix', 'global',
                            {'directory': mrtrix_path,
                             cif: 'mrtrix'})
                    else:
                        config.directory = mrtrix_path
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
            if 'MRTRIXConfig' in self.study_config.modules \
                    and 'capsul.engine.module.mrtrix' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    config = session.config('mrtrix', 'global')
                    if config:
                        directory = config.directory \
                            if config.directory not in (None, '') \
                            else Undefined
                        self.study_config.mrtrix_path = directory
                        if self.study_config.mrtrix_path not in (None,
                                                                 Undefined):
                            self.study_config.use_mrtrix = True
                        else:
                            self.study_config.use_mrtrix = False

        except ReferenceError:
            pass
        finally:
            del self._syncing
