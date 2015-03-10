#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging

# Define the logger
logger = logging.getLogger(__name__)

# Caspul import
from process import Process
from nipype_process import nipype_factory
from capsul.utils import load_objects

# Nipype import
try:
    from nipype.interfaces.base import Interface
# If nipype is not found create a dummy Interface class
except ImportError:
    Interface = type("Interface", (object, ), {})


def get_process_instance(process_or_id, **kwargs):
    """ Return a Process instance given an Process identifier.

    The identifier is a derived Process class, a derived Process class
    instance or a Nipype interface instance.
    It can also be the string description of this class:
    `<module>.<class>` e.g. `caps.pipeline.spm_preproc.PreprocClass`

    Default values of the instance are passed as additional parameters.

    .. note:

        If the function 'process_or_id' parameter is not valid a
        ValueError error is raised.

    Parameters
    ----------
    process_or_id: instance or class description (mandatory)
        a process/nipype interface instance or its string description.
    kwargs:
        default values of the process instance.

    Returns
    -------
    result: instance
        an initialized process instance.
    """
    # If the function 'process_or_id' parameter is already a Process
    # instance.
    if isinstance(process_or_id, Process):
        result = process_or_id

    # If the function 'process_or_id' parameter is already a Nipye
    # interface instance, wrap this structure in a Process class
    elif isinstance(process_or_id, Interface):
        result = nipype_factory(process_or_id)

    # If the function 'process_or_id' parameter is a class string
    # description
    elif isinstance(process_or_id, basestring):

        # Get the class and module names from the class string description
        id_list = process_or_id.split(".")
        module_name = ".".join(id_list[:-1])
        object_name = id_list[-1]

        # Try to load the class
        module_objects = load_objects(
            module_name, object_name,
            allowed_instances=[Process, Interface])

        # Expect only one Process
        if len(module_objects) != 1:
            raise ImportError(
                "Found {0} processes declared "
                "in {1} when looking for {2} class".format(
                    len(module_objects), module_name, object_name))

        # Get the target Process
        process_class = module_objects[0]

        # Get the process class instance
        result = process_class()

        # If we have a Nipype interface, wrap this structure in a Process
        # class
        if isinstance(result, Interface):
            result = nipype_factory(result)

    # If the function 'process_or_id' parameter is a Process
    # class.
    elif isinstance(process_or_id, type) and issubclass(process_or_id, Process):
        result = process_or_id()
        
    else:
        raise ValueError("Invalid process_or_id argument. "
                         "Got '{0}' and expect a Process instance/string "
                         "description or an Interface instance/string "
                         "description".format(process_or_id))

    # Set the instance default parameters
    for name, value in kwargs.iteritems():
        result.set_parameter(name, value)

    return result
