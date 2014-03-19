#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from PySide.QtUiTools import QUiLoader
from PySide import QtCore
from capsul.apps_qt.resources.icones import *


class MyQUiLoader(QUiLoader):
    """ Base window class based on ui file description.
    """

    def __init__(self, uifile):
        """ Method to initialize the base window.

        Parameters
        ----------
        uifile: str (mandatory)
            a filename containing the user interface description.
        """
        QUiLoader.__init__(self)
        fname = QtCore.QFile(uifile)
        fname.open(QtCore.QFile.ReadOnly)
        self.ui = self.load(fname)
        fname.close()
