##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool

class SomaWorkflowConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma woklow for the execution'))
