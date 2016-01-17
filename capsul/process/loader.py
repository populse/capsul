##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import sys
import os.path as osp
import importlib
import types
import re

# Caspul import
from capsul.process.process import Process
from capsul.process.nipype_process import nipype_factory
from capsul.process.xml import create_xml_process
from capsul.pipeline.xml import create_xml_pipeline

# Nipype import
try:
    from nipype.interfaces.base import Interface
# If nipype is not found create a dummy Interface class
except ImportError:
    Interface = type("Interface", (object, ), {})


process_xml_re = re.compile(r'<process>.*</process>', re.DOTALL)

def get_process_instance(process_or_id, **kwargs):
    """ Return a Process instance given an identifier.

    The identifier is either:

        * a derived Process class.
        * a derived Process class instance.
        * a Nipype Interface instance.
        * a Nipype Interface class.
        * a string description of the class `<module>.<class>`.
        * a string description of a function to warp `<module>.<function>`.
        * a string description of a pipeline `<module>.<fname>.xml`.

    Default values of the process instance are passed as additional parameters.

    .. note:

        If no process is found an ImportError is raised.

    .. note:

        If the 'process_or_id' parameter is not valid a ValueError is raised.

    .. note:

        If the function to warp does not contain a process description in its
        docstring ('<process>...</process>') a ValueError is raised.

    Parameters
    ----------
    process_or_id: instance or class description (mandatory)
        a process/nipype interface instance/class or a string description.
    kwargs:
        default values of the process instance parameters.

    Returns
    -------
    result: Process
        an initialized process instance.
    """
    result = None
    # If the function 'process_or_id' parameter is already a Process
    # instance.
    if isinstance(process_or_id, Process):
        result = process_or_id

    # If the function 'process_or_id' parameter is a Process class.
    elif (isinstance(process_or_id, type) and
          issubclass(process_or_id, Process)):
        result = process_or_id()

    # If the function 'process_or_id' parameter is already a Nipye
    # interface instance, wrap this structure in a Process class
    elif isinstance(process_or_id, Interface):
        result = nipype_factory(process_or_id)

    # If the function 'process_or_id' parameter is an Interface class.
    elif (isinstance(process_or_id, type) and
          issubclass(process_or_id, Interface)):
        result = nipype_factory(process_or_id())

    # If the function 'process_or_id' parameter is a class string
    # description
    elif isinstance(process_or_id, basestring):
        module_name, object_name = process_or_id.rsplit('.', 1)
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError('Cannot import %s: %s' % (module_name, str(e)))
        module = sys.modules[module_name]
        module_object = getattr(module, object_name, None)
        if module_object is None:
            xml_file = osp.join(osp.dirname(module.__file__), object_name + '.xml')
            if osp.exists(xml_file):
                result = create_xml_pipeline(module_name, object_name, xml_file)()
            ## Go through all the module items
            #for item_name in dir(module):
                ## Do not consider private items
                #if item_name.startswith("_"):
                    #continue
                #item = getattr(module, item_name)
                #selected = None
                #for possible_class in (Process, Interface):
                    #if isinstance(item, type) and item is not possible_class:
                        #if selected is None:
                            #selected = item
                        #else:
                            #raise ValueError('More than one %s defined in %s' % (possible_class.__name__, module_name)
                ## If the current tool is a subclass of one allowed instances,
                ## add this object to the final list.
                #for check_instance in allowed_instances:
                    #if issubclass(tool, check_instance):
                        #tools.append(tool)
                        #break
        else:
            if isinstance(module_object, Process):
                result = module_object()
            elif isinstance(module_object, Interface):
                # If we have a Nipype interface, wrap this structure in a Process
                # class
                result = nipype_factory(result)
            elif isinstance(module_object, types.FunctionType):
                # Check docstring
                match = process_xml_re.search(module_object.__doc__)
                if match:
                    xml = match.group(0)
                    result = create_xml_process(module_name, object_name, module_object, xml)()

    if result is None:
        raise ValueError("Invalid process_or_id argument. "
                         "Got '{0}' and expect a Process instance/string "
                         "description or an Interface instance/string "
                         "description".format(process_or_id))

    # Set the instance default parameters
    for name, value in kwargs.iteritems():
        result.set_parameter(name, value)

    return result
