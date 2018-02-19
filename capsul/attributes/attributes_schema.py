from __future__ import print_function

import six
from importlib import import_module
from pkgutil import iter_modules
from soma.sorted_dictionary import OrderedDict

from soma.controller import Controller
from soma.functiontools import partial, SomaPartial

    
class AttributesSchema(object):
    
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
                if hasattr(self._process, 'id'):
                    process_name = self._process.id
                else:
                    process_name = self._process.name
                attributes = {
                    'generated_by_process': process_name,
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
