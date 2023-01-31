# -*- coding: utf-8 -*-
'''
SPM configuration module

Classes
=======
:class:`SPMConfig`
------------------
'''

from __future__ import absolute_import

from traits.api import Directory, File, Bool, Enum, Undefined, Str
from capsul.study_config.study_config import StudyConfigModule
from capsul.subprocess.spm import check_spm_configuration
from capsul.engine import CapsulEngine
import glob
import os
import os.path as osp


class SPMConfig(StudyConfigModule):
    """ SPM configuration.

    There is two ways to configure SPM:
        * the first one requires to configure matlab and then to set the spm
          directory.
        * the second one is based on a standalone version of spm and requires
          to set the spm executable directory.
    """

    dependencies = ["MatlabConfig"]

    def __init__(self, study_config, configuration):
        super(SPMConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait("spm_directory", Directory(
            Undefined,
            output=False,
            desc="Directory containing SPM.",
            groups=['spm']))
        self.study_config.add_trait("spm_standalone", Bool(
            Undefined,
            desc="If True, use the standalone version of SPM.",
            groups=['spm']))
        self.study_config.add_trait('spm_version', Str(
            Undefined, output=False,
            desc='Version string for SPM: "12", "8", etc.',
            groups=['spm']))
        self.study_config.add_trait("spm_exec", File(
            Undefined,
            output=False,
            desc="SPM standalone (MCR) command path.",
            groups=['spm']))
        self.study_config.add_trait("use_spm", Bool(
            Undefined,
            desc="If True, SPM configuration is checked on module initialization.",
            groups=['spm']))

    def initialize_module(self):
        if 'capsul.engine.module.spm' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.spm')

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # this test aims to raise an exception in case of incorrect setting,
        # complying to capsul 2.x behavior.
        if self.study_config.use_spm is True:
            check_spm_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.sync_to_engine,
                                          "[use_spm, spm_+]")
        #  WARNING ref to self in callback
        self.study_config.engine.settings.module_notifiers[
            'capsul.engine.module.spm'] = [self.sync_from_engine]

    def sync_from_engine(self, param=None, value=None):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'SPMConfig' in self.study_config.modules \
                    and 'capsul.engine.module.spm' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    configs = list(session.configs('spm', 'global'))
                    configs = sorted(
                        configs,
                        key=lambda x: (-int(x.version)
                                       if x.version not in ('', None)
                                       else 0)
                                       * 1000 - int(bool(x.standalone)))
                    if len(configs) != 0:
                        config = configs[0]
                        directory = config.directory \
                            if config.directory not in (None, '') \
                            else Undefined
                        self.study_config.spm_directory = directory
                        self.study_config.spm_standalone \
                            = bool(config.standalone)
                        if config.version is not None:
                            self.study_config.spm_version = config.version
                        else:
                            self.study_config.spm_version = '0'
                        if self.study_config.spm_directory not in (None,
                                                                  Undefined):
                            if config.version:
                                spm_exec = \
                                    osp.join(self.study_config.spm_directory,
                                            'run_spm%s.sh' % config.version)
                                if os.path.exists(spm_exec):
                                    spm_exec = [spm_exec]
                                else:
                                    spm_exec = []
                            else:
                                spm_exec = glob.glob(osp.join(
                                    self.study_config.spm_directory,
                                    'run_spm*.sh'))
                            if len(spm_exec) != 0:
                                self.study_config.spm_exec = spm_exec[0]
                            else:
                                self.study_config.spm_exec = Undefined
                            self.study_config.use_spm = True
                        else:
                            self.study_config.use_spm = False
        finally:
            del self._syncing

    def sync_to_engine(self):
        if getattr(self, '_syncing', False):
            # manage recursive calls
            return
        self._syncing = True
        try:
            if 'SPMConfig' in self.study_config.modules \
                    and 'capsul.engine.module.spm' \
                        in self.study_config.engine._loaded_modules:
                with self.study_config.engine.settings as session:
                    cif = self.study_config.engine.settings.config_id_field
                    version = self.study_config.spm_version
                    if version in (None, Undefined):
                        version = '12'
                    standalone = (self.study_config.spm_standalone is True)
                    id = 'spm%s%s' % (version,
                                      '-standalone' if standalone else '')
                    query = '%s == "%s"' % (cif, id)
                    config = session.config('spm', 'global', selection=query)
                    if config is None:
                        # FIXME: do we keep only one config ? yes for now.
                        config_ids = [getattr(conf, cif)
                                      for conf in session.configs('spm',
                                                                  'global')
                                      if getattr(conf, cif) != id]
                        for config_id in config_ids:
                            session.remove_config('spm', 'global', config_id)
                        session.new_config(
                            'spm', 'global',
                            {'directory':
                                self.study_config.spm_directory
                                    if self.study_config.spm_directory
                                        is not Undefined
                                    else None,
                            'version': version,
                            'standalone': standalone,
                            cif: id})
                    else:
                        tparam = {'spm_directory': 'directory',
                                  'spm_standalone': 'standalone',
                                  'spm_version': 'version'}
                        params = ['spm_directory', 'spm_standalone',
                                  'spm_version']
                        defaults = {'directory': None, 'standalone': False,
                                    'version': '12'}
                        for p in params:
                            val = getattr(self.study_config, p)
                            ceparam = tparam[p]
                            if val is Undefined:
                                val = defaults.get(ceparam, None)
                            setattr(config, ceparam, val)
        finally:
            del self._syncing
