#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import string
import sys


def load_objects(module_name, object_name=None, allowed_instances=None):
    """ Load a python object

    The object is described by a string `module_name` and `object_name`.
    If `object_name` is None import the full module content.
    Can also filtered objects and only keep objects of
    types defined in allowed_instances.

    Parameters
    ----------
    module : str
        module name
    tool : str
        tool name
    allowed_instances : list
        list of instance to load

    Returns
    -------
    tools : list
        a list of objects.
    """
    # remove special characters
    module_name = cleanup(module_name)
    if object_name:
        object_name = cleanup(object_name)

    # import the module
    __import__(module_name)
    module = sys.modules[module_name]

    # get the target tool(s)
    tools = []
    if object_name:
        try:
            insert_tool(tools, getattr(module, object_name),
                        allowed_instances)
        except ImportError, e:
            raise Exception("Could not import {0}: {1}".format(object_name,
                                                               e))
    else:
        for tool_name in dir(module):
            if tool_name.startswith("_"):
                continue
            try:
                insert_tool(tools, getattr(module, tool_name),
                            allowed_instances)
            except ImportError, e:
                raise Exception("Could not import {0}: {1}".format(
                                tool_name, e))

    return tools


def cleanup(attribute):
    """ cleanup avoiding:
        * Windows reserved characters
        * '_' since it is reserved by Brainvisa
        * tab, newline and null character
    """
    cleanup_table = string.maketrans('(){} \t\r\n\0', '         ')

    attribute = attribute.translate(cleanup_table)
    attribute = attribute.replace(" ", "")

    return attribute


def insert_tool(tools, tool, allowed_instances):
    """ Add tool to list if tool is sub class
    of one item in allowed_instances
    """
    allowed_instances = allowed_instances or [object, ]
    if isinstance(tool, type) and tool not in allowed_instances:
        # (tool must not have the exact type of the allowed_instances types
        # otherwise it will always be inserted since the base classes are
        # always imported before being subclassed in a module)
        for check_instance in allowed_instances:
            if issubclass(tool, check_instance):
                tools.append(tool)
                break

