# -*- coding: utf-8 -*-
'''
Read and write a Process as an XML file.

Classes
=======
:class:`XMLProcess`
-------------------

Functions
=========
:func:`string_to_value`
-----------------------
:func:`trait_from_xml`
----------------------
:func:`create_xml_process`
--------------------------

Decorator
=========
:func:`xml_process`
-------------------
'''

from __future__ import absolute_import

import sys
import xml.etree.cElementTree as ET
from ast import literal_eval

from capsul.process.process import Process

from soma.utils.functiontools import getArgumentsSpecification

from traits.api import (Int, Float, String, Unicode, File, Directory, Enum,
                        Bool, List, Any, Undefined)
from six.moves import range

if sys.version_info[0] >= 3:
    xrange = range

_known_values = {
    'Undefined': Undefined,
    'None': Undefined
}
    
def string_to_value(string):
    """ Converts a string into a Python value without executing code.
    """
    value = _known_values.get(string)
    if value is None:
        try:
            value = literal_eval(string)
        except ValueError as e:
            raise ValueError('%s: %s' % (str(e), repr(string)))
    return value

class XMLProcess(Process):
    """ Base class of all generated classes for processes defined as a Python
    function decorated with an XML string.
    """    
    def _run_process(self):
        """ Execute the XMLProcess. Runs the function and check its result
        to set the output attributes values accordingly.
        """
        # Build function parameters with identified input attributes
        kwargs = dict((i, getattr(self, i)) for i in self._function_inputs)
        # Calls the function and get the result
        result = self._function(**kwargs)
        if self._function_return:
            # Process was declared to return a single value
            setattr(self, self._function_return, result)
        elif self._function_outputs:
            # Process was declared to return several output values
            if isinstance(result, (list, tuple)):
                # Return value is a list, maps the output parameter names in
                # their declaration order
                if len(result) > len(self._function_outputs):
                    raise ValueError('Too many values (%d instead of %d) '
                                     'returned by process %s' % 
                                     (len(result), len(self._function_outputs),
                                      self.id))
                for i in range(len(self._function_outputs)):
                    setattr(self, self._function_outputs[i], result[i])
            elif isinstance(result, dict):
                # Return value is a dict, set the output parameter values.
                for i in self._function_outputs:
                    setattr(self, i, result[i])
            else:
                raise ValueError('Value returned by process %s must be a list,'
                                 ' tuple or dict' % self.id)

string_to_trait = {
    'int': (Int, {}),
    'float': (Float, {}),
    'string': (String, {}),
    'unicode': (Unicode, {}),
    'bool': (Bool, {}),
    'file': (File, {}),
    'directory': (Directory, {}),
    'any': (Any, {}),
    'list_int': (List, {'trait': Int}),
    'list_float': (List, {'trait': Float}),
    'list_string': (List, {'trait': String}),
    'list_unicode': (List, {'trait': Unicode}),
    'list_bool': (List, {'trait': Bool}),
    'list_file': (List, {'trait': File}),
    'list_directory': (List, {'trait': Directory}),
    'list_any': (List, {'trait': Any}),
}
def trait_from_xml(element, order=None):
    """ Creates a trait from an XML element type (<input>, <output> or
    <return>).
    """
    type = element.get('type')
    trait_args = ()
    t = string_to_trait.get(type)
    if t:
        trait_class, trait_kwargs = t
    elif type == 'enum':
        trait_class = Enum
        trait_args = string_to_value(element.get('values'))
        trait_kwargs = {}
    else:
        raise ValueError('Invalid parameter type: %s' % type)
    trait_kwargs = trait_kwargs.copy()
    trait_kwargs['output'] = (element.tag != 'input')
    doc = element.get('doc')
    if doc:
        trait_kwargs['desc'] = doc
    optional = element.get('optional')
    if optional is not None:
        trait_kwargs['optional'] = bool(optional == 'true')
    allowed_ext = element.get('allowed_extensions')
    if allowed_ext is not None:
        trait_kwargs['allowed_extensions'] = eval(allowed_ext)
    if type in ('file', 'list_file'):
        input_filename = element.get('input_filename')
        if input_filename is not None:
            trait_kwargs['input_filename'] = input_filename
        else:
            trait_kwargs['input_filename'] = False
    if order is not None:
        trait_kwargs['order'] = order
    return trait_class(*trait_args, **trait_kwargs)

def create_xml_process(module, name, function, xml):
    """
    Create a new process class given a Python function and a string containing
    the corresponding Capsul XML 2.0 definition.

    Parameters
    ----------
    module: str (mandatory)
        name of the module for the created Process class (the Python module is
        not modified).
    name: str (mandatory)
        name of the new process class
    function: callable (mandatory)
        function to call to execute the process.
    xml: str (mandatory)
        XML definition of the function.

    Returns
    -------
    results:  XMLProcess subclass
        created process class.
    """
    xml_process = ET.fromstring(xml)
    
    class_kwargs = {
        "__module__": module,
    }
    if function.__doc__:
        class_kwargs['__doc__'] = function.__doc__
    
    args, varargs, varkw, defaults = getArgumentsSpecification(function)
    if defaults:
        default_values = dict((args[-1-i], defaults[-1-i]) for i in range(len(defaults)))
    else:
        default_values = {}
    class_kwargs['default_values'] = default_values
    version = xml_process.get('capsul_xml')
    if version and version != '2.0':
        raise ValueError('Only Capsul XML 2.0 is supported, not %s' % version)
    
    role = xml_process.get('role')
    if role:
        class_kwargs['role'] = role
    
    function_inputs = []
    function_outputs = []
    function_return = None
    trait_count = 0 # used to order traits in class
    for child in xml_process:
        if child.tag in ('input', 'output'):
            n = child.get('name')
            trait = trait_from_xml(child, trait_count)
            trait_count += 1
            class_kwargs[n] = trait
            if trait.output and trait.input_filename is False:
                function_outputs.append(n)
            else:
                function_inputs.append(n)
        elif child.tag == 'return':
            n = child.get('name')
            if n:
                trait = trait_from_xml(child, trait_count)
                trait_count += 1
                class_kwargs[n] = trait
                function_return = n
            else:
                for parameter in child:
                    n = parameter.get('name')
                    trait = trait_from_xml(parameter, trait_count)
                    trait_count += 1
                    class_kwargs[n] = trait
                    function_outputs.append(n)
        else:
            raise ValueError('Invalid tag in <process>: %s' % child.tag)
    class_kwargs['_function'] = staticmethod(function)
    class_kwargs['_function_inputs'] = function_inputs
    class_kwargs['_function_outputs'] = function_outputs
    class_kwargs['_function_return'] = function_return
    
    # Get the process instance associated to the function
    process_class = type(str(name), (XMLProcess, ), class_kwargs)
    return process_class


def xml_process(xml):
    """ Decorator used to associate a Python function to its Process XML
    representation.    
    """
    def set_capsul_xml(function):
        function.capsul_xml = xml
        return function
    return set_capsul_xml
