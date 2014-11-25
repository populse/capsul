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
        study_config.add_trait("use_nipype", Bool(
            Undefined,
            desc="If True, Nipype configuration is set up on startup"))
    
    def initialize_module(self, study_config):
        """ Set up Nipype environment variables according to current
        configuration.
        """
        if study_config.use_nipype is False:
            # Configuration is explicitely asking not to use Nipype
            return
        if study_config.use_nipype is Undefined:
            # If use_nipype is not defined, Nipype configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        else:
            # If use_nipype is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True
        
        if study_config.use_matlab:
            matlab.MatlabCommand.set_default_matlab_cmd(
                study_config.matlab_exec + " -nodesktop -nosplash")
        if study_config.use_spm == 'matlab':
            matlab.MatlabCommand.set_default_paths(study_config.spm_directory)
            spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)           
        elif study_config.use_spm == 'standalone':
            # If the spm interface has been imported properly, configure this
            # interface
            spm.SPMCommand.set_mlab_paths(
                matlab_cmd=study_config.spm_exec + " run script",
                use_mcr=True)
        
        study_config.use_nipype = True
    
    def _use_spm_mcr_changed(self, old_trait_value, new_trait_value):
        """ Event to setup SPM environment

        We interact with spm through nipype. If the nipype spm interface
        has not been imported properly, do nothing.

        .. note :

            If the path to the spm standalone binaries are not specified,
            raise an exception.
        """
        # Set up standalone SPM version
        if new_trait_value:

            # To set up standalone SPM version, need the path to the
            # binaries
            if not self.study_config.spm_exec_cmd is not undefined:

                # We interact with spm through nipype. If the spm
                # interface has been imported properly, configure this
                # interface
                if spm is not None:
                    spm.SPMCommand.set_mlab_paths(
                        matlab_cmd=self.study_config.spm_exec_cmd + " run script",
                        use_mcr=True)

            # Otherwise raise an exception
            else:
                raise Exception(
                    "No SPM execution command specified. "
                    "It is impossible to configure spm standlone version.")

        # Setup the classical matlab spm version
        else:

            # We interact with spm through nipype. If the spm
            # interface has been imported properly, configure this
            # interface
            if spm is not None:
                spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)

            # Need to set up the matlab path
            if self.study_config.matlab_exec is not undefined:

                # If the smatlab interface has been imported properly,
                # configure this interface
                if matlab is not None:
                    matlab.MatlabCommand.set_default_matlab_cmd(
                        self.study_config.matlab_exec + " -nodesktop -nosplash")

            # Otherwise raise an exception
            else:
                raise Exception(
                    "No MATLAB binary specified. "
                    "It is impossible to configure the matlab spm version.")

            # Need to set up the spm path
            # If the spm directory is not specified, try to find it
            # automatically
            if self.study_config.spm_directory is undefined:
                self.study_config.spm_directory = find_spm(self.study_config.matlab_exec)

            # If the smatlab interface has been imported properly,
            # configure this interface
            if matlab is not None:
                matlab.MatlabCommand.set_default_paths(self.study_config.spm_directory)
