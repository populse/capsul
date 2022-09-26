import sys

from soma.qt_gui.qt_backend import QtGui

from .api import Capsul
from .config.configuration import ApplicationConfiguration
from .qt_gui.widgets.settings_editor import SettingsEditor


app_config = ApplicationConfiguration('global_config')
app = QtGui.QApplication(sys.argv)
capsul = Capsul()
w = SettingsEditor(capsul.engine())
w.show()
app.exec_()
del w