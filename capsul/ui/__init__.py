# -*- coding: utf-8 -*-

from capsul.api import Capsul
from capsul.web import WebRoutes, WebBackend

from soma.qt_gui.qt_backend import Qt


class CapsulRoutes(WebRoutes):
    _templates = {"qt_backend.js", "html_backend.js"}

    def dashboard(self):
        return self._result("dashboard.html")

    def engine(self, engine_label):
        engine = self.handler.capsul.engine(engine_label)
        if engine:
            return self._result("engine.html", engine=engine)

    def execution(self, engine_label, execution_id):
        return self._result(
            "execution.html", engine_label=engine_label, execution_id=execution_id
        )


class CapsulBackend(WebBackend):
    def engines(self) -> list:
        return [engine.engine_status() for engine in Capsul().engines()]

    def engine_status(self, engine_label: str) -> dict:
        try:
            engine = Capsul().engine(engine_label)
        except ValueError:
            return {}
        return engine.engine_status()

    def executions_summary(self, engine_label: str) -> list:
        return Capsul().engine(engine_label).executions_summary()

    def execution_report(self, engine_label: str, execution_id: str) -> dict:
        with Capsul().engine(engine_label) as engine:
            return engine.database.execution_report_json(engine.engine_id, execution_id)
