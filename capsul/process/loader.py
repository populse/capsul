#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from process import Process, NipypeProcess
from nipype_process import nipype_factory
import warnings

try:
    from nipype.interfaces.base import Interface
except ImportError:
    warnings.warn("Nipype not installed: the process mdodule may not work"
                  "properly,please investigate")
    Interface = type("Interface", (object, ), {})
    
from capsul.utils import load_objects


def get_process_instance(process_or_id, **kwargs):
    """ Return an instance of Process given its identifier.
    The identifier is a string identifying a class derived from Process
    or Nipype Interface.
    It must contain one of the following value:

    * Case 1:
      The name of a Python module containing a single declaration of class
      derived from Process. e.g 'morphologist.process.morphologist'
    * Case 2:
      '<module>.<class>' where <module> is the name of a Python module and
      <class> is the name of a Process derived class defined in this
      module. e.g. 'soma.pipeline.sandbox.SPMNormalization'

    Default values of the instance are passed as additional parameters.

    Parameters
    ----------
    process_or_id: str or instance (mandatory)
        a class interface or a string formatting accordingly to case 1
        and 2.
    **kwargs: default values of the process instance.

    Returns
    -------
    result: instance
        a process or interface instance.
    """
    if isinstance(process_or_id, Process):
        # Is already a Process instance.
        result = process_or_id
    elif isinstance(process_or_id, Interface):
        # Need to convert the nipype interface
        result = nipype_factory(process_or_id)
        result.auto_nipype_process_qc()
    elif isinstance(process_or_id, str):
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

        # expect only one Process
        module_objects = module_objects or []
        if len(module_objects) != 1:
            raise ImportError('Found {0} processes declared '
                              'in {1}'.format(len(module_objects),
                               process_or_id))
        # Get the target Process
        process_class = module_objects[0]

        # Get the process class instance
        result = process_class()

        do_nipype_qc = False
        if isinstance(result, Interface):
            # Need to convert the nipype interface
            result = nipype_factory(result)
            do_nipype_qc = True

        # Set instance default parameters
        for name, value in kwargs.iteritems():
            result.set_parameter(name, value)

#        if do_nipype_qc:
#            # Try to run automatic QC
#            result.auto_nipype_process_qc()
    else:
        raise ValueError('Invalid process_or_id argument.'
                         'Got {0} and expect a Process instance/string'
                         'description or an Interface instance/string'
                         'description'.format(process_or_id))

    return result
