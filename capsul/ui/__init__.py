# -*- coding: utf-8 -*-

from capsul.api import Capsul
from capsul.web import WebRoutes, WebBackend

from soma.qt_gui.qt_backend import Qt


class CapsulRoutes(WebRoutes):
    _templates = {
        'qt_backend.js',
        'html_backend.js'
    }
    def dashboard(self):
        return self._result('dashboard.html')



    def engine(self, engine_id):
        engine = self.handler.capsul.engine(engine_id)
        if engine:
            return self._result('engine.html', engine=engine)


class CapsulBackend(WebBackend):
    def engines(self) -> list:
        return [engine.engine_status() for engine in Capsul().engines()]
