#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
import traceback
import os
import sys
from setuptools import find_packages
from inspect import isclass


def find_pipelines(module_name, allowed_instance="Pipeline"):
    """ Function that return all the Pipeline class of a module.

    Parameters
    ----------
    module_name: str (mandatory)
        the name of the module we want to go through in order to find all
        pipeline classes.

    Returns
    -------
    pipelines: list of str
        a list of all pipelines found in the module.
    """

    # First try to import the module
    try:
        __import__(module_name)
    except:
        logging.error("Can't load module {0}".format(module_name))
        return []

    # Get the module
    module = sys.modules[module_name]
    module_path = module.__path__[0]
    print module_path

    # Use setuptools to go through the module
    sub_modules = find_packages(where=module_path, exclude=("doc", ))
    sub_modules = [module_name + "." + x for x in sub_modules]
    sub_modules.insert(0, module_name)

    # Shift
    shift = len(module_name.split("."))

    # Set with all pipelines
    pipelines = set()
    for sub_module in sub_modules:
        # Get the sub module path
        sub_module_path = os.path.join(module_path,
                                       *sub_module.split(".")[shift:])

        # List all the mdule in sub module path
        sub_sub_module_names = [sub_module + "." + x[:-3]
                               for x in os.listdir(sub_module_path)
                               if (x.endswith(".py") and
                                   not x.startswith("_"))]

        # Try to import the sub sub module
        for sub_sub_module_name in sub_sub_module_names:
            try:
                __import__(sub_sub_module_name)
            except:
                exc_info = sys.exc_info()
                logging.error("".join(traceback.format_exception(*exc_info)))
                logging.error("Can't load module "
                              "{0}".format(sub_sub_module_name))
                continue

            # Get the module
            sub_sub_module = sys.modules[sub_sub_module_name]

            # From all the tools, find Pipeline instance
            for tool_name in dir(sub_sub_module):
                if tool_name.startswith("_"):
                    continue
                tool = getattr(sub_sub_module, tool_name)
                if (isclass(tool) and
                        tool.__mro__[1].__name__ == allowed_instance and
                        tool_name not in ["Pipeline", "ConnProcess"]):
                    pipelines.add(sub_sub_module_name + "." + tool_name)

    return list(pipelines)

