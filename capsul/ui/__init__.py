# -*- coding: utf-8 -*-
import os
from soma.qt_gui.qt_backend.Qt import QVariant
from soma.web import WebBackend, json_exception, pyqtSlot


class CapsulWebBackend(WebBackend):
    def __init__(self, capsul):
        super().__init__()
        s = os.path.split(os.path.dirname(__file__)) + ('static',)
        self.static_path.append("/".join(s))
        self._capsul = capsul
    
    @pyqtSlot(result=QVariant)
    @json_exception
    def engines(self):
        return [engine.engine_status() for engine in self._capsul.engines()]


    @pyqtSlot(str, result=QVariant)
    @json_exception
    def engine_status(self, engine_label):
        try:
            engine = self._capsul.engine(engine_label)
        except ValueError:
            return {}
        return engine.engine_status()


    @pyqtSlot(str, result=QVariant)
    @json_exception
    def executions_summary(self, engine_label):
        return self._capsul.engine(engine_label).executions_summary()


    @pyqtSlot(str, str, result=QVariant)
    @json_exception
    def execution_report(self, engine_label, execution_id):
        with self._capsul.engine(engine_label) as engine:
            return engine.database.execution_report_json(engine.engine_id, execution_id)
