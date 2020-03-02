# -*- coding: utf-8 -*-

# runprocess can be called with 'python -m capsul' or 'python -m capsul.run'.
# The latter was introduced for compatibility with older versions of Python
# (before 2.7), which did not recognize __main__.py.

from .process import runprocess
runprocess.main()
