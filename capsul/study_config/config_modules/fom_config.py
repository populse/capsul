##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str

class FomConfig(object):
    def __init__(self, study_config):
        study_config.add_trait('use_fom', Bool(
            False,
            output=False,
            desc='Use File Organization Models for file parameters completion'))
        study_config.add_trait('input_fom', Str(False, output=False,
            desc='input FOM'))
        study_config.add_trait('output_fom', Str(False, output=False,
            desc='output FOM'))
