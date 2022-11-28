# -*- coding: utf-8 -*-
import sys
from soma.qt_gui.qt_backend import Qt

from capsul.api import Capsul
from capsul.ui import CapsulRoutes, CapsulBackend
from capsul.web import CapsulBrowserWindow

routes = CapsulRoutes()
backend = CapsulBackend()
capsul=Capsul()


# import http, http.server
# from capsul.web import CapsulHTTPHandler
# class Handler(CapsulHTTPHandler,
#     base_url='http://localhost:8080',
#     capsul=capsul,
#     routes=routes,
#     backend=backend):
#     pass
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
