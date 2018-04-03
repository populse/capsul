from traits.api import Directory, File, Bool, Enum, Undefined, Str

from capsul.study_config.study_config import StudyConfigModule
from capsul.subprocess.spm import check_spm_configuration




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
        if self.study_config.use_spm is True:
            check_spm_configuration(self.study_config)
        
