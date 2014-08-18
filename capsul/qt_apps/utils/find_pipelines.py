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
import traceback
import os
import sys
from setuptools import find_packages
from inspect import isclass


def find_pipelines(module_name, url=None, allowed_instance="Pipeline"):
    """ Function that return all the Pipeline class of a module.

    All the mdoule path are scanned recuresively. Any pipeline will be added
    to the output.

    Parameters
    ----------
    module_name: str (mandatory)
        the name of the module we want to go through in order to find all
        pipeline classes.
    url: str (optional)
        the url to the module documentation

    Returns
    -------
    structured_pipelines: hierachic dict
        each key is a sub module of the module. Leafs contain a list with
        the url to the documentation.
    pipelines: list
        a list a pipeline string descriptions.
    """

    # Try to import the module
    try:
        __import__(module_name)
    except:
        logging.error("Can't load module {0}".format(module_name))
        return {}, []

    # Get the module path
    module = sys.modules[module_name]
    module_path = module.__path__[0]

    # Use setuptools to go through the module
    sub_modules = find_packages(where=module_path, exclude=("doc", ))
    sub_modules = [module_name + "." + x for x in sub_modules]
    sub_modules.insert(0, module_name)

    # Shift
    shift = len(module_name.split("."))

    # Create a set with all pipelines
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

    # Organize the pipeline string description by module names
    structured_pipelines = {}
    lists2dict([x.split(".") for x in pipelines], url, structured_pipelines)

    return structured_pipelines, list(pipelines)


def lists2dict(list_of_pipeline_description, url, d):
    """ Convert a list of splited module names to a hierachic dictionary with
    list leafs that contain the url to the module docuementation.

    Parameters
    ----------
    list_of_pipeline_description: list of list of str (mandatory)
        the splited module names to organize bu modules
    url: str (mandatory)
        the url to the module documentation

    Returns
    -------
    d: hierachic dict
        each key is a sub module of the module. Leafs contain a list with
        the url to the documentation.
    """
    # Go through all pipeline descriptions
    for l in list_of_pipeline_description:

        # Reach a leaf (a pipeline)
        if len(l) == 1:
            d.setdefault(l[0], []).append(url or "")

        # Continue the recursion
        else:
            if not l[0] in d:
                d[l[0]] = lists2dict([l[1:]], url, {})
            else:
                d[l[0]].update(lists2dict([l[1:]], url, d[l[0]]))

    return d


