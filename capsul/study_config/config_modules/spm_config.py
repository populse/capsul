##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Directory, File, Bool, Undefined
from capsul.study_config.config_utils import find_spm

try:
    import nipype.interfaces.matlab as matlab
    from nipype.interfaces import spm
except ImportError:
    matlab = None
    spm = None

class SPMConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('spm_directory', Directory(
            Undefined,
            output=False,
            desc='Parameter to set the SPM directory',
            exists=True))
        study_config.add_trait('spm_exec_cmd', File(
            Undefined,
            output=False,
            desc='parameter to set the SPM standalone (MCR) command path',
            exists=True))
        study_config.add_trait('use_spm_mcr', Bool(
            Undefined,
            output=False,
            desc=('Parameter to select way we execute SPM: the standalone '
                  'or matlab version')))

        self.study_config = study_config
        study_config.on_trait_change(self._use_spm_mcr_changed,'use_spm_mcr')
    
    
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
                    "It is impossible to configure spm stanalone version.")

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
