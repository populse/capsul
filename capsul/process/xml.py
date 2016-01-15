##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import absolute_import

from soma.controller.trait_utils import clone_trait

from capsul.process import Process

import xml.etree.cElementTree as ET
from traits.api import Int, Float, String, Unicode, File, Directory, Enum, List

class AutoProcess(Process):
    """ Process class  generated dynamically.
    """
    def _run_process(self):
        """ Execute the AutoProcess class.
        """
        kwargs = dict((i, getattr(self, i)) for i in self._function_inputs)
        result = self._function(**kwargs)
        if self._function_return:
            setattr(self, self._function_return, result)
        elif self._function_outputs:
            if isinstance(result, (list, tuple)):
                if len(result) > len(self._function_outputs):
                    raise ValueError('Too many values (%d instead of %d) returned by process %s' % (len(result), len(self._function_outputs), self.id))
                for i in xrange(len(self._function_outputs)):
                    setattr(self, self._function_outputs[i], result[i])
            elif isinstance(result, dict):
                for i in self._function_outputs:
                    setattr(self, i, result[i])
            else:
                raise ValueError('Value returned by process %s must be a list, tuple or dict' % self.id)

string_to_trait = {
    'int': (Int, {}),
    'float': (Float, {}),
    'string': (String, {}),
    'unicode': (Unicode, {}),
    'file': (File, {}),
    'directory': (Directory, {}),
    'list_int': (List, {'trait': Int}),
    'list_float': (List, {'trait': Float}),
    'list_string': (List, {'trait': String}),
    'list_unicode': (List, {'trait': Unicode}),
    'list_file': (List, {'trait': File}),
    'list_directory': (List, {'trait': Directory}),
}
def trait_from_xml(element):
    type = element.get('type')
    trait_args = ()
    t = string_to_trait.get(type)
    if t:
        trait_class, trait_kwargs = t
    elif type == 'enum':
        trait_args = element.get('values').split(',')
    else:
        raise ValueError('Invalid parameter type: %s' % type)
    trait_kwargs = trait_kwargs.copy()
    trait_kwargs['output'] = (element.tag != 'input')
    doc = element.get('doc')
    if doc:
        trait_kwargs['desc'] = doc
    return trait_class(*trait_args, **trait_kwargs)

def create_xml_process(module, name, function, xml):
    xml_process = ET.fromstring(xml)
    
    class_kwargs = {
        '__doc__': function.__doc__,
        "__module__": module,
    }
    
    version = xml_process.get('capsul_xml')
    if version and version != '2.0':
        raise ValueError('Only Capsul XML 2.0 is supported, not %s' % version)
    
    role = xml_process.get('role')
    if role:
        class_kwargs['role'] = role
    
    function_inputs = []
    function_outputs = []
    function_return = None
    for child in xml_process:
        if child.tag in ('input', 'output'):
            name = child.get('name')
            trait = trait_from_xml(child)
            class_kwargs[name] = trait
            if trait.output and not trait.input_filename:
                function_outputs.append(name)
            else:
                function_inputs.append(name)
        elif child.tag == 'return':
            name = child.get('name')
            if name:
                trait = trait_from_xml(child)
                class_kwargs[name] = trait
                function_return = name
            else:
                for parameter in child:
                    name = parameter.get('name')
                    trait = trait_from_xml(parameter)
                    class_kwargs[name] = trait
                    function_outputs.append(name)
        else:
            raise ValueError('Invalid tag in <process>: %s' % tag)
    class_kwargs['_function'] = staticmethod(function)
    class_kwargs['_function_inputs'] = function_inputs
    class_kwargs['_function_outputs'] = function_outputs
    class_kwargs['_function_return'] = function_return
    
    # Get the process instance associated to the function
    process_class = (
        type(name, (AutoProcess, ), class_kwargs))
    return process_class
