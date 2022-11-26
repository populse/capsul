# -*- coding: utf-8 -*-
import importlib
import json
import http, http.server
import mimetypes
import os

import jinja2

from soma.qt_gui.qt_backend import Qt, QtWidgets
from soma.qt_gui.qt_backend.QtCore import pyqtSlot, QUrl, QBuffer, QIODevice
from soma.qt_gui.qt_backend.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from soma.qt_gui.qt_backend.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineUrlScheme, QWebEngineUrlRequestJob
from soma.qt_gui.qt_backend.QtWebChannel import QWebChannel


class WebRoutes:
    def _result(self, template, **kwargs):
        return (template, kwargs)



def backend_decorator(function):
    args = [type for name, type in function.__annotations__.items() if name != 'return']
    return_type = function.__annotations__.get('return')
    if return_type:
        result = pyqtSlot(*args, result=return_type)(function)
    else:
        result = pyqtSlot(*args)(function)
    result._params = [name for name in function.__annotations__ if name != 'return']
    result._return = return_type
    return result


class WebBackendMeta(type(Qt.QObject)):
    def __new__(cls, name, bases, dict):
        for k, v in dict.items():
            if callable(v) and v.__annotations__:
                dict[k] = backend_decorator(v)
        return super().__new__(cls, name, bases, dict)


class WebBackend(Qt.QObject, metaclass=WebBackendMeta):
    pass


class WebHandler:
    def __init__(self, capsul, base_url, server_type, routes, backend=None, static=None, **kwargs):
        self.routes = routes
        routes.handler = self
        self.backend = backend
        m = importlib.import_module('capsul.web')
        self.static_directory = os.path.join(os.path.dirname(m.__file__), 'static')
        self.jinja = kwargs
        self.capsul = self.jinja['capsul'] = capsul
        self.base_url = self.jinja['base_url'] = base_url 
        self.server_type = self.jinja['server_type'] = server_type


    def resolve(self, path, *args):
        if path:
            if path[0] == '/':
                path = path[1:]
            paths = path.split('/')
            name = paths[0]
            path_args = paths[1:]

            if name in self.routes._templates and not path_args:
                return (name, self.jinja)
            method = getattr(self.routes, name, None)
            if method:
                template, kwargs = method(*(tuple(path_args) + args))
                kwargs.update(self.jinja)
                return (template, kwargs)
            if path.startswith('backend/') and self.backend:
                name = path[8:]
                method = getattr(self.backend, name, None)
                if method:
                    return method(*args)
            elif path.startswith('static/') and self.static_directory:
                path = path[7:]
                return (os.path.join(self.static_directory, path), None)
        raise ValueError('Invalid path')


class CapsulHTTPHandlerMeta(type(http.server.BaseHTTPRequestHandler)):
    def __new__(cls, name, bases, dict, capsul=None, base_url=None, routes=None, backend=None, static=None):
        if name != 'CapsulHTTPHandler':
            l = locals()
            missing = [i for i in ('capsul', 'base_url', 'routes') if l.get(i) is None]
            if missing:
                raise TypeError(f'CapsulHTTPHandlerMeta.__new__() missing {len(missing)} required positional arguments: {", ".join(missing)}')
            backend_methods = {}
            for attr in backend.__class__.__dict__:
                if attr.startswith('_'):
                    continue
                backend_methods[attr] = getattr(backend.__class__, attr)
            dict['_handler'] = WebHandler(
                server_type='http',
                capsul=capsul,
                base_url=base_url,
                routes=routes, 
                backend=backend,
                static=static,
                backend_methods=backend_methods)
        return super().__new__(cls, name, bases, dict)



