'''
SPM configuration module

Classes
=======
:class:`SPMConfig`
------------------
'''

from traits.api import Directory, File, Bool, Enum, Undefined, Str

from capsul.study_config.study_config import StudyConfigModule
from capsul.subprocess.spm import check_spm_configuration
from soma.functiontools import SomaPartial
from capsul.engine import CapsulEngine
import glob
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
            desc="Directory containing SPM."))
        self.study_config.add_trait("spm_standalone", Bool(
            Undefined,
            desc="If True, use the standalone version of SPM."))
        self.study_config.add_trait('spm_version', Str(
            Undefined, output=False,
            desc='Version string for SPM: "12", "8", etc.'))
        self.study_config.add_trait("spm_exec", File(
            Undefined,
            output=False,
            desc="SPM standalone (MCR) command path."))
        self.study_config.add_trait("use_spm", Bool(
            Undefined,
            desc="If True, SPM configuration is checked on module initialization."))

    def initialize_module(self):
        if 'capsul.engine.module.spm' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.spm')
            self.study_config.engine.init_module('capsul.engine.module.spm')

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
        # this test aims to raise an exception in case of incorrect setting,
        # complygin to capsul 2.x behavior.
        if self.study_config.use_spm is True:
            check_spm_configuration(self.study_config)

    def initialize_callbacks(self):
        self.study_config.engine.spm.on_trait_change(self.sync_from_engine)
        self.study_config.on_trait_change(self.sync_to_engine,
                                          "[use_spm, spm_+]")

    def sync_from_engine(self):
        if 'SPMConfig' in self.study_config.modules \
                and 'capsul.engine.module.spm' \
                    in self.study_config.engine.modules:
            engine = self.study_config.engine.spm
            self.study_config.spm_directory = engine.directory
            self.study_config.spm_standalone = engine.standalone
            self.study_config.spm_version = engine.version
            if self.study_config.spm_directory not in (None, Undefined):
                spm_exec = glob.glob(osp.join(self.study_config.spm_directory,
                                              'mcr', 'v*'))
                if len(spm_exec) != 0:
                    self.study_config.spm_exec = spm_exec[0]
                else:
                    self.study_config.spm_exec = Undefined
            else:
                self.study_config.spm_exec = Undefined
            self.study_config.use_spm = engine.use

    def sync_to_engine(self):
        if 'SPMConfig' in self.study_config.modules \
                and 'capsul.engine.module.spm' \
                    in self.study_config.engine.modules:
            engine = self.study_config.engine.spm
            engine.directory = self.study_config.spm_directory
            engine.standalone = self.study_config.spm_standalone
            engine.version = self.study_config.spm_version
            engine.use = self.study_config.use_spm

