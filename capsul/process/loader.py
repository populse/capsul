#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import warnings

# Caspul import
from process import Process
from nipype_process import nipype_factory
from capsul.utils import load_objects

# Nipype import
try:
    from nipype.interfaces.base import Interface
except ImportError:
    # warnings.warn("Nipype not installed: the process mdodule may not work"
    #               "properly,please investigate")
    Interface = type("Interface", (object, ), {})


def get_process_instance(process_or_id, **kwargs):
    """ Return a Process instance given an identifier or a class
    derived from Process.

    The identifier is a derived Process class or a Nipype Interface.
    It can also be the string description of such objects:

    * Case 1:
      the name of a Python module containing a single declaration
      of a derived Processclass e.g. `caps.pipeline.spm_preproc`
    * Case 2:
      `<module>.<class>` where <module> is the name of a Python
      module and <class> is the name of a Process derived class
      defined in this module. e.g.
      `caps.pipeline.spm_preproc.SPMNormalization`

    Default values of the instance are passed as additional parameters.

    Parameters
    ----------
    process_or_id: str, instance or class (mandatory)
        a process/nipype interface or its string description.
    kwargs:
        default values of the process instance.

    Returns
    -------
    result: instance
        an initialize process instance.
    """
    # Is already a Process instance.
    if isinstance(process_or_id, Process):
        result = process_or_id
    # Need to convert the nipype interface
    elif isinstance(process_or_id, Interface):
        result = nipype_factory(process_or_id)
        result.auto_nipype_process_qc()
    # From string description
    elif isinstance(process_or_id, basestring):
        # Try to import a module that must contain a single
        # Process derived class

        # Case 1
        try:
            module_objects = load_objects(process_or_id,
                             allowed_instances=[Process, Interface])
        except ImportError:
            module_objects = None

        # Case 2
        if module_objects is None:
            id_list = process_or_id.split(".")
            module_name = ".".join(id_list[:-1])
            object_name = id_list[-1]
            try:
                module_objects = load_objects(module_name,
                                 object_name,
                                 allowed_instances=[Process, Interface])
            except ImportError:
                module_objects = None

        # Expect only one Process
        module_objects = module_objects or []
        if len(module_objects) != 1:
            raise ImportError("Found {0} processes declared "
                              "in {1}".format(len(module_objects),
                               process_or_id))

        # Get the target Process
        process_class = module_objects[0]

        # Get the process class instance
        result = process_class()

        # Need to convert the nipype interface
        if isinstance(result, Interface):
            result = nipype_factory(result)

        # Set instance default parameters
        for name, value in kwargs.iteritems():
            result.set_parameter(name, value)

    elif isinstance(process_or_id,type) and issubclass(process_or_id, Process):
        return get_process_instance(process_or_id(), **kwargs)
    else:
        raise ValueError("Invalid process_or_id argument. "
                         "Got '{0}' and expect a Process instance/string "
                         "description or an Interface instance/string "
                         "description".format(process_or_id))

    return result
