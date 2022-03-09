# -*- coding: utf-8 -*-
'''
AFNI configuration module

Classes
=======
:class:`AFNIConfig`
------------------
'''

from __future__ import absolute_import
from traits.api import File, Bool, Undefined

from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
from capsul.subprocess.afni import check_afni_configuration

class AFNIConfig(StudyConfigModule):
    '''
    `AFNI <https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/index.html>`_ configuration module
    '''

    def __init__(self, study_config, configuration):
        super(AFNIConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('afni_path', File(
            Undefined,
            output=False,
            desc='Parameter to specify the AFNI path', groups=['afni']))
        self.study_config.add_trait('use_afni', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure AFNI',
            groups=['afni']))

    def __del__(self):
        try:
            self.study_config.engine.settings.module_notifiers.get(
                'capsul.engine.module.afni', []).remove(self.sync_from_engine)
        except (ValueError, ReferenceError):
            pass

    def initialize_module(self):
        """ Set up AFNI environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.afni' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.afni')
        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # this test aims to raise an exception in case of incorrect setting,
        # complying to capsul 2.x behavior.
        if self.study_config.use_afni is True:
            check_afni_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, '[afni_path, use_afni]')
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.afni'] = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'AFNIConfig' in self.study_config.modules \
                    and 'capsul.engine.module.afni' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    config = session.config('afni', 'global')
                    afni_path = self.study_config.afni_path
                    if afni_path is Undefined:
                        afni_path = None

                    if config is None:
                        session.new_config(
                            'afni', 'global',
                            {'directory': afni_path,
                             cif: 'afni'})
                    else:
                        config.directory = afni_path
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
            if 'AFNIConfig' in self.study_config.modules \
                    and 'capsul.engine.module.afni' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    config = session.config('afni', 'global')
                    if config:
                        directory = config.directory \
                            if config.directory not in (None, '') \
                            else Undefined
                        self.study_config.afni_path = directory
                        if self.study_config.afni_path not in (None,
                                                                   Undefined):
                            self.study_config.use_afni = True
                        else:
                            self.study_config.use_afni = False

        except ReferenceError:
            pass
        finally:
            del self._syncing
