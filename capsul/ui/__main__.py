# -*- coding: utf-8 -*-

import os
from ..api import Capsul
from . import CapsulWebBackend

# Parameters common to Qt and Web server handlers
handler_kwargs = dict(
    web_backend=CapsulWebBackend(capsul=Capsul()),
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
    from soma.web import SomaBrowserWidget
    
    s = os.path.split(os.path.dirname(__file__)) + ('static',)
    starting_url = f'file://{"/".join(s)}/dashboard.html'
    app = Qt.QApplication(sys.argv)
    w = SomaBrowserWidget(
        starting_url=starting_url,
        **handler_kwargs
    )
    w.static_path.append("/".join(s))
    w.showMaximized()
    app.exec_()

qt_web_gui()
