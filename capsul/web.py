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
    '''
    Class derived from `WebRoutes` are used to define the routes that will be
    available to the GUI browser (that is either a Qt widget or a real web
    browser). Each method define in the derived class will add a route (an URL
    that will be recognized by the browser). Each method must return an HTML
    document templated with Jinja2 using `return self._result(filename)` where
    `filename` is a path relative to the `templates` folder of the `capsul.ui`
    module.

    Derived class can also define a `_template` set containing paths (relative
    to `templates` directory of `capsul.ui` module). Each path will be added
    as a valid web route displaying the result of Jinja2 on this file (the
    `Content-Type` of the file is guessed from the filename extension).

    The following Jinja2 template parameters are always set:
    - `capsul`: the instance of Capsul application.
    - `base_url`: prefix to build any URL in template. For instance to create
      a link to a route corresponding to a method in this class, one should
      use: `<a href="{{base_url}}/method_name">the link</a>`.
    - `server_type`: a string containing either `qt` if the browser is a
       serverless Qt widget or `html` for a real browser with an HTTP server.
    For instance, let's consider that the base URL of the GUI is `capsul://`, 
    the following definition declares four routes: 
    
    - `capsul:///qt_backend.js`: using the result of 
      `{capsul.ui directory}/templates/qt_backend.js` send to Jinja2.
    - `capsul:///html_backend.js`: using the result of 
      `{capsul.ui directory}/templates/html_backend.js` send to Jinja2.
    - `capsul:///dashboard`: calling `dahsboard()` method.
    - `capsul:///engine/{engine_id}`. calling `engine(engine_id) method.

    ```
    from capsul.web import WebRoutes

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
    ```

    '''
    def _result(self, template, **kwargs):
        '''
        Return a valid result value that is passed to the `WebHandler` and
        will be interpreted as: an HTML page whose the result of a Jinja2
        template using builtin variables and those given in parameters.
        '''
        return (template, kwargs)



def backend_decorator(function):
    '''
    Used internally in `WebBackend` metaclass.
    '''


class WebBackendMeta(type(Qt.QObject)):
    '''
    `WebBackend` metaclass. Analyses all methods declared by `WebBackend`
    subclasses. Those using annotations are considered as valid API routes.
    Valid API routes are transformed in PyQt slots to be recognized by
    `QWebChannel` and some attributes are added to quickly list their
    parameters and return value type.
    '''
    def __new__(cls, name, bases, dict):
        for k, v in dict.items():
            if callable(v) and v.__annotations__:
                args = [type for name, type in v.__annotations__.items() if name != 'return']
                return_type = v.__annotations__.get('return')
                if return_type:
                    result = pyqtSlot(*args, result=Qt.QVariant)(v)
                else:
                    result = pyqtSlot(*args)(v)
                result._params = [name for name in v.__annotations__ if name != 'return']
                result._return = return_type
                dict[k] = result
        return super().__new__(cls, name, bases, dict)


class WebBackend(Qt.QObject, metaclass=WebBackendMeta):
    '''
    Base class to declare routes correponding to JSON backend API. Each method
    in derived class that has annotations can be called from the client browser
    using JavaScript. In all web pages, a `backend` global variable is
    declared. This Javascript object contains one method for each `WebBackend`
    method. The calling of these methods is Javascript is done as if using a Qt
    QWebChannel. But, in case of a real browser with a HTML server, an Ajax
    call to the server (using Javascript `fetch()` function) will be performed. 

    A method without return value can be called directly:
    ```
    backend.a_method_without_return(parameter1, parameter2);
    ```

    When there is a return value, a callback function must be given as last
    parameter. This function will be called with the method's result as last
    parameter:
    ```
    backend.a_method_with_return(parameter1, parameter2, (result) => { ... });
    ```

    Methods can return anything that can be serialized using `json.dumps()`.
    '''


