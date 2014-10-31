##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
from traits.api import File, Bool, Undefined
from capsul.study_config.config_utils import environment


class FSLConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('fsl_config', File(
            Undefined,
            output=False,
            desc='Parameter to specify the fsl.sh path'))
        study_config.add_trait('use_fsl', Bool(
            Undefined,
            output=False,
            desc='Parameter to tell that we need to configure FSL'))

        self.study_config = study_config
        self.study_config.on_trait_change(self._use_fsl_changed, 'use_fsl')
        self.study_config.on_trait_change(self._fsl_config_changed,
                                          'fsl_config')

    def _fsl_config_changed(self, new_trait_value):
        """ Event to setup FSL environment
        """
        if new_trait_value is not Undefined:
            if not os.path.exists(new_trait_value):
                self.study_config.use_fsl = False

    def _use_fsl_changed(self, new_trait_value):
        """ Event to setup FSL environment
        """
        # If the option is True
        if new_trait_value:

            # Get the fsl.sh path from the study configuration elements
            fsl_config_file = self.study_config.get_trait_value("fsl_config")

            # If the fsl.sh path has been defined
            if fsl_config_file is not Undefined \
                    and os.path.exists(fsl_config_file):

                # Parse the fsl environment
                envfsl = environment(fsl_config_file)
                if (not envfsl["LD_LIBRARY_PATH"] in
                   os.environ.get("LD_LIBRARY_PATH", [])):

                    # Set the fsl environment
                    for envname, envval in envfsl.iteritems():
                        if envname in os.environ:
                            if envname.startswith("FSL"):
                                os.environ[envname] = envval
                            else:
                                os.environ[envname] += ":" + envval
                        else:
                            os.environ[envname] = envval

            # Otherwise raise an exception
            else:
                self.study_config.use_fsl = False
                raise Exception("No valid FSL configuration file specified. "
                                "It is impossible to configure FSL.")
