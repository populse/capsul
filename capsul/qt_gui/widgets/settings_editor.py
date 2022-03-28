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
        self.environment_combo.setEditable(True)
        self.environment_combo.setInsertPolicy(
            Qt.QComboBox.InsertAlphabetically)
        self.environment_combo.addItem('global')
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
        #ok.setDefault(True)
        self.environment_combo.activated.connect(self.change_environment)

        self.update_gui()

    def update_gui(self):
        self.tab_wid.clear()
        self.module_tabs = {}
        environment = self.environment_combo.currentText()
        mod_map = dict([(module_name.split('.')[-1], module_name)
                        for module_name in self.engine._loaded_modules])
        for short_module_name in sorted(mod_map.keys()):
            module_name = mod_map[short_module_name]
            module = sys.modules.get(module_name)
            if module:
                edition_func = getattr(module, 'edition_widget', None)
                if edition_func:
                    tab1 = QVTabWidget()
                    #self.module_tabs[module] = tab1
                    self.tab_wid.addTab(tab1, short_module_name)
                    #self.tab_wid.addTab(tab, short_module_name)
                    config_ids = []
                    with self.engine.settings as session:
                        for config in session.configs(module_name,
                                                      environment):
                            config_ids.append(config._id)
                    if not config_ids:
                        config_ids = [short_module_name]
                    for config_id in config_ids:
                        tab = edition_func(self.engine, environment,
                                           config_id)
                        tab1.addTab(tab, config_id)
                        self.module_tabs.setdefault(
                            module_name, {})[config_id] = tab

    def change_environment(self, index):
        environment = self.environment_combo.currentText()
        self.update_gui()

    def accept(self):
        super(SettingsEditor, self).accept()
        for module_name, tab1 in self.module_tabs.items():
            for config_id, tab in tab1.items():
                tab.accept()
