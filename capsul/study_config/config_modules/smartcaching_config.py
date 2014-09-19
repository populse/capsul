##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool
try:
    from run_with_cache import _joblib_run_process
except ImportError:
    _joblib_run_process = None


class SmartCachingConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('use_smart_caching', Bool(
            False,
            output=False,
            desc='Use smart-caching during the execution'))
        self.study_config = study_config
        self.study_config.on_trait_change(self._use_smart_caching_changed, 'use_smart_caching')
    
    
    def _use_smart_caching_changed(self, old_trait_value, new_trait_value):
        """ Event to setup the apropriate caller.
        """
        # Try to set the smart caching caller
        if new_trait_value:

            # If the smart caching caller is not defined defined, raise
            # an Exception
            if _joblib_run_process is None:
                raise Exception("The smart cahing caller is not defined, "
                                "please investigate.")
            self.study_config._caller = _joblib_run_process

        # Set the standard caller
        else:
            self.study_config._caller = _run_process
