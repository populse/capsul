import importlib.metadata
import re

try:
    __release__ = importlib.metadata.version("capsul")
except importlib.metadata.PackageNotFoundError:
    __release__ = None

if __release__:
    __version__ = re.match(r"(\d+\.\d+\.\d+)[^.\d]*", __release__).group(1)
else:
    __version__ = None

_doc_path = None

application_name = "capsul"
organization_name = "populse"

def _init_doc_path():
    global _doc_path
    import os

    import capsul

    short_version = ".".join(__version__.split(".")[:2])

    p = os.path.dirname(os.path.dirname(capsul.__file__))
    doc_path = os.path.join(p, "doc/build/html")
    if os.path.exists(doc_path):
        _doc_path = doc_path
        return _doc_path

    # use soma/brainvisa_share
    import soma.config

    p2 = os.path.join(
        os.path.dirname(soma.config.BRAINVISA_SHARE),
        f"doc/capsul-{short_version}",
    )
    if os.path.exists(p2):
        _doc_path = p2
        return _doc_path
    _doc_path = "https://populse.github.io/capsul"
    return _doc_path


_init_doc_path()
