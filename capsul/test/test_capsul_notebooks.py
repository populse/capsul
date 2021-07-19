# -*- coding: utf-8 -*-
from __future__ import print_function

from __future__ import absolute_import
import os
import sys
import glob
import capsul

# jupyter nbconvert import
try:
    import nbformat
    from jupyter_core.command import main as main_jupyter
except ImportError:
    raise ImportError('cannot import nbformat and/or jupyter_core.command: '
                      'cannot test notebooks')

from soma.test_utils import test_notebook as tnb


def test():
    os.environ["ALLOW_GUI"] = "FALSE"
    root_dir = os.environ.get('CAPSUL_SOURCE_DIR', None)
    if root_dir is None:
        root_dir = os.path.dirname(capsul.__path__[0])
    root_dir = os.path.abspath(root_dir)
    nb_dir = os.path.join(root_dir, 'doc', 'source', '_static', 'tutorial')
    notebooks = glob.glob(os.path.join(nb_dir, '*.ipynb'))
    print('notebooks:', notebooks)
    res = True
    for notebook in notebooks:
        res = tnb.test_notebook(notebook)
    if res:
        print('OK')
    else:
        print('FAILURE')
    return res

if __name__ == '__main__':
    r = test()
    if r:
        res = 0
    else:
        res = 1
    print("RETURNCODE: ", res)
    sys.exit(res)
