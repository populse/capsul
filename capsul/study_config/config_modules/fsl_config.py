import os
import os.path as osp
import six
from traits.api import File, Bool, Undefined, String

from soma.path import find_in_path
from capsul.study_config.study_config import StudyConfigModule


class FSLConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(FSLConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path'))
        self.study_config.add_trait('fsl_prefix', String('',
            desc='Prefix to add to FSL commands'))
        self.study_config.add_trait('use_fsl', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure FSL'))


    def initialize_module(self):
        """ Set up FSL environment variables according to current
        configuration.
        """
        if self.study_config.use_fsl is False:
            # Configuration is explicitely asking not to use FSL
            return
        elif self.study_config.use_fsl is True:
            # Configuration is explicitely asking to use FSL.
            # Configuration must be valid otherwise
            # try to update configuration and recheck is validity
            if self.assess_configuration_validity() is not None:
                self.auto_configuration()
                error_message = self.assess_configuration_validity()
                if error_message:
                    raise EnvironmentError(error_message)
        elif self.study_config.use_fsl is Undefined:
            # If use_fsl is not defined, FSL configuration is checked
            # and use_fsl is set to True if configuration is valid
            if self.assess_configuration_validity() is None:
                self.study_config.use_fsl = True
 
    def assess_configuration_validity(self):
        '''
        Check if the configuration is valid to run FLS and returns an error
        message if there is an error or None if everything is good.
        '''
        if self.study_config.fsl_config is not Undefined:
            if self.study_config.fsl_prefix:
                return 'FSL configuration must either use fsl_config or fsl_prefix but not both'
            if not osp.exists(self.study_config.fsl_config):
                return 'File "%s" does not exists' % self.study_config.fsl_config
            if not self.study_config.fsl_config.endswith('fsl.sh'):
                return 'File "%s" is not a path to fsl.sh script' % self.study_config.fsl_config
        else:
            fsl_dir = os.environ.get('FSLDIR')
            if fsl_dir:
                bet = '%s/bin/bet' % fsl_dir
                if not osp.exists(bet):
                    return 'FSL command %s cannot be found (check FSLDIR environment variable)' % bet
            elif not find_in_path('%sbet' % self.study_config.fsl_prefix):
                return 'FSL command "%sbet" cannot be found in PATH' % self.study_config.fsl_prefix
        return None
    
    def auto_configuration(self):
        bet = find_in_path('fsl*-bet')
        if bet:
            self.study_config.fsl_prefix = osp.basename(bet)[:-3]
