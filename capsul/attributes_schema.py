##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
from importlib import import_module
from pkgutil import iter_modules
import six

class AttributesSchema(object):
    # Name of the schema. Must be defined in subclasses.
    schema_name = None

class AttributeSet(object):
    pass


def find_classes_in_module(module_name, parent_class):
    '''
    Find all the classes derived from AttributedSchema defined in a
    Python module. If the module is a package, it also look into
    submodules.
    '''
    try:
        module = import_module(module_name)
    except ImportError:
        return
    for i in six.itervalues(module.__dict__):
        if (isinstance(i, type) and issubclass(i, parent_class)
                and i.__module__ == module.__name__):
            yield i
    path = getattr(module, '__path__', None)
    if path:
        for importer, submodule_name, ispkg in iter_modules(path):
            for j in find_classes_in_module('%s.%s' % 
                    (module.__name__, submodule_name), parent_class):
                yield j

class AttributesSchemaManager(object):
    def __init__(self):
        self.module_path = []
        self.attribute_schemas = {}
    
    def find_attributes_schema(self, schema_name):
        '''
        Find an attribute schema class by its name in all modules declared in
        self.module_path. Look for all subclasses of AttributesSchema
        declared in the modules and return the first one having
        cls.name == name. If none is found, returns None.
        '''
        for module_name in self.module_path:
            for cls in find_classes_in_module(module_name, AttributesSchema):
                if cls.schema_name == schema_name:
                    return cls
        return None
    
    def get_attributes_schema(self, schema_name):
        '''
        Returns an instance of AttributesSchema given its name.
        '''
        attribute_schema = self.attribute_schemas.get(schema_name)
        if attribute_schema is None:
            attribute_schema = self.find_attributes_schema(schema_name)
            if attribute_schema is not None:
                self.attribute_schemas[schema_name] = attribute_schema
        return attribute_schema

