#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os, sys
import logging


def load_pilots(root, path):
    """ Load all the modules in the use_cases module: path is
    recursively scanned for __init__.py files.
    Any function declared inside will be loaded.

    Parameters
    ----------
    root : str (mandatory)
        path to the use_cases module.
    path : str
        path to the module

    Returns
    -------
    pilots : dict
        a dict with module name as keys referencing to function module used
        for unitest.
    """

    pilots = {}
    files = os.listdir(path)

    for fname in files:
        if os.path.isdir(os.path.join(path, fname)):
            sub_pilots = load_pilots(root, os.path.join(path, fname))
            pilots.update(sub_pilots)

    if not any([x in files for x in ["__init__.py", ]]):
        # No __init__ file
        return pilots

    for fname in files:
        if fname.endswith(".py") and fname.startswith("test_"):

            module_name = (["capsul"] +
                path[len(os.path.normpath(root)) + 1:].split(os.path.sep) +
                [os.path.splitext(fname)[0]])
            module_name = ".".join([x for x in module_name if x])

            try:
                __import__(module_name)
            except ImportError, e:
                # An api exists, but it cannot be imported
                logging.debug("Could not import {0}:"
                              "{1}".format(module_name, e))
                return pilots

            module = sys.modules[module_name]

            for function in dir(module):
                if function in ["test", ]:
                    if module_name in  pilots.keys():
                        pilots[module_name].append(getattr(module, function))
                    else:
                        pilots[module_name] = [getattr(module, function), ]

    return pilots


if __name__ == "__main__":

    import soma
    module_path = soma.__path__[0]
    print load_pilots(module_path, module_path)
