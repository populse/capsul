##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
import sys


qt_backend = None


def get_qt_backend():
    '''get currently setup or loaded Qt backend name: "PyQt4" or "PySide"'''
    global qt_backend
    if qt_backend is None:
        pyqt = sys.modules.get('PyQt4')
        if pyqt is not None:
            qt_backend = 'PyQt4'
        else:
            pyside = sys.modules.get('PySide')
            if pyside is not None:
                qt_backend = 'PySide'
    return qt_backend


def set_qt_backend(backend=None):
    '''set the Qt backend.

    If a different backend has already setup or loaded, a warning is issued.
    If no backend is specified, try to guess which one is already loaded, or
    default to PyQt4.

    After the backend is set, QtCore and QtGui modules are imported and
    available in the current module.
    Moreover if using PyQt4, QtCore is patched to duplicate QtCore.pyqtSignal
    and QtCore.pyqtSlot as QtCore.Signal and QtCore.Slot.

    Parameters
    ----------
    backend: str (default: None)
        name of the backend to use

    Examples
    --------
        >>> from capsul.apps_qt import qt_backend
        >>> qt_backend.set_qt_backend('PySide')
        >>> qt_backend.QtCore
        <module 'PySide.QtCore' from '/usr/lib/python2.7/dist-packages/PySide/QtCore.so'>
    '''
    global qt_backend
    get_qt_backend()
    if backend is None:
        if qt_backend is None:
            backend = 'PyQt4'
        else:
            backend = qt_backend
    if qt_backend is not None and qt_backend != backend:
        logging.warn('set_qt_backend: a different backend, %s, has already ' \
            'be set, and %s is now requested' % (qt_backend, backend))
    if backend == 'PyQt4' and sys.modules.get('PyQt4') is None:
        import sip
        SIP_API = 2
        sip_classes = ['QString', 'QVariant', 'QDate', 'QDateTime',
            'QTextStream', 'QTime', 'QUrl']
        for sip_class in sip_classes:
            sip.setapi(sip_class, SIP_API)
    qt_module = __import__(backend)
    __import__(backend + '.QtCore')
    __import__(backend + '.QtGui')
    sys.modules[__name__].QtCore = qt_module.QtCore
    sys.modules[__name__].QtGui = qt_module.QtGui
    qt_backend = backend
    if backend == 'PyQt4':
        qt_module.QtCore.Signal = qt_module.QtCore.pyqtSignal
        qt_module.QtCore.Slot = qt_module.QtCore.pyqtSlot


def get_qt_module():
    '''Get the main Qt module (PyQt4 or PySide)'''
    global qt_backend
    return sys.modules.get(qt_backend)


def import_qt_submodule(submodule):
    '''Import a specified Qt submodule, and export it in the current module

    Parameters
    ----------
        submodule: str (mandatory)
            submodule name, ex: QtWebKit

    Returns
    -------
        the loaded submodule
    '''
    mod = __import__(qt_backend + '.' + submodule)
    setattr(sys.modules[__name__], submodule, mod)
    return mod


def loadUI(ui_file):
    '''Load a .ui file and returns the widget instance
    '''
    if get_qt_backend() == 'PyQt4':
        from PyQt4 import uic
        return uic.loadUi(ui_file)
    else:
        from PySide import QtUiTools
        return QtUiTools.QUiLoader().load(ui_file)

