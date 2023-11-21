import os.path
import sys

""" Information module describing the Capsul package.
"""

# Capsul current version
version_major = 3
version_minor = 0
version_micro = 0
version_extra = ""

# The following variables are here for backward compatibility in order to
# ease a transition for bv_maker users. They will be removed in a few days.
_version_major = version_major
_version_minor = version_minor
_version_micro = version_micro
_version_extra = version_extra

# Expected by setup.py: string of form "X.Y.Z"
__version__ = f"{version_major}.{version_minor}.{version_micro}"

brainvisa_dependencies = [
    "soma-base",
    "soma-workflow",
    ("RUN", "RECOMMENDS", "python-qt4", "RUN"),
    ("RUN", "RECOMMENDS", "graphviz", "RUN"),
]

# Expected by setup.py: the status of the project
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Environment :: X11 Applications :: Qt",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Topic :: Scientific/Engineering",
    "Topic :: Utilities",
]

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
SPHINX_MIN_VERSION = "1.0"
SOMA_MIN_VERSION = "6.0.0"

# dependencies
SOMA_WORKFLOW_MIN_VERSION = "2.9.0"
POPULSE_DB_MIN_VERSION = "3.0.0"
PYDANTIC_MIN_VERSION = "1.9.0"
NIBABEL_MIN_VERSION = "1.0"
NETWORKX_MIN_VERSION = "1.0"
NUMPY_MIN_VERSION = "1.3"
SCIPY_MIN_VERSION = "0.7"
NIPYPE_VERSION = "0.10.0"
TRAITS_MIN_VERSION = "4.0"

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
CLASSIFIERS = CLASSIFIERS
AUTHOR = "Populse team"
AUTHOR_EMAIL = "support@brainvisa.info"
PLATFORMS = "OS Independent"
ISRELEASE = ""
VERSION = __version__
PROVIDES = ["capsul"]
REQUIRES = [
    "redis <4.5.0",
    f"pydantic >={PYDANTIC_MIN_VERSION}",
    f"soma-base >={SOMA_MIN_VERSION}",
    f"soma-workflow >={SOMA_WORKFLOW_MIN_VERSION}",
    f"populse-db >={POPULSE_DB_MIN_VERSION}",
    "PyYAML",
]
EXTRA_REQUIRES = {
    "test": ["pytest", "jupyter"],
    "doc": [
        "sphinx >=1.0",
        f"numpy >={NUMPY_MIN_VERSION}",
    ],
    "nipype": [
        f"traits >={TRAITS_MIN_VERSION}",
        f"numpy >={NUMPY_MIN_VERSION}",
        f"scipy >={SCIPY_MIN_VERSION}",
        f"nibabel >={NIBABEL_MIN_VERSION}",
        f"networkx >={NETWORKX_MIN_VERSION}",
        f"nipype =={NIPYPE_VERSION}",
    ],
}

# tests to run
test_commands = ["%s -m capsul.test --verbose" % os.path.basename(sys.executable)]
# Shorten the default timeout: tests usually last 4 minutes, and have a known
# deadlock issue so we want them to fail asap.
test_timeouts = [600]
