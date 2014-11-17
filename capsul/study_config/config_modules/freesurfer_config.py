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
from capsul.study_config.config_utils import environment


class FreeSurferConfig(object):
    """ Class to set up freesurfer configuration.

    Parse the 'SetUpFreeSurfer.sh' file and update dynamically the system
    environment.
    """
    def __init__(self, study_config):
        """ Initilaize the FreeSurferConfig class.

        Parameters
        ----------
        study_config: StudyConfig object
            the study configuration we want to update in order to deal with 
            freesurfer functions.
        """
        study_config.add_trait("fs_config", File(
            Undefined,
            output=False,
            desc="Parameter to specify the 'SetUpFreeSurfer.sh' path"))
        study_config.add_trait("use_fs", Bool(
            Undefined,
            output=False,
            desc="Parameter to tell that we need to configure FreeSurfer"))

        self.study_config = study_config
        self.study_config.on_trait_change(self._use_fs_changed, "use_fs")

    def _use_fs_changed(self, use_fs_value):
        """ Event to setup FreeSurfer environment.

        Parameters
        ----------
        use_fs_value: bool
            the current value of the 'use_fs' trait.
        """
        # If the option is True
        if use_fs_value:

            # Get the 'SetUpFreeSurfer.sh' path from the study configuration
            # elements
            fs_config_file = self.study_config.get_trait_value("fs_config")

            # If the 'SetUpFreeSurfer.sh' path has been defined
            if fs_config_file is not Undefined \
                    and os.path.exists(fs_config_file):

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

            # Otherwise raise an exception
            else:
                raise Exception("No FreeSurfer configuration file specified. "
                                "It is impossible to configure FreeSurfer.")
