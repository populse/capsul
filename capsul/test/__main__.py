# -*- coding: utf-8 -*-

from __future__ import absolute_import

from importlib import import_module
import os
import unittest


def load_tests(loader, standard_tests, pattern):
    """
    Prepares the tests parameters

    :param loader:

    :param standard_tests:

    :param pattern:

    :return: A test suite
    """
    suite = unittest.TestSuite()
    
    base = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    for root, dirs, files in os.walk(base):
        if '__init__.py' not in files:
            continue
        for f in files:
            if f.startswith('test_') and f.endswith('.py'):
                module_name = 'capsul.%s' % (root[len(base)+1:].replace(os.path.sep, '.') + '.' + f[:-3])   
                try:
                    module = import_module(module_name)
                    import_error = None
                except ImportError as e:
                    module = None
                    import_error = str(e)
                if import_error:
                    print('ERROR [%s]: %s' % (module_name, import_error))
                else:
                    for name in dir(module):
                        item = getattr(module, name)
                        if isinstance(item, type) and issubclass(item, unittest.TestCase):
                            suite.addTests(loader.loadTestsFromTestCase(item))
    return suite


if __name__ == '__main__':
    unittest.main()
