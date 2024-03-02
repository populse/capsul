import sys

from soma.qt_gui.qt_backend import Qt
from soma.qt_gui.qvtabbar import QVTabWidget

from capsul.config.configuration import get_config_class


class SettingsEditor(Qt.QDialog):
    def __init__(self, config, parent=None):
        super(SettingsEditor, self).__init__(parent)

        self.config = config

        layout = Qt.QVBoxLayout()
        self.setLayout(layout)

        env_layout = Qt.QHBoxLayout()
        layout.addLayout(env_layout)
        env_layout.addWidget(Qt.QLabel("Resource:"))
        self.resource_combo = Qt.QComboBox()
        self.resource_combo.setEditable(True)
        self.resource_combo.setInsertPolicy(Qt.QComboBox.InsertAlphabetically)
        self.resource_combo.addItem("builtin")
        env_layout.addWidget(self.resource_combo)

        # htab_layout = Qt.QHBoxLayout()
        self.tab_wid = QVTabWidget()  # Qt.QTabWidget()
        # self.tab_wid.setTabPosition(Qt.QTabWidget.West)
        layout.addWidget(self.tab_wid)
        self.module_tabs = {}

        buttons_layout = Qt.QHBoxLayout()
        layout.addLayout(buttons_layout)
        buttons_layout.addStretch(1)
        ok = Qt.QPushButton("OK")
        buttons_layout.addWidget(ok)
        cancel = Qt.QPushButton("Cancel")
        buttons_layout.addWidget(cancel)

        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        # ok.setDefault(True)
        self.resource_combo.activated.connect(self.change_resource)

        self.update_gui()

    def update_gui(self):
        self.tab_wid.clear()
        self.module_tabs = {}
        resource = self.resource_combo.currentText()
        non_modules = {
            "dataset",
            "config_modules",
            "python_modules",
            "database",
            "persistent",
            "start_workers",
        }
        mod_map = [
            f.name
            for f in getattr(self.config, resource).fields()
            if f.name not in non_modules
        ]
        for short_module_name in sorted(mod_map):
            module_class = get_config_class(short_module_name)
            module_name = module_class.__module__
            module = sys.modules.get(module_name)
            if module:
                edition_func = getattr(module, "edition_widget", None)
                if edition_func:
                    tab = edition_func(self.engine, resource)
                    self.tab_wid.addTab(tab, short_module_name)
                    self.module_tabs[module] = tab

    def change_resource(self, index):
        resource = self.resource_combo.currentText()
        print("change_resource:", resource)
        self.update_gui()

    def accept(self):
        super(SettingsEditor, self).accept()
        for module_name, tab in self.module_tabs.items():
            tab.accept()
