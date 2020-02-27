# -*- coding: utf-8 -*-
##########################################################################
# CAPSUL - CAPS - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from __future__ import absolute_import
import os
import sys
import logging


def load_pilots(root, path, root_module_name):
    """ Load all the pilot functions.

    Path is recursively scanned for ``__init__.py`` files.
    Any function declared inside whose name start with ``pilot_`` will be
    loaded.

    Parameters
    ----------
    root: str (mandatory)
        path to the use_cases module.
    path: str
        path to the module.
    root_module_name: str (mandatory)
        the name of the package.

    Returns
    -------
    pilots: dict
        a dict with module name as keys referencing to function module
        used for unitest.
    """
    # List the module path
    items = os.listdir(path)

    # Got through mdole items
    pilots = {}
    for item in items:
        # If a directory is found, try to load the potential module
        if os.path.isdir(os.path.join(path, item)):
            sub_pilots = load_pilots(
                root, os.path.join(path, item), root_module_name)
            pilots.update(sub_pilots)

    # Check if we are in a valid python module
    if not any([x in items for x in ["__init__.py"]]):
        return pilots

    # Go through all python files
    for fname in items:
        # Check if the file is a python file
        if fname.endswith(".py"):
            if fname == '__main__.py':
                # skip main
                continue
            # Construct the module name
            module_name = (
                [root_module_name] +
                path[len(os.path.normpath(root)) + 1:].split(os.path.sep) +
                [os.path.splitext(fname)[0]])
            module_name = ".".join([x for x in module_name if x])

            # Try to load the module from its string description
            try:
                __import__(module_name)
                module = sys.modules[module_name]

                # Try to find the pilots
                for function in dir(module):
                    if function.startswith("pilot_"):
                        pilots.setdefault(module_name, []).append(
                            getattr(module, function))

            # An api exists, but it cannot be imported
            except ImportError as e:
                logging.debug(
                    "Could not import {0}: {1}".format(module_name, e))
                raise

    return pilots
