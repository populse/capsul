# -*- coding: utf-8 -*-

import http, http.server
import sys

from capsul.web import WebRoutes, WebBackend, CapsulBrowserWindow, CapsulHTTPHandler
from capsul.api import Capsul

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
    def print(self, text: str):
        print('python:', text)


    def hello(self, text: str) -> str:
        return f'Hello, {text} !'

routes = CapsulRoutes()
backend = CapsulBackend()
capsul=Capsul()


class Handler(CapsulHTTPHandler,
    base_url='http://localhost:8080',
    capsul=capsul,
    routes=routes,
    backend=backend):
    pass
# httpd = http.server.HTTPServer(('', 8080), Handler)
# httpd.serve_forever()


app = Qt.QApplication(sys.argv)
w = CapsulBrowserWindow(
    starting_route='capsul:///dashboard',
    capsul=capsul,
    routes=routes,
    backend=backend)
w.show()
app.exec_()
