# -*- coding: utf-8 -*-
from .info import __version__

_doc_path = None

def _init_doc_path():
    global _doc_path
    import capsul
    import os
    from .info import version_major
    from .info import version_minor

    p = os.path.dirname(os.path.dirname(capsul.__file__))
    doc_path = os.path.join(p, 'doc/build/html')
    if os.path.exists(doc_path):
        _doc_path = doc_path
        return _doc_path

    # use soma/brainvisa_share
    import soma.config
    p2 = os.path.join(
        os.path.dirname(soma.config.BRAINVISA_SHARE),
        'doc/capsul-%d.%d' % (version_major, version_minor))
    if os.path.exists(p2):
        _doc_path = p2
        return _doc_path
    _doc_path = 'https://populse.github.io/capsul'
    return _doc_path

_init_doc_path()
