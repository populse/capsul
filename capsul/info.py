#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

version_major = 0
version_minor = 0
version_micro = 1
version_extra = '.dev'

# The following variables are here for backward compatibility in order to
# ease a transition for bv_maker users. They will be removed in a few days.
_version_major = version_major
_version_minor = version_minor
_version_micro = version_micro
_version_extra = version_extra

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
__version__ = "%s.%s.%s%s" % (version_major,
                              version_minor,
                              version_micro,
                              version_extra)
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
ISRELEASE = version_extra == ''
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = ["nipype=={0}".format(NIPYPE_VERSION)]
EXTRA_REQUIRES = {"doc": ["sphinx>=1.0"]}
