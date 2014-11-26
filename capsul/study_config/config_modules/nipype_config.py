##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from soma.undefined import undefined
from traits.api import File

import nipype.interfaces.matlab as matlab
from nipype.interfaces import spm

from capsul.study_config.study_config import StudyConfigModule

class NipypeConfig(StudyConfigModule):
    
    dependencies = ['MatlabConfig', 'SpmConfig']
    
    def __init__(self, study_config, configuration):
        super(NipypeConfig, self).__init__(study_config, configuration)
        study_config.add_trait("use_nipype", Bool(
            Undefined,
            desc="If True, Nipype configuration is set up on startup"))
    
    def initialize_module(self):
        """ Set up Nipype environment variables according to current
        configuration.
        """
        if self.study_config.use_nipype is False:
            # Configuration is explicitely asking not to use Nipype
            return
        if self.study_config.use_nipype is Undefined:
            # If use_nipype is not defined, Nipype configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        else:
            # If use_nipype is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True
        
        if self.study_config.use_matlab:
            matlab.MatlabCommand.set_default_matlab_cmd(
                self.study_config.matlab_exec + " -nodesktop -nosplash")
        if self.study_config.use_spm == 'matlab':
            matlab.MatlabCommand.set_default_paths(self.study_config.spm_directory)
            spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)           
        elif self.study_config.use_spm == 'standalone':
            # If the spm interface has been imported properly, configure this
            # interface
            spm.SPMCommand.set_mlab_paths(
                matlab_cmd=self.study_config.spm_exec + " run script",
                use_mcr=True)
        
        self.study_config.use_nipype = True

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.initialize_module, 'use_nipype')
