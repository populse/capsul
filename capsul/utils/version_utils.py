# -*- coding: utf-8 -*-
'''
Functions
=========
:func:`get_tool_version`
------------------------
:func:`get_nipype_interfaces_versions`
--------------------------------------
'''

# System import
from __future__ import absolute_import
import logging

# Define the logger
logger = logging.getLogger(__name__)


def get_tool_version(tool):
    """ Get the version of a python tool.

    Check if the python tool module has a '__version__' attribute and return
    this value. If this attribute is not found, return None.

    Parameters
    ----------
    tool: str (mandatory)
        a tool name

    Returns
    -------
    version: str
        the tool version, None if no information found in the module.
    """
    # Initialize the version to None ie. not found
    version = None

    # Try to get the '__version__' module attribute.
    try:
        module = __import__(tool)
        version = module.__version__
    except Exception:
        pass

    # Debug message
    logger.debug("Module '{0}' version is {1}".format(tool, version))

    return version


def get_nipype_interfaces_versions():
    """ Get the versions of the nipype interfaces.

    If nipype is not found, return None.
    If no interfaces are configured, returned an empty dictionary.

    Returns
    -------
    versions: dict
        a dictionary with interface names as keys and corresponding
        versions as values.
    """
    # Initialize the versions to an empty dict
    versions = {}

    # Try to load the nipype interfaces module
    try:
        nipype_module = __import__("nipype.interfaces")

        # List all the interface
        sub_modules = [
            "{0}".format(i)
            for i in dir(nipype_module)
            if (not i.startswith("_") and not i[0].isupper())]

        # For each interface, try to get its version and fill the
        # output structure
        for module in sub_modules:
            try:
                version = eval("nipype_module.{0}."
                               "Info.version()".format(module))
                if version:
                    versions[module] = version
            except Exception:
                pass
    except Exception:
        versions = None

    # Debug message
    logger.debug("Nipype interfaceversions are {0}".format(versions))

    return versions
