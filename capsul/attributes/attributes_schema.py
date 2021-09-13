# -*- coding: utf-8 -*-
''' A schema defines attrinbutes used within a completion framework

Classes
=======
:class:`AttributesSchema`
-------------------------
:class:`EditableAttributes`
---------------------------
:class:`ProcessAttributes`
--------------------------

Functions
=========
:func:`set_attribute`
---------------------
'''

from __future__ import print_function

from __future__ import absolute_import
import six
from importlib import import_module
from pkgutil import iter_modules
from soma.sorted_dictionary import OrderedDict
from soma.controller import Controller
from soma.functiontools import partial, SomaPartial
import traits.api as traits
from capsul.pipeline.pipeline_nodes import ProcessNode


class AttributesSchema(object):
    '''
    An AttributesSchema has a name, which is used as an identifier to specify completion.
    '''

    # Name of the schema. Must be defined in subclasses.
    schema_name = None

    def __init__(self):
        # Instantiate EditableAttributes classes that are defined in schema
        sets = dict((k, getattr(self.__class__, k)()) for k in 
                    dir(self.__class__)
                    if isinstance(getattr(self.__class__, k), type) and 
                       issubclass(getattr(self.__class__, k), EditableAttributes))
        self.attribute_sets = sets


class EditableAttributes(Controller):
    ''' A set of attributes (group) used to define process parameters
    attributes. Attributes are traits in the EditableAttributes Controller.
    '''
    def __str__(self):
        return '<{0}({1})>'.format(self.__class__.__name__, None)



def set_attribute(object, name, value):
    '''
    
    '''
    setattr(object, name, value)

