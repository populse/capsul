from traits.api import Directory, File, Bool, Enum, Undefined, Str

from capsul.study_config.study_config import StudyConfigModule
#from capsul.subprocess.spm import check_spm_configuration
from capsul.subprocess.spm import sync_from_engine, sync_to_engine
from soma.functiontools import SomaPartial


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
        sync_from_engine(self.study_config)

    def initialize_callbacks(self):
        self.study_config.engine.spm.on_trait_change(
            SomaPartial(sync_from_engine, self.study_config))
        self.study_config.on_trait_change(
            SomaPartial(sync_to_engine, self.study_config),
            "[use_spm, spm_+]")
        #if self.study_config.use_spm is True:
            #check_spm_configuration(self.study_config)

