from traits.api import File, Bool, Undefined, String

from capsul.study_config.study_config import StudyConfigModule
from capsul.subprocess.fsl import check_fsl_configuration

class FSLConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(FSLConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path'))
        self.study_config.add_trait('fsl_prefix', String(Undefined,
            desc='Prefix to add to FSL commands'))
        self.study_config.add_trait('use_fsl', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure FSL'))


    def initialize_module(self):
        """ Set up FSL environment variables according to current
        configuration.
        """
        if self.study_config.use_fsl is True:
            check_fsl_configuration(self.study_config)
