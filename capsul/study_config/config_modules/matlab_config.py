##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from soma.undefined import undefined
from traits.api import File

class MatlabConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('matlab_exec', File(
            undefined,
            output=False,
            desc='Matlab command path',
            exists=True))
