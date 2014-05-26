#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

_version_major = 0
_version_minor = 0
_version_micro = 1
_version_extra = '.dev'

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
__version__ = "%s.%s.%s%s" % (_version_major,
                              _version_minor,
                              _version_micro,
                              _version_extra)
CLASSIFIERS = ["Development Status :: 1 - Planning",
               "Environment :: Console",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Scientific/Engineering",
               "Topic :: Utilities"]

description = 'CAPSUL'

long_description = """
========
CAPSUL 
========

[capsul] Collaborative Analysis Platform: Simple Unifying, Lean.
CAPSUL is a powerful tool to define and share pipelines.
"""

# versions for dependencies
SPHINX_MIN_VERSION = 1.0
NIPYPE_VERSION = '0.9.2'

# Main setup parameters
NAME = 'capsul'
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
MAJOR = _version_major
MINOR = _version_minor
MICRO = _version_micro
ISRELEASE = _version_extra == ''
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = ["nipype=={0}".format(NIPYPE_VERSION)]
EXTRA_REQUIRES = {"doc": ["sphinx>=1.0"]}
