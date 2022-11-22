# -*- coding: utf-8 -*-

import http, http.server
import sys

from capsul.web import CapsulHTTPHandler, CapsulBrowserWindow

from soma.qt_gui.qt_backend import Qt


    

# httpd = http.server.HTTPServer(('', 8080), CapsulHTTPHandler)
# httpd.serve_forever()

app = Qt.QApplication(sys.argv)
w = CapsulBrowserWindow()
w.browser.page()._load_template('dashboard')
w.show()
app.exec_()
