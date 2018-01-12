##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import sys

# Capsul current version
version_major = 2
version_minor = 1
version_micro = 3
version_extra = ""

# The following variables are here for backward compatibility in order to
# ease a transition for bv_maker users. They will be removed in a few days.
_version_major = version_major
_version_minor = version_minor
_version_micro = version_micro
_version_extra = version_extra

# Expected by setup.py: string of form "X.Y.Z"
__version__ = "{0}.{1}.{2}".format(version_major, version_minor, version_micro)

brainvisa_dependencies = [
    'soma-base',
    'soma-workflow',
    ('RUN', 'RECOMMENDS', 'python-qt4', 'RUN'),
    ('RUN', 'RECOMMENDS', 'graphviz', 'RUN'),
]

# Expected by setup.py: the status of the project
CLASSIFIERS = ["Development Status :: 5 - Production/Stable",
               "Environment :: Console",
               "Environment :: X11 Applications :: Qt",
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
SOMA_MIN_VERSION = "4.6.0"

# dependencies
SOMA_WORKFLOW_MIN_VERSION = "2.9.0"
NIBABEL_MIN_VERSION = "1.0"
NETWORKX_MIN_VERSION = "1.0"
NUMPY_MIN_VERSION = "1.3"
SCIPY_MIN_VERSION = "0.7"
TRAITS_MIN_VERSION = "4.0"
NIPYPE_VERSION = "0.10.0"

# Main setup parameters
NAME = "capsul"
ORGANISATION = "CEA"
MAINTAINER = ""
MAINTAINER_EMAIL = ""
DESCRIPTION = description
LONG_DESCRIPTION = long_description
URL = ""
DOWNLOAD_URL = ""
LICENSE = "CeCILL-B"
CLASSIFIERS = CLASSIFIERS
AUTHOR = "BrainVISA team"
AUTHOR_EMAIL = "support@brainvisa.info"
PLATFORMS = "OS Independent"
ISRELEASE = ""
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = [
    "traits>={0}".format(TRAITS_MIN_VERSION),
    "soma-base>={0}".format(SOMA_MIN_VERSION),
]
EXTRA_REQUIRES = {
    "doc": [
        "sphinx>=1.0",
        "numpy>={0}".format(NUMPY_MIN_VERSION),
    ],
    "distributed": ["soma-workflow>={0}".format(SOMA_WORKFLOW_MIN_VERSION)],
    "nipype": [
        "numpy>={0}".format(NUMPY_MIN_VERSION),
        "scipy>={0}".format(SCIPY_MIN_VERSION),
        "nibabel>={0}".format(NIBABEL_MIN_VERSION),
        "networkx>={0}".format(NETWORKX_MIN_VERSION),
        "nipype=={0}".format(NIPYPE_VERSION),
    ],

}

# tests to run
test_commands = ['%s -m capsul.test.test_capsul' % sys.executable]

