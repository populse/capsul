##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import six

# Trait import
from traits.api import File, Bool, Undefined

# Capsul import
from capsul.study_config.study_config import StudyConfigModule
from capsul.study_config.config_utils import environment


class FreeSurferConfig(StudyConfigModule):
    """ Class to set up freesurfer configuration.

    Parse the 'SetUpFreeSurfer.sh' file and update dynamically the system
    environment.
    """
    def __init__(self, study_config, configuration):
        """ Initilaize the FreeSurferConfig class.

        Parameters
        ----------
        study_config: StudyConfig object
            the study configuration we want to update in order to deal with 
            freesurfer functions.
        """
        super(FreeSurferConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait("freesurfer_config", File(
            Undefined,
            desc="Path to 'SetUpFreeSurfer.sh'"))
        self.study_config.add_trait("use_freesurfer", Bool(
            Undefined,
            desc="If True, FreeSurfer configuration is set up on startup"))

    def initialize_module(self):
        """ Set up Freesurfer environment variables according to current
        configuration.
        """
        if self.study_config.use_freesurfer is False:
            # Configuration is explicitely asking not to use FreeSurfer
            return
        if self.study_config.use_freesurfer is Undefined:
            # If use_freesurfer is not defined, FreeSurfer configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        else:
            # If use_freesurfer is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True

        # Get the 'SetUpFreeSurfer.sh' path from the study configuration
        # elements
        fs_config_file = self.study_config.freesurfer_config

        # If the 'SetUpFreeSurfer.sh' path has been defined
        if fs_config_file is not Undefined:
            if os.path.exists(fs_config_file):
                # Parse the fs environment: check if the 'FREESURFER_HOME'
                # environment varibale is already set and use it to configure
                # freesurfer
                fs_home = os.environ.get("FREESURFER_HOME", None)
                env = {}
                if fs_home is not None:
                    env["FREESURFER_HOME"] = fs_home
                envfs = environment(fs_config_file, env)

                # Set the fs environment
                for envname, envval in six.iteritems(envfs):
                    if envname in os.environ:
                        if envname.startswith(("FS", "FREESURFER")):
                            os.environ[envname] = envval
                        else:
                            os.environ[envname] += ":" + envval
                    else:
                        os.environ[envname] = envval

                # No error detected in configuration, set use_freesurfer to
                # True
                self.study_config.use_freesurfer = True
            else:
                #Error in configuration, do not let use_freesurfer = Undefined
                self.study_config.use_freesurfer = False
                if force_configuration:
                    raise EnvironmentError(
                        "FreeSurfer configuration file (%s) does not exist. "
                        "It is impossible to configure FreeSurfer." % \
                        fs_config_file)
        else:
            # Error in configuration, do not let use_freesurfer = Undefined
            self.study_config.use_freesurfer = False
            if force_configuration:
                raise EnvironmentError(
                  "No FreeSurfer configuration file specified. "
                  "It is impossible to configure FreeSurfer.")

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.initialize_module,
                                          'use_freesurfer')
