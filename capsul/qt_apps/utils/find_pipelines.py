# -*- coding: utf-8 -*-
'''
Functions
=========
:func:`find_pipelines_from_description`
---------------------------------------
:func:`find_pipeline_and_process`
---------------------------------
:func:`lists2dict`
------------------
'''

# System import
from __future__ import absolute_import
import logging
import traceback
import os
import json
import sys
from setuptools import find_packages
from inspect import isclass

# CAPSUL import
from capsul.api import Pipeline
from capsul.api import Process

# Define the logger
logger = logging.getLogger(__name__)


def find_pipelines_from_description(module_name, url=None):
    """ Function that list all the pipeline of a module.

    Parameters
    ----------
    module_name: str (mandatory)
        the name of the module we want to go through in order to find all
        pipeline classes.
    url: str (optional)
        the url to the module documentation.

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
    except ImportError:
        logger.error("Can't load module {0}".format(module_name))
        return {}, []

    # Get the module path
    module = sys.modules[module_name]
    module_path = module.__path__[0]

    # Build the expected pipeline description file
    description_file = os.path.join(
        module_path, "{0}.capsul".format(module_name))

    # Load the description file
    if os.path.isfile(description_file):
        with open(description_file) as json_file:
            pipelines = json.load(json_file)

        # Organize the pipeline string description by module names
        structured_pipelines = {}
        lists2dict([x.split(".") for x in pipelines], url, structured_pipelines)

        return structured_pipelines, pipelines

    # No description found
    else:
        return {}, []


def find_pipeline_and_process(module_name):
    """ Function that return all the Pipeline and Process classes of a module.

    All the mdoule path are scanned recuresively. Any pipeline or process will
    be added to the output.

    Parameters
    ----------
    module_name: str (mandatory)
        the name of the module we want to go through in order to find all
        pipeline classes.

    Returns
    -------
    output: dict
        a dictionary with a list of pipeline and process string descriptions
        found in the module.
    """

    # Try to import the module
    try:
        __import__(module_name)
    except ImportError:
        logger.error("Can't load module {0}".format(module_name))
        return {}, []

    # Get the module path
    module = sys.modules[module_name]
    if hasattr(module, '__path__'):
        module_path = module.__path__[0]
    else:
        module_path = os.path.dirname(module.__file__)

    # Use setuptools to go through the module
    sub_modules = find_packages(where=module_path, exclude=("doc", ))
    sub_modules = [module_name + "." + x for x in sub_modules]
    sub_modules.insert(0, module_name)
    logger.debug("Modules found with setuptools: '{0}'.".format(sub_modules))

    # Shift
    shift = len(module_name.split("."))

    # Create a set with all pipelines and process
    pip_and_proc = [set(), set()]
    for sub_module in sub_modules:
        # Get the sub module path
        sub_module_path = os.path.join(
            module_path, *sub_module.split(".")[shift:])

        # List all the mdule in sub module path
        sub_sub_module_names = [
            sub_module + "." + x[:-3] for x in os.listdir(sub_module_path)
            if (x.endswith(".py") and not x.startswith("_"))]

        # Try to import the sub sub module
        for sub_sub_module_name in sub_sub_module_names:
            try:
                __import__(sub_sub_module_name)
            except ImportError:
                exc_info = sys.exc_info()
                logger.error("".join(traceback.format_exception(*exc_info)))
                logger.error("Can't load module "
                              "{0}".format(sub_sub_module_name))
                continue

            # Get the module
            sub_sub_module = sys.modules[sub_sub_module_name]

            # From all the tools, find Pipeline instance
            for tool_name in dir(sub_sub_module):
                if tool_name.startswith("_"):
                    continue
                tool = getattr(sub_sub_module, tool_name)
                # Check all the authorized derived class
                parent_classes = [Pipeline, Process]
                for cnt, parent_class in enumerate(parent_classes):
                    if (isclass(tool) and issubclass(tool, parent_class)) \
                            and tool not in parent_classes:
                        pip_and_proc[cnt].add(
                            sub_sub_module_name + "." + tool_name)
                        break
    # Format output
    output = {
        "pipeline_descs": list(pip_and_proc[0]),
        "process_descs": list(pip_and_proc[1])
    }

    return output


def lists2dict(list_of_pipeline_description, url, d):
    """ Convert a list of splited module names to a hierachic dictionary with
    list leafs that contain the url to the module docuementation.

    Parameters
    ----------
    list_of_pipeline_description: list of list of str (mandatory)
        the splited module names to organize by modules
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
