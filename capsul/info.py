#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# Capsul current version
version_major = 0
version_minor = 0
version_micro = 1
version_extra = ""

# The following variables are here for backward compatibility in order to
# ease a transition for bv_maker users. They will be removed in a few days.
_version_major = version_major
_version_minor = version_minor
_version_micro = version_micro
_version_extra = version_extra

# Expected by setup.py: string of form "X.Y.Z"
__version__ = "{0}.{1}.{2}{3}".format(
    version_major, version_minor, version_micro, version_extra)

# Expected by setup.py: the status of the project
CLASSIFIERS = ["Development Status :: 1 - Planning",
               "Environment :: Console",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Scientific/Engineering",
               "Topic :: Utilities"]

# Project descriptions
description = "CAPSUL"
long_description = """
========
CAPSUL 
========

[capsul] Collaborative Analysis Platform: Simple Unifying, Lean.
CAPSUL is a powerful tool to define and share processing pipelines.
"""

# Capsul dependencies
SPHINX_MIN_VERSION = 1.0
SOMA_WORKFLOW_MIN_VERSION = "2.6.0"
SOMA_MIN_VERSION = "4.5.0"

# Nipype dependencies: pypi package is not taged correctly
NIBABEL_MIN_VERSION = "1.0"
NETWORKX_MIN_VERSION = "1.0"
NUMPY_MIN_VERSION = "1.3"
SCIPY_MIN_VERSION = "0.7"
TRAITS_MIN_VERSION = "4.0"
NIPYPE_VERSION = "0.9.2"

# Main setup parameters
NAME = "capsul"
ORGANISATION = "CEA"
MAINTAINER = "Antoine Grigis"
MAINTAINER_EMAIL = "antoine.grigis@cea.fr"
DESCRIPTION = description
LONG_DESCRIPTION = long_description
URL = ""
DOWNLOAD_URL = ""
LICENSE = "CeCILL-B"
CLASSIFIERS = CLASSIFIERS
AUTHOR = "CAPSUL developers"
AUTHOR_EMAIL = "antoine.grigis@cea.fr"
PLATFORMS = "OS Independent"
ISRELEASE = version_extra == ""
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = [
    "numpy>={0}".format(NUMPY_MIN_VERSION),
    "scipy>={0}".format(SCIPY_MIN_VERSION),
    "nibabel>={0}".format(NIBABEL_MIN_VERSION),
    "networkx>={0}".format(NETWORKX_MIN_VERSION),
    "traits>={0}".format(TRAITS_MIN_VERSION),
    "nipype=={0}".format(NIPYPE_VERSION),
    "soma-base>={0}".format(SOMA_MIN_VERSION),
    "soma-workflow>={0}".format(SOMA_WORKFLOW_MIN_VERSION)
]
EXTRA_REQUIRES = {
    "doc": ["sphinx>=1.0"]
}
