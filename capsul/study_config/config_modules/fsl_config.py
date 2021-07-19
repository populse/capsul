# -*- coding: utf-8 -*-
'''
FSL configuration module

Classes
=======
:class:`FSLConfig`
------------------
'''

from __future__ import absolute_import
from traits.api import File, Bool, Undefined, String

from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
from capsul.subprocess.fsl import check_fsl_configuration
import os.path as osp

class FSLConfig(StudyConfigModule):
    '''
    `FSL <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki>`_ configuration module
    '''

    def __init__(self, study_config, configuration):
        super(FSLConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path', groups=['fsl']))
        self.study_config.add_trait('fsl_prefix', String(Undefined,
            desc='Prefix to add to FSL commands', groups=['fsl']))
        self.study_config.add_trait('use_fsl', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure FSL',
            groups=['fsl']))

    def __del__(self):
        try:
            self.study_config.engine.settings.module_notifiers.get(
                'capsul.engine.module.fsl', []).remove(self.sync_from_engine)
        except (ValueError, ReferenceError):
            pass

    def initialize_module(self):
        """ Set up FSL environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.fsl' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.fsl')
        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # this test aims to raise an exception in case of incorrect setting,
        # complying to capsul 2.x behavior.
        if self.study_config.use_fsl is True:
            check_fsl_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine, '[fsl_config, fsl_prefix, use_fsl]')
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.fsl'] = [self.sync_from_engine]

    def sync_to_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'FSLConfig' in self.study_config.modules \
                    and 'capsul.engine.module.fsl' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    config = session.config('fsl', 'global')
                    fsl_conf = self.study_config.fsl_config
                    if fsl_conf is Undefined:
                        fsl_conf = None
                        fsl_dir = None
                    else:
                        fsl_dir = osp.dirname(fsl_conf)
                        if fsl_dir.endswith('/etc/fslconf'):
                            fsl_dir = osp.dirname(osp.dirname(fsl_dir))
                        elif fsl_dir.endswith('/etc'):
                            fsl_dir = osp.dirname(fsl_dir)
                    if config is None:
                        session.new_config(
                            'fsl', 'global',
                            {'directory': fsl_dir,
                             'config': fsl_conf,
                             'prefix': self.study_config.fsl_prefix
                                if self.study_config.fsl_prefix
                                    is not Undefined
                                else None,
                             cif: 'fsl'})
                    else:
                        tparam = {'fsl_config': 'config',
                                  'fsl_prefix': 'prefix'}
                        if param is not None:
                            if param not in ('use_fsl', ):
                                params = [param]
                            else:
                                params = []
                        else:
                            params = ['fsl_config', 'fsl_prefix']
                        defaults = {'prefix': None, 'config': None}
                        for p in params:
                            val = getattr(self.study_config, p)
                            ceparam = tparam[p]
                            if val is Undefined:
                                val = defaults.get(ceparam, None)
                            setattr(config, ceparam, val)
                        if 'fsl_config' in params:
                            config.directory = fsl_dir
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
            if 'FSLConfig' in self.study_config.modules \
                    and 'capsul.engine.module.fsl' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    config = session.config('fsl', 'global')
                    if config:
                        directory = config.directory \
                            if config.directory not in (None, '') \
                            else Undefined

                        self.study_config.fsl_config = config.config \
                            if config.config is not None else Undefined
                        self.study_config.fsl_prefix = config.prefix \
                            if config.prefix is not None else Undefined
                        if self.study_config.fsl_config not in (
                                    '', None, Undefined)\
                                or self.study_config.fsl_prefix not in (
                                    '', None, Undefined):
                            self.study_config.use_fsl = True
                        else:
                            self.study_config.use_fsl = False
        except ReferenceError:
            pass
        finally:
            del self._syncing