class CapsulHTTPHandler(http.server.BaseHTTPRequestHandler, metaclass=CapsulHTTPHandlerMeta):
    def __init__(self, request, client_address, server):
        self.jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.web'),
            autoescape=jinja2.select_autoescape()
        )
        super().__init__(request, client_address, server)


    def do_GET(self):
        # Read JSON body if any
        if self.headers.get('Content-Type') == 'application/json':
            length = int(self.headers.get('Content-Length'))
            if length:
                args = json.loads(self.rfile.read(length))
        else:
            args = []
        path = self.path.split('?',1)[0]
        path = path.split('#',1)[0]
        try:
            template_data = self._handler.resolve(path, *args)
        except ValueError as e:
            self.send_error(400, str(e))
            return None
        except Exception as e:
            self.send_error(500, str(e))
            raise
            return None
        
        header = {}
        if template_data is None:
            body = None
        elif isinstance(template_data, tuple):
            template, data = template_data
            if data is None:
                try:
                    s = os.stat(template)
                except FileNotFoundError:
                    self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")
                    return None
                f, extension = os.path.splitext(template)
                mime_type = mimetypes.types_map.get(extension, 'text/plain')
                header['Content-Type'] = mime_type
                header['Last-Modified'] = self.date_time_string(os.stat(template).st_mtime)
                body = open(template).read()
            else:
                try:
                    template = self.jinja.get_template(template)
                except jinja2.TemplateNotFound:
                    self.send_error(http.HTTPStatus.NOT_FOUND, "Template not found")
                    return None
                header['Content-Type'] = 'text/html'
                header['Last-Modified'] = self.date_time_string(os.stat(template.filename).st_mtime)
                body = template.render(**data)
        else:
            header['Content-Type'] = 'application/json'
            body = json.dumps(template_data)
        
        self.send_response(http.HTTPStatus.OK)
        # The following line introduces a security issue by allowing any 
        # site to use the backend. But this is a demo only server.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST')
        self.send_header('Access-Control-Allow-HEADERS', 'Content-Type')
        for k, v in header.items():
            self.send_header(k, v)

        if body is not None:
            body = body.encode('utf8')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_OPTIONS(self):
        # The following line introduces a security issue by allowing any 
        # site to use the backend. But this is a demo only server.
        self.send_response(http.HTTPStatus.OK)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST')
        self.send_header('Access-Control-Allow-HEADERS', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        return self.do_GET()


class CapsulSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, parent, capsul, routes, backend):
        super().__init__(parent)
        self._jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.web'),
            autoescape=jinja2.select_autoescape()
        )
        self._handler = WebHandler(
            capsul=capsul,
            base_url='capsul://',
            server_type='qt',
            routes=routes,
            backend=backend)

    def requestStarted(self, request):
        url = request.requestUrl()
        path = url.toString()[9:]

        try:
            template_data = self._handler.resolve(path)
        except ValueError as e:
            request.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return None
        except Exception as e:
            request.fail(QWebEngineUrlRequestJob.Failed)
            return None
        body = None
        if template_data:
            template, data = template_data
            if data is None:
                body = open(template).read()
            else:
                try:
                    template = self._jinja.get_template(template)
                except jinja2.TemplateNotFound:
                    return False
                body = template.render(**data)

        if isinstance(body, str):
            body = body.encode('utf8')
        buf = QBuffer(parent=self)
        request.destroyed.connect(buf.deleteLater)
        buf.open(QIODevice.WriteOnly)
        buf.write(body)
        buf.seek(0)
        buf.close()
        mime_type = mimetypes.guess_type(path)[0]
        if mime_type is None:
            mime_type = 'text/html'
        request.reply(mime_type.encode(), buf)


class CapsulBrowserWindow(QtWidgets.QMainWindow):
    def __init__(self, starting_route, capsul, routes, backend):
        super(QtWidgets.QMainWindow, self).__init__()
        if not QWebEngineUrlScheme.schemeByName(b'capsul').name():
            scheme = QWebEngineUrlScheme(b'capsul')
            scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
            QWebEngineUrlScheme.registerScheme(scheme)

            profile = QWebEngineProfile.defaultProfile()
            capsul.url_scheme_handler = CapsulSchemeHandler(None, capsul=capsul, routes=routes, backend=backend)
            profile.installUrlSchemeHandler(b'capsul', capsul.url_scheme_handler)


        self.browser = QWebEngineView()

        self.channel = QWebChannel()
        self.channel.registerObject('backend', capsul.url_scheme_handler._handler.backend)
        self.browser.page().setWebChannel(self.channel)
        self.setCentralWidget(self.browser)
        if starting_route:
            self.browser.setUrl(QUrl(starting_route))
