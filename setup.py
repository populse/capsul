#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from ez_setup import use_setuptools
use_setuptools()
import os
from setuptools import find_packages, setup
import argparse
import sys

# Select which package is created: core or gui
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--gui", help="Create the gui package.",
                    action="store_true")
options, unknown = parser.parse_known_args()
sys.argv = [sys.argv[0]] + unknown

# Select appropriate modules
modules = find_packages()
core_modules = []
gui_modules = ["capsul"]
for module in modules:
    if module.startswith("capsul.wip"):
        continue
    if module.startswith(("capsul.qt_apps", "capsul.qt_gui")):
        gui_modules.append(module)
    else:
        core_modules.append(module)

# Set selcted package options
if options.gui:
    import capsul
    name_suffix = "gui"
    modules = gui_modules
    scripts = ["capsul/qt_apps/capsulview"]
    pkgdata = {"capsul.qt_apps.resources": ["*.ui", "*.png", "*.qrc", "*.txt"]}
    release_info = {}
    execfile(os.path.join(os.path.dirname(capsul.__file__), "info.py"),
             release_info)
else:
    name_suffix = "core"
    modules = core_modules
    scripts = []
    pkgdata = {
        "capsul.utils.test": ["*.xml"],
        "capsul.pipeline.test": ["*.json"]
    }
    release_info = {}
    execfile(os.path.join("capsul", "info.py"), release_info)

# Build the setup
setup(
    name="{0}-{1}".format(release_info["NAME"], name_suffix),
    description=release_info["DESCRIPTION"],
    long_description=release_info["LONG_DESCRIPTION"],
    license=release_info["LICENSE"],
    classifiers=release_info["CLASSIFIERS"],
    author=release_info["AUTHOR"],
    author_email=release_info["AUTHOR_EMAIL"],
    version=release_info["VERSION"],
    url=release_info["URL"],
    packages=modules,
    package_data=pkgdata,
    platforms=release_info["PLATFORMS"],
    extras_require=release_info["EXTRA_REQUIRES"],
    install_requires=release_info["REQUIRES"],
    scripts=scripts
)
