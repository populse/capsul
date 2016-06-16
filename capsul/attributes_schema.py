##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
import six
from importlib import import_module
from pkgutil import iter_modules
from collections import OrderedDict

from soma.controller import Controller
from soma.functiontools import partial, SomaPartial

class AttributesSchemaValidation(type):
    '''
    Attributes schema are created in user code by defining classes. This
    meta class of AttributesSchema is used to check that the definition
    is correct and to raise an explicit error if not.
    '''
    
    def __init__(cls, name, base, dict):
        '''
        Do the following verification on the newly declared class and
        raise an exception if required:
        
        - schema_name is defined in the class
        '''
        super(AttributesSchemaValidation, cls).__init__(name, base, dict)
        if name == 'AttributesSchema':
            return
        if cls.schema_name is None:
            raise ValueError('AttributesSchema subclasses must define schema_name')

    
class AttributesSchema(object):
    __metaclass__ = AttributesSchemaValidation
    
    # Name of the schema. Must be defined in subclasses.
    schema_name = None

    def __init__(self):
        # Instanciate EditableAttributes classes that are defined in schema
        sets = dict((k, getattr(self.__class__, k)()) for k in 
                    dir(self.__class__)
                    if isinstance(getattr(self.__class__, k), type) and 
                       issubclass(getattr(self.__class__, k), EditableAttributes))
        self.attribute_sets = sets


class EditableAttributes(Controller):
    def __str__(self):
        return '<{0}({1})>'.format(self.__class__.__name__, None)


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


class AttributesSchemaFactory(object):
    '''
    This is the main entry point for finding and creating an attribute
    schema given its name and based to a serching path composed of Python
    module names.
    
    TODO: It is not clear yet if there will be a single instance of this
    class for an application or for each StudyConfig instance. It will depend
    on how its configuration (i.e. module_path) is managed.
    '''
    
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
            attribute_schema_class = self.find_attributes_schema(schema_name)
            if attribute_schema_class is not None:
                attribute_schema = attribute_schema_class()
                self.attribute_schemas[schema_name] = attribute_schema
        return attribute_schema

def set_attribute(object, name, value):
    '''
    
    '''
    setattr(object, name, value)

class ProcessAttributes(Controller):
    '''
    This is the base class for managing attributes for a process.
    '''
    
    def __init__(self, process, schema_dict):
        super(ProcessAttributes, self).__init__()
        self._process = process
        self._schema_dict = schema_dict
        self.editable_attributes = OrderedDict()
        self.parameter_attributes = {}

    
    def set_parameter_attributes(self, parameter, schema, editable_attributes, fixed_attibute_values):
        if parameter in self.parameter_attributes:
            raise KeyError('Attributes already set for parameter %s' % parameter)
        if isinstance(editable_attributes, six.string_types) or isinstance(editable_attributes, EditableAttributes):
            editable_attributes = [editable_attributes]
        parameter_editable_attributes = []
        for ea in editable_attributes:
            add_editable_attributes = False
            if isinstance(ea, six.string_types):
                key = ea
                ea = self.editable_attributes.get(key)
                if ea is None:
                    ea = getattr(self._schema_dict[schema], key)()
                    self.editable_attributes[key] = ea
                    add_editable_attributes = True
            elif isinstance(ea, EditableAttributes):
                key = ea
                if key not in self.editable_attributes:
                    self.editable_attributes[key] = ea
                    add_editable_attributes = True
            else:
                raise TypeError('Invalid value for editable attributes: {0}'.format(ea))
            parameter_editable_attributes.append(ea)
            if add_editable_attributes:
                for name, trait in six.iteritems(ea.user_traits()):
                    self.add_trait(name, trait)
                    f = SomaPartial(set_attribute, ea)
                    self.on_trait_change(f, name)
        self.parameter_attributes[parameter] = (parameter_editable_attributes, fixed_attibute_values)

    def get_parameters_attributes(self):
        pa = {}
        for parameter, trait in six.iteritems(self._process.user_traits()):
            if trait.output:
                attributes = {
                    'generated_by_process': self._process.id,
                    'generated_by_parameter': parameter}
            else:
                attributes = {}
            editable_fixed = self.parameter_attributes.get(parameter, ([], {}))
            editable_attributes, fixed_attibute_values = editable_fixed
            for ea in editable_attributes:
                for attribute in ea.user_traits():
                    value = getattr(ea, attribute)
                    attributes[attribute] = value
            attributes.update(fixed_attibute_values)
            if attributes:
                pa[parameter] = attributes
        return pa
