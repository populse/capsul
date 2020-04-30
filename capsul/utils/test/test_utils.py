# -*- coding: utf-8 -*-
# System import
from __future__ import absolute_import
import unittest
import six
import sys


# Trait import
from traits.api import Float, CTrait, File, Directory
from traits.api import Undefined

# Soma import
from soma.controller.trait_utils import (
    get_trait_desc, is_trait_value_defined, is_trait_pathname,
    trait_ids)

# Capsul import
import capsul
from capsul.utils.version_utils import get_tool_version
from capsul.utils.version_utils import get_nipype_interfaces_versions


class TestUtils(unittest.TestCase):
    """ Class to test the utils function.
    """

    def test_version_python(self):
        """ Method to test if we can get a python module version from
        its string description and the nipype insterfaces versions.
        """
        self.assertEqual(capsul.__version__, get_tool_version("capsul"))
        self.assertEqual(get_tool_version("error_capsul"), None)

    def test_version_interfaces(self):
        """ Method to test if we can get the nipype interfaces versions.
        """
        interface_version = get_nipype_interfaces_versions()
        self.assertTrue(interface_version is None or
                        isinstance(interface_version, dict))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
