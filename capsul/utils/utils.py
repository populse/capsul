#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
import shutil


def get_tool_version(tool):
    """ Get the version of a python tool
    Parameters
    ----------
    tool: str (mandatory)
    a tool name

    Returns
    -------
    version: str (default None)
    the tool version.
    """
    version = None
    try:
        module = __import__(tool)
        version = module.__version__
    except:
        pass
    return version


def get_nipype_interfaces_versions():
    """
    """
    try:
        nipype_module = __import__("nipype.interfaces")
        sub_modules = ["{0}".format(i)
                        for i in dir(nipype_module)
                        if (not i.startswith("_") and
                            not i[0].isupper())]
        versions = {}
        for module in sub_modules:
            try:
                version = eval("nipype_module.{0}."
                               "Info.version()".format(module))
                if version:
                    versions[module] = version
            except:
                pass

        return versions
    except:
        return {}
