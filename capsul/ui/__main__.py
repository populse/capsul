# -*- coding: utf-8 -*-

from ..api import Capsul
from . import CapsulRoutes, CapsulBackend

# Parameters common to Qt and Web server handlers
handler_kwargs = dict(
    routes=CapsulRoutes(),
    backend=CapsulBackend(),
    static='capsul.ui',
    templates='capsul.ui',
    capsul=Capsul(),
    title='Capsul'
)

def web_server_gui():
    import http, http.server
    from soma.web import SomaHTTPHandler

    class Handler(SomaHTTPHandler, base_url='http://localhost:8080', **handler_kwargs):
        pass
    httpd = http.server.HTTPServer(('', 8080), Handler)
    httpd.serve_forever()

def qt_web_gui():
    import sys
    from soma.qt_gui.qt_backend import Qt
    from soma.web import SomaBrowserWindow
    
    app = Qt.QApplication(sys.argv)
    w = SomaBrowserWindow(
        starting_url='soma://dashboard',
        window_title='Capsul dashboard',
        **handler_kwargs
    )
    w.showMaximized()
    app.exec_()

qt_web_gui()
