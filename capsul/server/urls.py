import datetime
import importlib

from django.urls import path
from django.shortcuts import render
from django.core.exceptions import PermissionDenied

from . import settings


class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        capsul_token = request.GET.get("capsul_token", None)
        if capsul_token:
            get = request.GET.copy()
            del get["capsul_token"]
            request.GET = get
            cookies = request.COOKIES.copy()
            cookies["capsul_token"] = capsul_token
            request.COOKIES = cookies
        response = self.get_response(request)
        if capsul_token:
            response.set_cookie(
                "capsul_token", capsul_token, max_age=datetime.timedelta(days=1)
            )
        return response


class TestToolbox:
    launcher_html = '<h2><a href="test">Test {{url("home")}}</a>'


def render_string(text, context):
    """Render a string with Jinja2 using the same context as for a request"""

    env_path = settings.TEMPLATES[0]["OPTIONS"]["environment"]
    module_path, func_name = env_path.rsplit(".", 1)
    env_module = importlib.import_module(module_path)
    env = getattr(env_module, func_name)()
    template = env.from_string(text)
    return template.render(context)


def home(request):
    capsul_token = request.COOKIES.get("capsul_token")
    print(repr(capsul_token), "==?", repr(settings.SECRET_KEY))
    if capsul_token != settings.SECRET_KEY:
        raise PermissionDenied()

    toolboxes = [
        {"launcher_html": render_string(t.launcher_html, {}) for t in [TestToolbox]}
    ]
    return render(request, "home.html", {"title": "Capsul", "toolboxes": toolboxes})


urlpatterns = [
    path("", home, name="home"),
]
