# -*- coding: utf-8 -*-
'''
Attributes factory module

Classes
=======
:class:`AttributesFactory`
--------------------------
'''

from __future__ import print_function
from __future__ import absolute_import

from soma.factory import ClassFactory

from capsul.attributes.attributes_schema import AttributesSchema


class AttributesFactory(ClassFactory):
    ''' AttributesFactory holds an attributes schema
    '''
    class_types = {
        'schema': AttributesSchema,
    }