class WebHandler:
    '''
    This class puts together the various objects and parameters necessary to
    answer to all browser queries. 
    '''

    def __init__(self, capsul, base_url, server_type, routes, backend, 
                 static, **kwargs):
        '''
        Creates a handler for handling any browser requests. This class is
        build and used internally by Qt or HTML server implementations.

        Parameters
        ----------
        capsul: Capsul
            Capsul instance passed to Jinja2 templates.
        base_url: str
            URL prefix passed to Jinja2 templates and used to create links.
        server_type: str
            Either `'qt'` for browser using serverless QWebEngine or `'html'`
            for real web browser using an http server.
        routes: :class:`WebRoutes`
            Defines routes that will be available to browser to display HTML
            content to the user. These routes are exposed as 
            `{{base_url}}/method_name`.
        backend: :class:`WebBackend`
            Defines routes that are avalaible as a JSON API backend. These
            routes are exposed as `{{base_url}}/backend/method_name`.
        static: str
            A module name containing a `static` directory whose content will
            be exposed. If `None` is given, the default value `'capsul.ui'` is
            used. These files are exposed as `{{base_url}}/static/file_name`.
        kwargs: dict
            All supplementary keyword parameter will be passed to every Jinja2
            templates.
        '''
        if static is None:
            static = 'capsul.ui'
        self.routes = routes
        routes.handler = self
        self.backend = backend
        m = importlib.import_module(static)
        self.static_directory = os.path.join(os.path.dirname(m.__file__), 'static')
        self.jinja = kwargs
        self.capsul = self.jinja['capsul'] = capsul
        self.base_url = self.jinja['base_url'] = base_url 
        self.server_type = self.jinja['server_type'] = server_type


    def resolve(self, path, *args):
        '''
        Main method used to forge a reply to a browser request.

        Parameters
        ----------
        path: str
            path extracted from the request URL. If the URL path contains
            several / separated elements, this parameter only contains the 
            first one. The others are passed in `args`.
        args: list[str]
            List of parameters extracted from URL path. These parameters are
            passed to the method correponding to `path`.
        
        '''
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
    '''
    Python standard HTTP server needs a handler class. This metaclass
    allows to instanciate this class with parameters required to
    build a :class:`WebHandler`.
    '''
    def __new__(cls, name, bases, dict, capsul=None, base_url=None,
                routes=None, backend=None, static=None):
        if name != 'CapsulHTTPHandler':
            l = locals()
            missing = [i for i in ('base_url',) if l.get(i) is None]
            if missing:
                raise TypeError(f'CapsulHTTPHandlerMeta.__new__() missing {len(missing)} required positional arguments: {", ".join(missing)}')
            if capsul is None:
                from capsul.api import Capsul
                capsul = Capsul()
            if routes is None:
                from capsul.ui import CapsulRoutes
                routes = CapsulRoutes()
            if backend is None:
                from capsul.ui import CapsulBackend
                backend = CapsulBackend()
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
    '''
    Base class to create a handler in order to implement a proof-of-concept
    http server for Capsul GUI. This class must be used only for demo, debug
    or tests. It must not be used in production. Here is an example of server
    implementation:

    ::

        import http, http.server

        from capsul.api import Capsul
        from capsul.ui import CapsulRoutes, CapsulBackend
        from capsul.web import CapsulHTTPHandler

        routes = CapsulRoutes()
        backend = CapsulBackend()
        capsul=Capsul()

        class Handler(CapsulHTTPHandler, base_url='http://localhost:8080',
                    capsul=capsul, routes=routes, backend=backend):
            pass

        httpd = http.server.HTTPServer(('', 8080), Handler)
        httpd.serve_forever()
    '''
    
    def __init__(self, request, client_address, server):
        self.jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.ui'),
            autoescape=jinja2.select_autoescape()
        )
        super().__init__(request, client_address, server)


    def do_GET(self):
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
                _, extension = os.path.splitext(template)
                mime_type = mimetypes.types_map.get(extension, 'text/plain')
                header['Content-Type'] = mime_type
                header['Last-Modified'] = self.date_time_string(os.stat(template).st_mtime)
                body = open(template).read()
            else:
                _, extension = os.path.splitext(template)
                mime_type = mimetypes.types_map.get(extension, 'text/html')
                try:
                    template = self.jinja.get_template(template)
                except jinja2.TemplateNotFound:
                    self.send_error(http.HTTPStatus.NOT_FOUND, "Template not found")
                    return None
                header['Content-Type'] = mime_type
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
    '''
    In Qt implementation of Capsul GUI, all internal links uses the scheme
    'capsul'. For instance, the dashboard page URL is capsul:///dashboard.
    A :class:`CapsulSchemeHandler` is installed to process these URL and
    return appropriate content using a :class:̀ WebHandler`.
    '''
    def __init__(self, parent, capsul, routes, backend):
        super().__init__(parent)
        self._jinja = jinja2.Environment(
            loader=jinja2.PackageLoader('capsul.ui'),
            autoescape=jinja2.select_autoescape()
        )
        self._handler = WebHandler(
            capsul=capsul,
            base_url='capsul://',
            server_type='qt',
            routes=routes,
            backend=backend,
            static=None)

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


