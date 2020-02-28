# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup

# Select appropriate modules
modules = find_packages()

scripts = ["capsul/qt_apps/capsulview"]
pkgdata = {
    "capsul.qt_apps.resources":
        ["*.ui", "*.png", "*.gif", "*.qrc", "*.txt"],
    "capsul.utils.test": ["*.xml"],
    "capsul.process.test": ["*.xml"],
    "capsul.pipeline.test": ["*.json"]
}

release_info = {}
python_dir = os.path.dirname(__file__)
with open(os.path.join(python_dir, "capsul", "info.py")) as f:
    code = f.read()
    exec(code, release_info)


# Build the setup
setup(
    name=release_info["NAME"],
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
