##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Undefined
from capsul.study_config.study_config import StudyConfigModule


class SmartCachingConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(SmartCachingConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_smart_caching', Bool(
            False,
            output=False,
            desc='Use smart-caching during the execution'))
        self.study_config = study_config
        # self.study_config.on_trait_change(self._use_smart_caching_changed, 'use_smart_caching')
