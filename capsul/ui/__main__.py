# -*- coding: utf-8 -*-
import sys
from soma.qt_gui.qt_backend import Qt

from capsul.web import CapsulBrowserWindow


import http, http.server
from capsul.web import CapsulHTTPHandler


class Handler(CapsulHTTPHandler, base_url="http://localhost:8080"):
    pass


httpd = http.server.HTTPServer(("", 8080), Handler)
httpd.serve_forever()


app = Qt.QApplication(sys.argv)
w = CapsulBrowserWindow()
w.show()
app.exec_()
