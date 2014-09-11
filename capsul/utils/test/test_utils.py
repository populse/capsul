#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest

# Trait import
from traits.api import Float, CTrait, File, Directory
from traits.trait_base import _Undefined

# Soma import
from soma.controller import trait_ids

# Capsul import
import capsul
from capsul.utils import get_tool_version, get_nipype_interfaces_versions
from capsul.utils.trait_utils import (
    get_trait_desc, is_trait_value_defined, is_trait_pathname,
    clone_trait)
from capsul.utils.loader import load_objects


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
        self.assertTrue(get_nipype_interfaces_versions() in [{}, None])

    def test_trait_string_description(self):
        """ Method to test if we can build a string description for a trait.
        """
        trait = CTrait(0)
        trait.handler = Float()
        trait.ouptut = False
        trait.optional = True
        trait.desc = "bla"
        manhelp = get_trait_desc("float_trait", trait, 5)
        self.assertEqual(
            manhelp[0],
            "float_trait: a float (['Float'] - optional, default value: 5)")
        self.assertEqual(manhelp[1], "    bla")

    def test_trait(self):
        """ Method to test trait characterisitics: value, type.
        """
        self.assertTrue(is_trait_value_defined(5))
        self.assertFalse(is_trait_value_defined(""))
        self.assertFalse(is_trait_value_defined(None))
        self.assertFalse(is_trait_value_defined(_Undefined()))

        trait = CTrait(0)
        trait.handler = Float()
        self.assertFalse(is_trait_pathname(trait))
        for handler in [File(), Directory()]:
            trait.handler = handler
            self.assertTrue(is_trait_pathname(trait))

    def test_clone_trait(self):
        """ Method to test trait clone from string description.
        """
        trait_description = ["Float", "Int"]
        handler = clone_trait(trait_description)
        trait = CTrait(0)
        trait.handler = handler
        #self.assertEqual(trait_description, trait_ids(trait))

    def test_load_module_objects(self):
        """ Method to test module objects import from string description.
        """
        from capsul.pipeline.pipeline_nodes import Node
        node_sub_class = load_objects(
            "capsul.pipeline.pipeline_nodes", allowed_instances=[Node])
        for sub_class in node_sub_class:
            self.assertTrue(issubclass(sub_class, Node))
        node_class = load_objects(
            "capsul.pipeline.pipeline_nodes", object_name="Node")[0]
        self.assertEqual(node_class, Node)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
