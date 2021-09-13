# -*- coding: utf-8 -*-
'''
NiPype configuration module

Classes
=======
:class:`NipypeConfig`
---------------------
'''

from __future__ import absolute_import

import glob
import os

# TRAITS import
from traits.api import Bool, Undefined, List, Directory

# NIPYPE import
try:
    import nipype.interfaces.matlab as matlab
    from nipype.interfaces import spm
    has_nipype = True
except ImportError:
    has_nipype = False

# CAPSUL import
from capsul.study_config.study_config import StudyConfigModule
import capsul.engine.module.nipype as ce_nipype


class NipypeConfig(StudyConfigModule):
    """ Nipype configuration.

    In order to use nipype spm, fsl and freesurfer interfaces, we need to
    configure the nipype module.
    """

    dependencies = []

    def __init__(self, study_config, configuration):
        """ Initialize the NipypeConfig class.
        """
        super(NipypeConfig, self).__init__(study_config, configuration)
        study_config.add_trait("use_nipype", Bool(
            Undefined,
            desc="If True, Nipype configuration is set up on startup.",
            groups=['nipype']))
        study_config.add_trait("add_to_default_matlab_path", List(
            Directory,
            default=[],
            desc="Paths that are added to Matlab default path.",
            groups=['nipype']))
        self.has_nipype = has_nipype

    def initialize_module(self):
        """ Set up Nipype environment variables according to current
        configuration.
        """
        if 'capsul.engine.module.nipype' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module(
                'capsul.engine.module.nipype')
        ce_nipype.ensure_config_exists(self.study_config.engine)
        if not self.has_nipype:
            self.study_config.use_nipype = False
            return
        if self.study_config.use_nipype is False:
            # Configuration is explicitly asking not to use Nipype
            return
        elif self.study_config.use_nipype is True:
            # If use_nipype is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True
        else:
            # If use_nipype is not defined, Nipype configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False

        # Configure matlab for nipype
        if self.study_config.use_matlab:
            matlab.MatlabCommand.set_default_matlab_cmd(
                self.study_config.matlab_exec + " -nodesktop -nosplash")

        # Configure spm for nipype
        if self.study_config.use_spm is True:

            # Standalone spm version
            if self.study_config.spm_standalone is True:
                spm.SPMCommand.set_mlab_paths(
                    matlab_cmd=self.study_config.spm_exec + " " \
                        + glob.glob(os.path.join(
                            self.study_config.spm_directory, 'mcr', 'v*'))[0] \
                        + " script",
                    use_mcr=True)
            # Matlab spm version
            else:
                matlab.MatlabCommand.set_default_paths(
                    [self.study_config.spm_directory] +
                    self.study_config.add_to_default_matlab_path)
                spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)  

        self.study_config.use_nipype = True

    def initialize_callbacks(self):
        """ When the 'use_nipype' trait changes, configure nipype with the new
        setting.
        """
        self.study_config.on_trait_change(self.initialize_module, "use_nipype")
