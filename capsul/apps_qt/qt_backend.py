##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''Compatibility module for PyQt and PySide. Currently supports PyQt4 and
PySide, not PyQt5.
This modules handles differences between PyQt and PySide APIs and behaviours,
and offers a few functions to make it easier to build neutral GUI code, which
can run using either backend.

The main funcion here is set_qt_backend() which must be called to initialize
the appropriate backend. Most functions of this module assume set_qt_backend()
has been called first to setup internal variables.

Note that such compatibility generally requires to use PyQt4 with SIP API
version 2, ie do not use QString, QVariant, QDate and similar classes, but
directly convert to/from python types, which is also PySide behaviour. The
qt_backend module switches to this API level 2, but this only works before the
PyQt modules are imported, thus it may fail if PyQt has already be imported
without such settings.

Qt submodules can be imported in two ways:

>>> from capsul.apps_qt import qt_backend
>>> qt_backend.import_qt_submodule('QtWebKit')

or using the import statement:

>>> from capsul.apps_qt.qt_backend import QtWebKit

in the latter case, set_qt_backend() will be called automatically to setup the
appropriate Qt backend, so that the use of the backend selection is more
transparent.
'''

import logging
import sys
import os
import imp


# make qt_backend a fake module package, with Qt modules as sub-modules
__package__ = __name__
__path__ = [os.path.dirname(__file__)]

qt_backend = None


class QtImporter(object):
    def find_module(self, fullname, path=None):
        modsplit = fullname.split('.')
        modpath = '.'.join(modsplit[:-1])
        module_name = modsplit[-1]
        if modpath != __name__ or module_name == 'sip':
            return None
        set_qt_backend()
        qt_module = get_qt_module()
        found = imp.find_module(module_name, qt_module.__path__)
        return self

    def load_module(self, name):
        qt_backend = get_qt_backend()
        module_name = name.split('.')[-1]
        __import__('.'.join([qt_backend, module_name]))
        return sys.modules['.'.join([qt_backend, module_name])]

# tune the import statement to get Qt submodules in this one
sys.meta_path.append(QtImporter())


def get_qt_backend():
    '''get currently setup or loaded Qt backend name: "PyQt4" or "PySide"'''
    global qt_backend
    if qt_backend is None:
        pyside = sys.modules.get('PySide')
        if pyside is not None:
            qt_backend = 'PySide'
        else:
            pyqt = sys.modules.get('PyQt4')
            if pyqt is not None:
                qt_backend = 'PyQt4'
    return qt_backend


def set_qt_backend(backend=None):
    '''set the Qt backend.

    If a different backend has already setup or loaded, a warning is issued.
    If no backend is specified, try to guess which one is already loaded, or
    default to PySide.

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
        >>> qt_backend.import_qt_submodule('QtCore')
        <module 'PySide.QtCore' from '/usr/lib/python2.7/dist-packages/PySide/QtCore.so'>
    '''
    global qt_backend
    get_qt_backend()
    if backend is None:
        if qt_backend is None:
            backend = 'PySide'
        else:
            backend = qt_backend
    if qt_backend is not None and qt_backend != backend:
        logging.warn('set_qt_backend: a different backend, %s, has already ' \
            'be set, and %s is now requested' % (qt_backend, backend))
    if backend == 'PyQt4': # and sys.modules.get('PyQt4') is None:
        import sip
        SIP_API = 2
        sip_classes = ['QString', 'QVariant', 'QDate', 'QDateTime',
            'QTextStream', 'QTime', 'QUrl']
        for sip_class in sip_classes:
            try:
                sip.setapi(sip_class, SIP_API)
            except ValueError, e:
                logging.error(e.message)
    qt_module = __import__(backend)
    __import__(backend + '.QtCore')
    __import__(backend + '.QtGui')
    qt_backend = backend
    if backend == 'PyQt4':
        qt_module.QtCore.Signal = qt_module.QtCore.pyqtSignal
        qt_module.QtCore.Slot = qt_module.QtCore.pyqtSlot


def get_qt_module():
    '''Get the main Qt module (PyQt4 or PySide)'''
    global qt_backend
    return sys.modules.get(qt_backend)


def import_qt_submodule(submodule):
    '''Import a specified Qt submodule.
    An alternative to the standard statement:

    >>> from capsul.apps_qt.qt_backend import <submodule>

    The main differences is that it forces loading the module from the 
    appropriate backend, whereas the import statement will reuse the already
    loaded one. Moreover it returns the module.

    For instance,

    >>> from capsul.apps_qt import qt_backend
    >>> qt_backend.set_qt_backend('PyQt4')
    >>> from capsul.apps_qt.qt_backend import QtWebKit
    >>> QtWebKit
    <module 'PyQt4.QtWebKit' from '/usr/lib/python2.7/dist-packages/PyQt4/QtWebKit.so'>
    >>> qt_backend.set_qt_backend('PySide') # changing backend
    WARNING:root:set_qt_backend: a different backend, PyQt4, has already be set, and PySide is now requested
    >>> from capsul.apps_qt.qt_backend import QtWebKit
    >>> QtWebKit
    <module 'PyQt4.QtWebKit' from '/usr/lib/python2.7/dist-packages/PyQt4/QtWebKit.so'>

    In the above example, we are still using the QtWebKit from PyQt4.
    Now:

    >>> QtWebKit = qt_backend.import_qt_submodule('QtWebKit')
    >>> QtWebKit
    <module 'PySide.QtWebKit' from '/usr/lib/python2.7/dist-packages/PySide/QtWebKit.so'>

    We are now actually using PySide.
    Note that it is generally a bad idea to mix both...

    Parameters
    ----------
        submodule: str (mandatory)
            submodule name, ex: QtWebKit

    Returns
    -------
        the loaded submodule
    '''
    __import__(qt_backend + '.' + submodule)
    mod = sys.modules[qt_backend + '.' + submodule]
    return mod


def loadUi(ui_file):
    '''Load a .ui file and returns the widget instance
    '''
    if get_qt_backend() == 'PyQt4':
        from PyQt4 import uic
        return uic.loadUi(ui_file)
    else:
        from PySide import QtUiTools
        return QtUiTools.QUiLoader().load(ui_file)


def getOpenFileName(parent=None, caption='', directory='', filter='',
        selectedFilter=None, options=0):
    '''PyQt4 / PySide compatible call to QFileDialog.getOpenFileName'''
    if get_qt_backend() == 'PyQt4':
        return get_qt_module().QtGui.QFileDialog.getOpenFileName(parent,
            caption, directory, filter, selectedFilter,
            QtGui.QFileDialog.Options(options))
    else:
        return get_qt_module().QtGui.QFileDialog.getOpenFileName(parent,
            caption, directory, filter, selectedFilter,
            QtGui.QFileDialog.Options(options))[0]


def getSaveFileName(parent=None, caption='', directory='', filter='',
        selectedFilter=None, options=0):
    '''PyQt4 / PySide compatible call to QFileDialog.getSaveFileName'''
    if get_qt_backend() == 'PyQt4':
        return get_qt_module().QtGui.QFileDialog.getSaveFileName(parent,
            caption, directory, filter, selectedFilter, options)
    else:
        return get_qt_module().QtGui.QFileDialog.getSaveFileName(parent,
            caption, directory, filter, selectedFilter, options)[0]


def init_matplotlib_backend():
    '''Initialize Matplotlib to use Qt, and the appropriate Qt/Python binding
    (PySide or PyQt) according to the configured/loaded toolkit.
    Moreover, the appropriate FigureCanvas type is set in the current module,
    and returned by this function.
    '''
    import matplotlib
    matplotlib.use('Qt4Agg')
    if get_qt_backend() == 'PySide':
        if 'backend.qt4' in matplotlib.rcParams.keys():
            matplotlib.rcParams['backend.qt4'] = 'PySide'
        else:
            raise RuntimeError("Could not use Matplotlib, the backend using " \
                "PySide is missing.")
    else:
        if 'backend.qt4' in matplotlib.rcParams.keys():
            matplotlib.rcParams['backend.qt4'] = 'PyQt4'
        else:
            raise RuntimeError("Could not use Matplotlib, the backend using " \
                "PyQt4 is missing.")
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg \
        as FigureCanvas
    sys.modules[__name__].FigureCanvas = FigureCanvas
    return FigureCanvas

