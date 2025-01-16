import os
import sys

from ..api import Capsul
from . import CapsulWebBackend

# Parameters common to Qt and Web server handlers
web_backend = CapsulWebBackend(capsul=Capsul())


def web_server_gui():
    import http
    import http.server

    from soma.web import SomaHTTPHandler

    class Handler(SomaHTTPHandler, web_backend=web_backend):
        pass

    httpd = http.server.HTTPServer(("", 8080), Handler)
    httpd.serve_forever()


def qt_web_gui():
    import sys

    from soma.qt_gui.qt_backend import Qt
    from soma.web import SomaBrowserWidget

    s = os.path.split(os.path.dirname(__file__)) + ("static",)
    starting_url = f"file://{'/'.join(s)}/dashboard.html"
    app = Qt.QApplication(sys.argv)
    w = SomaBrowserWidget(
        starting_url=starting_url,
        web_backend=web_backend,
    )
    w.show()
    app.exec_()


if len(sys.argv) < 2 or sys.argv[1] == "qt":
    qt_web_gui()
else:
    web_server_gui()
