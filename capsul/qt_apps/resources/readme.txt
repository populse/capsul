##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# WARNING: this results in a python file which will NOT work with PyQt
# We'd better use compiled binary resources (rcc -binary)

compile resources with pyside-tools: 
    pyside-rcc icones.qrc -o icones.py
