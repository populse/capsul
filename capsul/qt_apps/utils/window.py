"""
Classes
=======
:class:`MyQUiLoader`
--------------------
"""

# Soma import
from soma.qt_gui import qt_backend

# Capsul import
from capsul.qt_apps.resources.icones import *


class MyQUiLoader:
    """Base window class based on ui file description."""

    def __init__(self, uifile):
        """Method to initialize the base window.

        Parameters
        ----------
        uifile: str (mandatory)
            a filename containing the user interface description.
        """
        self.ui = qt_backend.loadUi(uifile)
