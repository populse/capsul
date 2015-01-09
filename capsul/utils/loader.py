#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import string
import sys
import logging

# Define the logger
logger = logging.getLogger(__name__)


def load_objects(module_name, object_name=None, allowed_instances=None):
    """ Load a python object from a a module.

    If 'object_name' is None, the function will import the full module
    content.
    It is possible to filter objects and to keep only objects of specific
    types by setting the 'allowed_instances' parameter.
    By default only class are returned.

    Parameters
    ----------
    module_name: str (mandatory)
        the module name, ie. module1.module2
    object_name: str (optional, default None)
        the specific tool name we want to load from the module.
    allowed_instances : list (optional, default None)
        the list of allowed instances that will be returned by the function.

    Returns
    -------
    tools: list
        a list of objects.
    """
    # Remove special characters from the module name and object name
    module_name = cleanup(module_name)
    if object_name:
        object_name = cleanup(object_name)

    # Import the module
    __import__(module_name)
    module = sys.modules[module_name]

    # Get the target (possibly allowed) tool(s)
    tools = []

    # If a specific object is required, load only this object
    if object_name:
        try:
            insert_tool(tools, getattr(module, object_name),
                        allowed_instances)
        except ImportError, e:
            raise Exception(
                "Could not import {0}: {1}".format(object_name, e))

    # Otherwise, return all the module public objects
    else:

        # Go through all the module items
        for tool_name in dir(module):

            # Do not consider private items
            if tool_name.startswith("_"):
                continue

            # Load the module object
            try:
                insert_tool(tools, getattr(module, tool_name),
                            allowed_instances)
            except ImportError, e:
                raise Exception(
                    "Could not import {0}: {1}".format(tool_name, e))

    return tools


def cleanup(attribute):
    """ Cleanup a string.

    This step may avoid:
        * Windows reserved characters
        * tab, newline and null character

    Parameters
    ----------
    attribute: str (mandatory)
        the input string to cleanup.

    Returns
    -------
    out: str
        the cleaned input string.
    """
    cleanup_table = string.maketrans('(){} \t\r\n\0', '         ')

    attribute = str(attribute).translate(cleanup_table)
    attribute = attribute.replace(" ", "")

    return attribute


def insert_tool(tools, tool, allowed_instances=None):
    """ Function to add a tool to list of tools if the tool is a subclass
    of one item in allowed_instances.

    By default only class are returned.

    Parameters
    ----------
    tools: list of instance (mandatory)
        the list that contains all the allowed instances.
    tool: instance (mandatory)
        a new instance to treat: add this objects to the final list
        if its type is allowed.
    allowed_instances: list of instances (optional, default None)
        the list of allowed instances that will be added to the final list.
    """
    # Set up the default behaviour: only class are returned.
    allowed_instances = allowed_instances or [object, ]

    # Tool must not have the exact type of the allowed_instances types
    # otherwise it will always be inserted since the base classes are
    # always imported before being subclassed in a module)
    if isinstance(tool, type) and tool not in allowed_instances:

        # If the current tool is a subclass of one allowed instances,
        # add this object to the final list.
        for check_instance in allowed_instances:
            if issubclass(tool, check_instance):
                tools.append(tool)
                break
