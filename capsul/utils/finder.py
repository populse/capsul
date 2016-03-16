##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import sys
import os.path as osp
import importlib
import pkgutil
import types
import re
from glob import glob

from capsul.process.process import Process

try:
    from nipype.interfaces.base import Interface
# If nipype is not found create a dummy Interface class
except ImportError:
    Interface = type("Interface", (object, ), {})

process_xml_re = re.compile(r'<process.*</process>', re.DOTALL)
pipeline_xml_re = re.compile(r'<pipeline.*</pipeline>', re.DOTALL)

def find_processes(module_name, ignore_import_error=True):
    importlib.import_module(module_name)
    module = sys.modules[module_name]
    module_names  = [module_name]
    for i, m, p in pkgutil.walk_packages(module.__path__, 
                                         prefix='%s.' % module_name):
        module_names.append(m)
    for module_name in module_names:
        try:
            importlib.import_module(module_name)
        except ImportError:
            if not ignore_import_error:
                raise
            continue
        module = sys.modules[module_name]
        for name in dir(module):
            item = getattr(module, name)
            if (isinstance(item, type) and
                issubclass(item, Process)):
                yield '%s.%s' % (module_name, name)
            elif isinstance(item, Interface):
                # If we have a Nipype interface, wrap this structure in a Process
                # class
                yield '%s.%s' % (module_name, name)
            elif isinstance(item, types.FunctionType):
                # Check docstring
                if getattr(item, 'capsul_xml', None) or (item.__doc__ and process_xml_re.search(item.__doc__)):
                    yield '%s.%s' % (module_name, name)
        module_dir = osp.dirname(module.__file__)
        for f in glob(osp.join(module_dir, '*.xml')):
            xml = open(osp.join(module_dir, f)).read()
            if pipeline_xml_re.search(xml):
                yield '%s.%s' % (module_name, osp.basename(f)[:-4])