class ProcessAttributes(Controller):
    '''
    This is the base class for managing attributes for a process.

    It stores attributes associated with a Process, for each of its parameters.
    Attribute values can be accessed "globally" (for the whole process) as
    ProcessAttributes instance traits.
    Or each parameter attributes set may be accessed individually, using
    :meth:`get_parameters_attributes()`.

    To define attributes for a process, the programmer may subclass
    ProcessAttributes and define some EditableAttributes in it. Each
    EditableAttributes is a group of attributes (traits in the EditableAttributes instance or subclass).

    A ProcessAttributes subclass should be registered to a factory to be linked
    to a process name, using the `factory_id` class variable.

    See Capsul :ref:`advanced usage doc <completion>` for details.
    '''
    
    def __init__(self, process, schema_dict):
        super(ProcessAttributes, self).__init__()
        self._process = process
        self._schema_dict = schema_dict
        self.editable_attributes = OrderedDict()
        self.parameter_attributes = {}

    def __getinitargs__(self):
        # needed for self.copy()
        return (self._process, self._schema_dict)

    def set_parameter_attributes(self, parameter, schema, editable_attributes,
                                 fixed_attibute_values, allow_list=True):
        '''
        Set attributes associated with a single process parameter.

        Parameters
        ----------
        parameter: str
            process parameter name
        schema: str
            schema used for it (input, output, shared)
        editable_attributes: str, EditableAttributes instance, or list of them
            EditableAttributes or id containing attributes traits
        fixed_attibute_values: dict (str/str)
            values of non-editable attributes
        allow_list: bool
            if True (the default), it the process parameter is a list, then
            attributes are transformed into lists.
        '''
        if parameter in self.parameter_attributes:
            if schema == 'link':
                return  # this is just a lower priority
            raise KeyError('Attributes already set for parameter %s'
                           % parameter)
        process = self._process
        if isinstance(process, ProcessNode):
            process = process.process
        if parameter not in process._instance_traits():
            print('WARNING: parameter', parameter,
                  'not in process', process.name)
            return
        if isinstance(editable_attributes, six.string_types) \
                or isinstance(editable_attributes, EditableAttributes):
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
                raise TypeError(
                    'Invalid value for editable attributes: {0}'.format(ea))
            parameter_editable_attributes.append(ea)
            if add_editable_attributes:
                is_list = allow_list \
                        and isinstance(process.trait(parameter).trait_type,
                                       traits.List)
                for name in list(ea.user_traits().keys()):
                    # don't use items() since traits may change during iter.
                    trait = ea.trait(name)
                    if is_list:
                        trait = traits.List(trait)
                        ea.remove_trait(name)
                        ea.add_trait(name, trait)
                    if name in self.user_traits():
                        if not is_list \
                                and isinstance(self.trait(name).trait_type,
                                               traits.List):
                            # a process attribute trait may have been changed
                            # into a list. Here we assume attributes are only
                            # strings (at this point - it can be changed at
                            # higher lever afterwards), so change it back into
                            # a single value trait.
                            self.remove_trait(name)
                            self.add_trait(name, trait)
                        # else don't add it again: this way non-list versions
                        # of attributes get priority. If both exist, lists
                        # should get one single value (otherwise there is an
                        # ambiguity or inconsistency), so the attribute should
                        # not be a list.
                    else:
                        self.add_trait(name, trait)
                    f = SomaPartial(set_attribute, ea)
                    self.on_trait_change(f, name)
        self.parameter_attributes[parameter] = (parameter_editable_attributes,
                                                fixed_attibute_values)

    def get_parameters_attributes(self):
        ''' Get attributes for each process parameter
        '''
        pa = {}
        process = self._process
        if isinstance(process, ProcessNode):
            process = process.process
        for parameter, trait in six.iteritems(process.user_traits()):
            if trait.output:
                if hasattr(process, 'id'):
                    process_name = process.id
                else:
                    process_name = process.name
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

    def copy(self, with_values=True):
        ''' overloads :meth:`soma.Controller.copy`
        '''
        other = self.__class__(self._process, self._schema_dict)
        ea_map = {}
        for parameter, pa in six.iteritems(self.parameter_attributes):
            if parameter not in other.parameter_attributes:
                # otherwise assume this has been done in a subclass constructor
                eas, fa = pa
                oeas = []
                for ea in eas:
                    oea = ea_map.get(ea)
                    if oea is None:
                        oea = ea.copy()
                    oeas.append(oea)
                other.set_parameter_attributes(parameter, '', oeas, fa,
                                               allow_list=False)
        # copy the values
        if with_values:
            for name in self.user_traits():
                #print('copy attribs:', self, name, getattr(self, name))
                #print('   to:', other.trait(name).trait_type)
                #if isinstance(other.trait(name).trait_type, traits.List):
                    #print('    ', other.trait(name).inner_traits[0].trait_type)
                #if isinstance(self.trait(name).trait_type, traits.List):
                    #print('    self list:', self.trait(name).inner_traits[0].trait_type)
                setattr(other, name, getattr(self, name))

        return other

    def copy_to_single(self, with_values=True):
        ''' Similar to :meth:`copy`, excepts that it converts list attributes
        into single values. This is useful within the completion system
        infrastructure, to get from an attributes set containing lists
        (process parameters which are lists), a single value allowing to
        determine a single path.

        This method is merely useful to the end user.
        '''
        other = ProcessAttributes(self._process, self._schema_dict)

        ea_map = {}
        for parameter, pa in six.iteritems(self.parameter_attributes):
            if parameter not in other.parameter_attributes:
                # otherwise assume this has been done in a subclass constructor
                eas, fa = pa
                oeas = []
                for ea in eas:
                    oea = ea_map.get(ea)
                    if oea is None:
                        oea = EditableAttributes()
                        for name, trait in six.iteritems(ea.user_traits()):
                            if isinstance(trait.trait_type, traits.List):
                                trait = trait.inner_traits[0]
                            oea.add_trait(name, trait)
                        ea_map[ea] = oea
                    oeas.append(oea)
                other.set_parameter_attributes(parameter, '', oeas, fa,
                                               allow_list=False)
        # copy the values
        if with_values:
            for name in self.user_traits():
                value = getattr(self, name)
                if isinstance(value, list):
                    if len(value) != 0:
                        value = value[0]
                    else:
                        value = self.trait(name).inner_traits[0].default
                if value is not None:
                    setattr(other, name, value)
        return other
