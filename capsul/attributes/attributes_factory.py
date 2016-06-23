##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function
from __future__ import absolute_import

from soma.factory import ClassFactory

from capsul.attributes.attributes_schema import AttributesSchema


class AttributesFactory(ClassFactory):
    class_types = {
        'schema': AttributesSchema,
    }
