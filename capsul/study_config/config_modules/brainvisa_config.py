##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_

Classes
=======
:class:`BrainVISAConfig`
------------------------
'''

import os
from traits.api import Directory, Undefined
from soma import config as soma_config
from capsul.study_config.study_config import StudyConfigModule


class BrainVISAConfig(StudyConfigModule):
    '''
    Configuration module allowing to use `BrainVISA / Axon <http://brainvisa.info/axon/user_doc>`_ shared data in Capsul processes.

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

    shared_directory: str (filename)
        Study shared directory
     '''

    def __init__(self, study_config, configuration):
        super(BrainVISAConfig, self).__init__(study_config, configuration)
        study_config.add_trait('shared_directory',Directory(
            Undefined,
            output=False,
            desc='Study shared directory'))

        study_config.shared_directory = soma_config.BRAINVISA_SHARE
