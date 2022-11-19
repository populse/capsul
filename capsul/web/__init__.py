# -*- coding: utf-8 -*-
import inspect
import json
import http, http.server
import os

import jinja2

from soma.qt_gui.qt_backend import Qt, QtWidgets
from soma.qt_gui.qt_backend.QtCore import pyqtSlot, QUrl
from soma.qt_gui.qt_backend.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from soma.qt_gui.qt_backend.QtWebChannel import QWebChannel

from capsul.api import Capsul


class WebRoutes:
    def __init__(self, base_url='capsul://', server_type='qt', backend=None):
        self.capsul = Capsul()
        self.base_url = base_url
        self.server_type = server_type
        self._backend = backend
    

    def _result(self, template, **kwargs):
        kwargs['capsul'] = self.capsul
        kwargs['base_url'] = self.base_url
        kwargs['server_type'] = self.server_type
        if self._backend:
            cls = self._backend.__class__
            backends = {}
            for attr in cls.__dict__:
                if attr.startswith('_'):
                    continue
                backends[attr] = getattr(cls, attr)
            kwargs['backends'] = backends
        return (template, kwargs)


    def _resolve(self, path):
        if path:
            if path[0] == '/':
                path = path[1:]
            paths = path.split('/')
            if paths:
                name = paths[0]
                args = paths[1:]
                method = getattr(self, name, None)
                if method:
                    return method(*args)
                if name == 'backend' and self._backend and args:
                    name = args[0]
                    args = args[1:]
                    method = getattr(self._backend, name)
                    if method:
                        result = method(*args)
                        if result is None:
                            return 'none'
                        else:
                            return result

    def dashboard(self):
        return self._result('dashboard.html')



    def engine(self, engine_id):
        engine = self.capsul.engine(engine_id)
        if engine:
            return self._result('engine.html', engine=engine)

def backend(function):
    args = [type for name, type in function.__annotations__.items() if name != 'return']
    return_type = function.__annotations__.get('return')
    if return_type:
        result = pyqtSlot(*args, result=return_type)(function)
    else:
        result = pyqtSlot(*args)(function)
    result._params = [name for name in function.__annotations__ if name != 'return']
    result._return = return_type
    return result

class WebBackend(Qt.QObject):
    @backend
    def print(self, text: str):
        print('python:', text)

    @backend
    def hello(self, text: str) -> str:
        return f'Hello, {text} !'

class CapsulHTTPHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.web'),
            autoescape=jinja2.select_autoescape()
        )
        host, port = server.server_address
        if not host:
            host = 'localhost'
        base_url = f'http://{host}:{port}'
        self.routes = WebRoutes(base_url=base_url, server_type='http', backend=WebBackend())
        super().__init__(request, client_address, server)


    def send_head(self):
        # abandon query parameters
        path = self.path.split('?',1)[0]
        path = path.split('#',1)[0]
        template_data = self.routes._resolve(path)
        header = {}
        if template_data is None:
            self.send_error(http.HTTPStatus.NOT_FOUND, "Page not found")
            return None
        elif isinstance(template_data, tuple):
            template, data = template_data
            try:
                template = self.jinja.get_template(template)
            except jinja2.TemplateNotFound:
                self.send_error(http.HTTPStatus.NOT_FOUND, "Template not found")
                return None
            header['Content-type'] = 'text/html'
            header['Last-Modified'] = self.date_time_string(os.stat(template.filename).st_mtime)
            body = template.render(**data)
        else:
            header['Content-type'] = 'application/json'
            header['Access-Control-Allow-Origin'] = '*'
            body = json.dumps(template_data)
        
        self.send_response(http.HTTPStatus.OK)
        for k, v in header.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return body


    def do_GET(self):
        f = self.send_head()
        if f is not None:
           self.wfile.write(f.encode('utf8'))


    def do_HEAD(self):
        self.send_head()


class CapsulWebPage(QWebEnginePage):
    def __init__(self, *args):
        super().__init__(*args)
        self._jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.web'),
            autoescape=jinja2.select_autoescape()
        )
        self._routes = WebRoutes()
        self._backend = WebBackend()
        
    def _load_template(self, path):
        template_data = self._routes._resolve(path)
        if template_data:
            template, data = template_data
            try:
                template = self._jinja.get_template(template)
            except jinja2.TemplateNotFound:
                return False
            html = template.render(**data)
            self.setHtml(html, QUrl(f'capsul://{path}'))


    def acceptNavigationRequest(self, url,  _type, isMainFrame):
        if url.scheme() == 'capsul':
            self._load_template(f'{url.host()}{url.path()}')
            return False
        return super().acceptNavigationRequest(url,  _type, isMainFrame)


class CapsulWebEngineView(QWebEngineView):
    def createWindow(self, wintype):
        w = super().createWindow(wintype)
        if not w:
            try:
                self.source_window = CapsulBrowserWindow()
                self.source_window.show()
                w = self.source_window.browser
            except Exception as e:
                print('ERROR: Cannot create browser window:', e)
                w = None
        return w


class CapsulBrowserWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.browser = CapsulWebEngineView()

        self.channel = QWebChannel()
        page = CapsulWebPage(self)
        self.channel.registerObject('backend', page._backend)
        self.browser.setPage(page)
        self.browser.page().setWebChannel(self.channel)
        self.setCentralWidget(self.browser)
