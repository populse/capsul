##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
import six
from traits.api import File, Bool, Undefined
from capsul.study_config.config_utils import environment
from capsul.study_config.study_config import StudyConfigModule


class FSLConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(FSLConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path'))
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
        if self.study_config.use_fsl is Undefined:
            # If use_fsl is not defined, FSL configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        else:
            # If use_fsl is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True

        # Get the fsl.sh path from the study configuration elements
        fsl_config_file = self.study_config.fsl_config

        # If the fsl.sh path has been defined
        if fsl_config_file is not Undefined and \
           os.path.exists(fsl_config_file):
            # Parse the fsl environment
            envfsl = environment(fsl_config_file)
            if "FSLDIR" not in envfsl and "FSLDIR" not in os.environ:
                # assume the fsl.sh script is in $FSLDIR/etc/fslconf/fsl.sh
                envfsl["FSLDIR"] = os.path.dirname(os.path.dirname(
                    os.path.dirname(fsl_config_file)))
            if envfsl.get("FSLDIR", "") != os.environ.get("FSLDIR", ""):
                # Set the fsl environment
                for envname, envval in six.iteritems(envfsl):
                    if envname in os.environ:
                        if envname.startswith("FSL"):
                            os.environ[envname] = envval
                        else:
                            os.environ[envname] += ":" + envval
                    else:
                        os.environ[envname] = envval

                # No error detected in configuration, set use_fsl to
                # True
                self.study_config.use_fsl = True
        else:
            # Error in configuration, do not let use_fsl = Undefined
            self.study_config.use_fsl = False
            if force_configuration:
                raise EnvironmentError(
                    "No valid FSL configuration file specified. "
                    "It is impossible to configure FSL.")

    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.initialize_module, 'use_fsl')
