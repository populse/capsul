# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os.path
import sys

''' Information module describing the Capsul package.
'''

# Capsul current version
version_major = 2
version_minor = 3
version_micro = 0
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
    ('RUN', 'RECOMMENDS', 'python-qt5', 'RUN'),
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
SOMA_MIN_VERSION = "4.6.1"

# dependencies
SOMA_WORKFLOW_MIN_VERSION = "2.9.0"
POPULSE_DB_MIN_VERSION = "1.1.1"
NIBABEL_MIN_VERSION = "1.0"
NETWORKX_MIN_VERSION = "1.0"
NUMPY_MIN_VERSION = "1.3"
SCIPY_MIN_VERSION = "0.7"
TRAITS_MIN_VERSION = "4.0"
NIPYPE_VERSION = "0.10.0"

# Main setup parameters
NAME = "capsul"
ORGANISATION = "Populse"
MAINTAINER = "Populse team"
MAINTAINER_EMAIL = "support@brainvisa.info"
DESCRIPTION = description
LONG_DESCRIPTION = long_description
URL = "https://github.com/populse/capsul"
DOWNLOAD_URL = "https://github.com/populse/capsul"
LICENSE = "CeCILL-B"
AUTHOR = "Populse team"
AUTHOR_EMAIL = "support@brainvisa.info"
PLATFORMS = "OS Independent"
ISRELEASE = ""
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = [
    "traits>={0}".format(TRAITS_MIN_VERSION),
    # activate the following line after soma-base > 4.6.1 is released
    #"soma-base[controller,subprocess]>={0}".format(SOMA_MIN_VERSION),
    "soma-base>={0}".format(SOMA_MIN_VERSION),
    "soma-workflow>={0}".format(SOMA_WORKFLOW_MIN_VERSION),
    "populse-db>={0}".format(POPULSE_DB_MIN_VERSION),
    "six>=1.13",
    "PyYAML",
]
EXTRA_REQUIRES = {
    "doc": [
        "sphinx>=1.0",
        "numpy>={0}".format(NUMPY_MIN_VERSION),
    ],
    "database": ["populse_db"],
    "nipype": [
        "numpy>={0}".format(NUMPY_MIN_VERSION),
        "scipy>={0}".format(SCIPY_MIN_VERSION),
        "nibabel>={0}".format(NIBABEL_MIN_VERSION),
        "networkx>={0}".format(NETWORKX_MIN_VERSION),
        "nipype=={0}".format(NIPYPE_VERSION),
    ],
}

# tests to run
test_commands = ['%s -m capsul.test --verbose' % os.path.basename(sys.executable)]
# Shorten the default timeout: tests usually last 4 minutes, and have a known
# deadlock issue so we want them to fail asap.
test_timeouts = [600]
