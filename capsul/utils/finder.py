# -*- coding: utf-8 -*-
'''
Utilities to find processes

Functions
=========
:func:`find_processes`
----------------------
'''

from __future__ import absolute_import
import sys
import os.path as osp
import importlib
import pkgutil
import types
import re
from glob import glob

from capsul.process.process import Process


process_xml_re = re.compile(r'<process.*</process>', re.DOTALL)
pipeline_xml_re = re.compile(r'<pipeline.*</pipeline>', re.DOTALL)
pipeline_json_re = re.compile(r'{.*"definition":', re.DOTALL)

def find_processes(module_name, ignore_import_error=True):
    ''' Find processes in a module and iterate over them
    '''
    importlib.import_module(module_name)
    module = sys.modules[module_name]
    module_names  = [module_name]
    for i, m, p in pkgutil.walk_packages(module.__path__, 
                                         prefix='%s.' % module_name):
        module_names.append(m)

    # avoid loading nipype if not needed, since it takes time
    nipype_loaded = False
    Interface = None

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
            if not nipype_loaded:
                nipype = sys.modules.get('nipype.interfaces.base')
                if nipype is not None:
                    Interface = getattr(nipype, 'Interface')
                    nipype_loaded = True
                elif Interface is None:
                    # If nipype is not found create a dummy Interface class
                    Interface = type("Interface", (object, ), {})
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
        for f in glob(osp.join(module_dir, '*.json')):
            json = open(osp.join(module_dir, f)).read()
            if pipeline_json_re.search(json):
                yield '%s.%s' % (module_name, osp.basename(f)[:-4])
