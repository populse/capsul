##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest

# Nipype impoort
try:
    import nipype.interfaces.spm as spm
except ImportError:
    raise Warning('test not performed because Nipype is not installed')

# Trait import
from traits.api import Float, CTrait, File, Directory
from traits.api import Undefined

# Soma import
from soma.controller.trait_utils import (
    get_trait_desc, is_trait_value_defined, is_trait_pathname,
    clone_trait, build_expression, trait_ids, eval_trait)

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
        self.assertFalse(is_trait_value_defined(Undefined))

        trait = CTrait(0)
        trait.handler = Float()
        self.assertFalse(is_trait_pathname(trait))
        for handler in [File(), Directory()]:
            trait.handler = handler
            self.assertTrue(is_trait_pathname(trait))

    def test_clone_trait(self):
        """ Method to test trait clone from string description.
        """
        # Test first to build trait description from nipype traits and then
        # to instanciate the trait
        to_test_fields = {
            "timing_units": "traits.Enum(('secs', 'scans'))",
            "bases": ("traits.Dict(traits.Enum(('hrf', 'fourier', "
                      "'fourier_han', 'gamma', 'fir')), traits.Any())"),
            "mask_image": "traits.File(Undefined)",
            "microtime_onset": "traits.Float()",
            "mask_threshold": ("traits.Either(traits.Enum(('-Inf',)), "
                               "traits.Float())")
        }
        i = spm.Level1Design()
        for field, result in to_test_fields.iteritems():

            # Test to build the trait expression
            trait = i.inputs.trait(field)
            expression = build_expression(trait)
            self.assertEqual(expression, result)

            # Try to clone the trait
            trait = eval_trait(expression)()
            self.assertEqual(build_expression(trait), result)

        to_test_fields = {
            "contrasts": (
                "traits.List(traits.Either(traits.Tuple(traits.Str(), "
                "traits.Enum(('T',)), traits.List(traits.Str()), "
                "traits.List(traits.Float())), traits.Tuple(traits.Str(), "
                "traits.Enum(('T',)), traits.List(traits.Str()), "
                "traits.List(traits.Float()), traits.List(traits.Float())), "
                "traits.Tuple(traits.Str(), traits.Enum(('F',)), "
                "traits.List(traits.Either(traits.Tuple(traits.Str(), "
                "traits.Enum(('T',)), traits.List(traits.Str()), "
                "traits.List(traits.Float())), traits.Tuple(traits.Str(), "
                "traits.Enum(('T',)), traits.List(traits.Str()), "
                "traits.List(traits.Float()), traits.List(traits.Float())"
                "))))))"),
            "use_derivs": "traits.Bool()"
        }
        i = spm.EstimateContrast()
        for field, result in to_test_fields.iteritems():

            # Test to build the trait expression
            trait = i.inputs.trait(field)
            expression = build_expression(trait)
            self.assertEqual(expression, result)

            # Try to clone the trait
            trait = eval_trait(expression)()
            self.assertEqual(build_expression(trait), result)

        # Test to clone some traits
        trait_description = ["Float", "Int"]
        handler = clone_trait(trait_description)
        trait = handler.as_ctrait()
        self.assertEqual(trait_description, trait_ids(trait))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
