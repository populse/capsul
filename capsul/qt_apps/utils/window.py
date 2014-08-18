#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# Soma import
from soma.qt_gui import qt_backend

# Capsul import
from capsul.qt_apps.resources.icones import *


class MyQUiLoader(object):
    """ Base window class based on ui file description.
    """

    def __init__(self, uifile):
        """ Method to initialize the base window.

        Parameters
        ----------
        uifile: str (mandatory)
            a filename containing the user interface description.
        """
        self.ui = qt_backend.loadUi(uifile)
