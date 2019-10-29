'''
Process execution cache configuration module

Classes
=======
:class:`SmartCachingConfig`
---------------------------
'''

from traits.api import Bool, Undefined
from capsul.study_config.study_config import StudyConfigModule


class SmartCachingConfig(StudyConfigModule):
    '''
    '''
    def __init__(self, study_config, configuration):
        super(SmartCachingConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_smart_caching', Bool(
            False,
            output=False,
            desc='Use smart-caching during the execution'))
        self.study_config = study_config
        # self.study_config.on_trait_change(self._use_smart_caching_changed, 'use_smart_caching')
