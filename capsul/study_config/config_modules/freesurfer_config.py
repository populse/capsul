#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os

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
        study_config.add_trait("freesurfer_config", File(
            Undefined,
            desc="Path to 'SetUpFreeSurfer.sh'"))
        study_config.add_trait("use_freesurfer", Bool(
            Undefined,
            desc="If True, FreeSurfer configuration is set up on startup"))

    def initialize_module(self, study_config):
        """ Set up Freesurfer environment variables according to current
        configuration.
        """
        if study_config.use_freesurfer is False:
            # Configuration is explicitely asking not to use FreeSurfer
            return
        if study_config.use_freesurfer is Undefined:
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
        fs_config_file = study_config.freesurfer_config

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
                for envname, envval in envfs.iteritems():
                    if envname in os.environ:
                        if envname.startswith(("FS", "FREESURFER")):
                            os.environ[envname] = envval
                        else:
                            os.environ[envname] += ":" + envval
                    else:
                        os.environ[envname] = envval
                
                # No error detected in configuration, set use_freesurfer to
                # True
                study_config.use_freesurfer = True
            elif force_configuration:
                raise EnvironmentError("FreeSurfer configuration file (%s) "
                                       "does not exists. It is impossible to "
                                       "configure FreeSurfer." % \
                                       fs_config_file)
            else:
                #Error in configuration, do not let use_freesurfer = Undefined
                study_config.use_freesurfer = False
        elif force_configuration:
            raise EnvironmentError("No FreeSurfer configuration file "
                                   "specified. It is impossible to configure "
                                   "FreeSurfer.")
        else:
            # Error in configuration, do not let use_freesurfer = Undefined
            study_config.use_freesurfer = False
