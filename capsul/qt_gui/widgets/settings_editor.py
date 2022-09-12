# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import sys
from capsul.engine import CapsulEngine
from soma.qt_gui.qt_backend import Qt
from soma.qt_gui.qvtabbar import QVTabBar, QVTabWidget
from functools import partial


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
        self.environment_combo.addItems(engine.settings.get_all_environments())
        self.environment_combo.setCurrentText('global')
        env_layout.addWidget(self.environment_combo)
        self.environment = 'global'

        #htab_layout = Qt.QHBoxLayout()
        self.tab_wid = QVTabWidget()  # Qt.QTabWidget()
        #self.tab_wid.setTabPosition(Qt.QTabWidget.West)
        layout.addWidget(self.tab_wid)
        self.module_tabs = {}

        buttons_layout = Qt.QHBoxLayout()
        layout.addLayout(buttons_layout)
        buttons_layout.addStretch(1)
        ok = Qt.QPushButton('OK')
        ok.setDefault(False)
        ok.setAutoDefault(False)
        buttons_layout.addWidget(ok)
        cancel = Qt.QPushButton('Cancel')
        cancel.setDefault(False)
        cancel.setAutoDefault(False)
        buttons_layout.addWidget(cancel)

        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        #ok.setDefault(True)
        self.environment_combo.activated.connect(self.change_environment)

        self.update_gui()
        #self.tab_wid.currentChanged.connect(self.mod_tab_changed)

    def update_gui(self):
        self.tab_wid.clear()
        self.module_tabs = {}
        environment = self.environment
        mod_map = dict([(module_name.split('.')[-1], module_name)
                        for module_name in self.engine._loaded_modules])
        for short_module_name in sorted(mod_map.keys()):
            module_name = mod_map[short_module_name]
            module = sys.modules.get(module_name)
            if module:
                edition_func = getattr(module, 'edition_widget', None)
                if edition_func:
                    tab1 = QVTabWidget()
                    tab1.setTabsClosable(True)
                    tab1.tabCloseRequested.connect(partial(self.tab_closed,
                                                           short_module_name))
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
                    tab1.addTab(Qt.QWidget(), '+')
                    tab1.tabBar().tabButton(
                        tab1.count() -1, Qt.QTabBar.RightSide).hide()
                    #tab1.update_buttons()
                    tab1.currentChanged.connect(partial(self.tab_changed,
                                                        short_module_name))

    def change_environment(self, index):
        self.validate()
        self.environment = self.environment_combo.currentText()
        self.update_gui()

    def validate(self):
        for module_name, tab1 in self.module_tabs.items():
            for config_id, tab in tab1.items():
                try:
                    tab.accept()
                except Exception as e:
                    print(e, file=sys.stderr)

    def accept(self):
        self.validate()
        super(SettingsEditor, self).accept()

    def tab_closed(self, module, index):
        # print('close:', module, index)
        mod_index = [i for i in range(self.tab_wid.count())
                     if self.tab_wid.tabText(i) == module][0]
        mod_widget = self.tab_wid.widget(mod_index)
        if mod_widget.count() == 2 or index == mod_widget.count() - 1:
            return  # don't allow to remove the last config
        config_id = mod_widget.tabText(index)
        environment = self.environment
        self._modifying = True
        mod_widget.removeTab(index)
        with self.engine.settings as session:
            session.remove_config(module, environment, config_id)
        self._modifying = False
        mod_widget.setCurrentIndex(index - 1)

    #def mod_tab_changed(self, index):
        #self.tab_wid.widget(index).update_buttons()

    def tab_changed(self, module_name, index):
        if getattr(self, '_modifying', False):
            return
        self._modifying = True
        try:
            mod_index = [i for i in range(self.tab_wid.count())
                        if self.tab_wid.tabText(i) == module_name][0]
            mod_widget = self.tab_wid.widget(mod_index)
            former_index = getattr(mod_widget, 'former_current', 0)
            if index != mod_widget.count() - 1:
                mod_widget.former_current = index
                return

            dial = Qt.QDialog()
            dial.setWindowTitle('New config ID for module %s' % module_name)
            layout = Qt.QVBoxLayout()

            le = Qt.QLineEdit()
            tlay = Qt.QHBoxLayout()
            layout.addLayout(tlay)
            tlay.addWidget(Qt.QLabel('config id:'))
            tlay.addWidget(le)

            dial.setLayout(layout)
            blay = Qt.QHBoxLayout()
            layout.addLayout(blay)
            ok = Qt.QPushButton('OK')
            blay.addWidget(ok)
            cancel = Qt.QPushButton('Cancel')
            blay.addWidget(cancel)
            ok.clicked.connect(dial.accept)
            cancel.clicked.connect(dial.reject)

            res = dial.exec_()
            if res != Qt.QDialog.Accepted:
                mod_widget.setCurrentIndex(former_index)
                return
            config_id = le.text()
            if config_id == '':
                mod_widget.setCurrentIndex(former_index)
                return
            environment = self.environment
            with self.engine.settings as session:
                config = session.config(module_name, environment,
                                        'config_id=="%s"' % config_id)
                if config:
                    Qt.QMessageBox.critical(
                        self, 'invalid new config ID',
                        'config %s already exists' % config_id,
                        Qt.QMessageBox.Ok)
                    mod_widget.setCurrentIndex(former_index)
                    return
            with self.engine.settings as session:
                config = session.new_config(module_name, environment,
                                            {'config_id': config_id})
            mod_tab = self.tab_wid.currentIndex()
            self.validate()
            self.update_gui()
            self.tab_wid.setCurrentIndex(mod_tab)
            mod_index = [i for i in range(self.tab_wid.count())
                        if self.tab_wid.tabText(i) == module_name][0]
            mod_widget = self.tab_wid.widget(mod_index)
            mod_widget.setCurrentIndex(index)
            mod_widget.former_current = index
        finally:
            self._modifying = False