class CapsulWebEngineView(QWebEngineView):
    '''
    Reimplements :meth:`CapsulWebEngineView.createWindow` to allow the browser
    to open new windows.
    '''
    def createWindow(self, wintype):
        w = super().createWindow(wintype)
        if not w:
            try:
                parent = self.parent()
                self.source_window = CapsulBrowserWindow(
                    starting_url = parent.starting_url,
                    capsul = parent.capsul,
                    routes = parent.routes,
                    backend = parent.backend,
                )
                self.source_window.show()
                w = self.source_window.browser
            except Exception as e:
                print('ERROR: Cannot create browser window:', e)
                w = None
        return w


class CapsulBrowserWindow(QtWidgets.QMainWindow):
    '''
    Top level widget to display Capsul GUI in Qt.

    ::

        import sys
        from soma.qt_gui.qt_backend import Qt
        from capsul.web import CapsulBrowserWindow

        app = Qt.QApplication(sys.argv)
        w = CapsulBrowserWindow()
        w.show()
        app.exec_()

    '''
    def __init__(self, starting_url='capsul://dashboard', 
                 capsul=None, routes=None, backend=None):
        super(QtWidgets.QMainWindow, self).__init__()
        if capsul is None:
            from capsul.api import Capsul
            capsul = Capsul()
        if routes is None:
            from capsul.ui import CapsulRoutes
            routes = CapsulRoutes()
        if backend is None:
            from capsul.ui import CapsulBackend
            backend = CapsulBackend()
        self.setWindowTitle(capsul.label)
        self.starting_url = starting_url
        self.capsul = capsul
        self.routes = routes
        self.backend = backend
        if not QWebEngineUrlScheme.schemeByName(b'capsul').name():
            scheme = QWebEngineUrlScheme(b'capsul')
            scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
            QWebEngineUrlScheme.registerScheme(scheme)

            profile = QWebEngineProfile.defaultProfile()
            capsul.url_scheme_handler = CapsulSchemeHandler(None, capsul=capsul, routes=routes, backend=backend)
            profile.installUrlSchemeHandler(b'capsul', capsul.url_scheme_handler)


        self.browser = CapsulWebEngineView()

        self.channel = QWebChannel()
        self.channel.registerObject('backend', capsul.url_scheme_handler._handler.backend)
        self.browser.page().setWebChannel(self.channel)
        self.setCentralWidget(self.browser)
        self.browser.iconChanged.connect(self.set_icon)
        if starting_url:
            self.browser.setUrl(QUrl(starting_url))

    def set_icon(self):
        self.setWindowIcon(self.browser.icon())
