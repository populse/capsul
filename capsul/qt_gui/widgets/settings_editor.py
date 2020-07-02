# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import sys
from capsul.engine import CapsulEngine
from soma.qt_gui.qt_backend import Qt
from soma.qt_gui.qvtabbar import QVTabBar, QVTabWidget


class SettingsEditor(Qt.QDialog):

    def __init__(self, engine, parent=None):
        super(SettingsEditor, self).__init__(parent)

        self.engine = engine

        layout = Qt.QVBoxLayout()
        self.setLayout(layout)

        env_layout = Qt.QHBoxLayout()
        layout.addLayout(env_layout)
        env_layout.addWidget(Qt.QLabel('Environment:'))
        self.environment_combo = Qt.QComboBox()
        env_layout.addWidget(self.environment_combo)

        #htab_layout = Qt.QHBoxLayout()
        self.tab_wid = QVTabWidget()  # Qt.QTabWidget()
        #self.tab_wid.setTabPosition(Qt.QTabWidget.West)
        layout.addWidget(self.tab_wid)
        self.module_tabs = {}

        buttons_layout = Qt.QHBoxLayout()
        layout.addLayout(buttons_layout)
        buttons_layout.addStretch(1)
        ok = Qt.QPushButton('OK')
        buttons_layout.addWidget(ok)
        cancel = Qt.QPushButton('Cancel')
        buttons_layout.addWidget(cancel)

        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        ok.setDefault(True)

        self.update_gui()

    def update_gui(self):
        self.environment_combo.clear()
        self.environment_combo.addItem('global')
        self.tab_wid.clear()
        self.module_tabs = {}
        environment = self.environment_combo.currentText()
        for module_name in self.engine._loaded_modules:
            module = sys.modules.get(module_name)
            if module:
                edition_func = getattr(module, 'edition_widget', None)
                if edition_func:
                    tab = edition_func(self.engine, environment)
                    self.tab_wid.addTab(tab, module_name.split('.')[-1])
                    self.module_tabs[module] = tab

    def accept(self):
        for module_name, tab in self.module_tabs.items():
            tab.accept()
        super(SettingsEditor, self).accept()
