##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
from traits.api import Directory, Undefined
try:
    from brainvisa_share import config as bv_share_config
except ImportError:
    bv_share_config = None
from soma import config as soma_config
from capsul.study_config.study_config import StudyConfigModule


class BrainVISAConfig(StudyConfigModule):
    def __init__(self, study_config, configuration):
        super(BrainVISAConfig, self).__init__(study_config, configuration)
        study_config.add_trait('shared_directory',Directory(
            Undefined,
            output=False,
            desc='Study shared directory'))

        if bv_share_config is not None:
            # take 2 fist digits in version
            bv_share_version = '.'.join(bv_share_config.version.split('.')[:2])
        else:
            # brainvisa_share.config cannot be imported: sounds bad, but
            # fallback to soma.config version (which may be different)
            bv_share_version = soma_config.short_version
        study_config.shared_directory = os.path.join(
            soma_config.BRAINVISA_SHARE, 'brainvisa-share-%s' \
                % bv_share_version)
