##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import six
import sys

# Nipype import
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
            "timing_units": "traits.api.Enum(('secs', 'scans'))",
            "bases": ("traits.api.Dict(traits.api.Enum(('hrf', 'fourier', "
                      "'fourier_han', 'gamma', 'fir')), traits.api.Any())"),
            "mask_image": "traits.api.File(Undefined)",
            "microtime_onset": "traits.api.Float()",
            "mask_threshold": ("traits.api.Either(traits.api.Enum(('-Inf',)), "
                               "traits.api.Float())")
        }
        i = spm.Level1Design()
        # fix param types depending on nipype/spm version
        if sys.version_info[0] < 3 \
                and type(i.inputs.trait('timing_units').get_validate()[1][0]) \
                    is unicode:
            to_test_fields["timing_units"] \
                = "traits.api.Enum((u'secs', u'scans'))"
            to_test_fields["bases"] \
                = "traits.api.Dict(traits.api.Enum((u'hrf', u'fourier', " \
                  "u'fourier_han', u'gamma', u'fir')), traits.api.Any())"
            to_test_fields["mask_threshold"] \
                = ("traits.api.Either(traits.api.Enum((u'-Inf',)), "
                   "traits.api.Float())")

        for field, result in six.iteritems(to_test_fields):

            # Test to build the trait expression
            trait = i.inputs.trait(field)
            expression = build_expression(trait)
            self.assertEqual(expression, result)

            # Try to clone the trait
            trait = eval_trait(expression)()
            self.assertEqual(build_expression(trait), result)

        to_test_fields = {
            "contrasts": (
                "traits.api.List(traits.api.Either(traits.api.Tuple(traits.api.Str(), "
                "traits.api.Enum(('T',)), traits.api.List(traits.api.Str()), "
                "traits.api.List(traits.api.Float())), traits.api.Tuple(traits.api.Str(), "
                "traits.api.Enum(('T',)), traits.api.List(traits.api.Str()), "
                "traits.api.List(traits.api.Float()), traits.api.List(traits.api.Float())), "
                "traits.api.Tuple(traits.api.Str(), traits.api.Enum(('F',)), "
                "traits.api.List(traits.api.Either(traits.api.Tuple(traits.api.Str(), "
                "traits.api.Enum(('T',)), traits.api.List(traits.api.Str()), "
                "traits.api.List(traits.api.Float())), traits.api.Tuple(traits.api.Str(), "
                "traits.api.Enum(('T',)), traits.api.List(traits.api.Str()), "
                "traits.api.List(traits.api.Float()), traits.api.List(traits.api.Float())"
                "))))))"),
            "use_derivs": "traits.api.Bool()"
        }
        i = spm.EstimateContrast()
        # fix param types depending on nipype/spm version
        if sys.version_info[0] < 3 \
                and type(i.inputs.trait('contrasts').inner_traits[0]. \
                    handler.handlers[0].as_ctrait().get_validate()[1][1]. \
                    get_validate()[1][0]) \
                    is unicode:
            to_test_fields["contrasts"] \
                = (
                    "traits.api.List(traits.api.Either(traits.api.Tuple(traits.api.Str(), "
                    "traits.api.Enum((u'T',)), traits.api.List(traits.api.Str()), "
                    "traits.api.List(traits.api.Float())), traits.api.Tuple(traits.api.Str(), "
                    "traits.api.Enum((u'T',)), traits.api.List(traits.api.Str()), "
                    "traits.api.List(traits.api.Float()), traits.api.List(traits.api.Float())), "
                    "traits.api.Tuple(traits.api.Str(), traits.api.Enum((u'F',)), "
                    "traits.api.List(traits.api.Either(traits.api.Tuple(traits.api.Str(), "
                    "traits.api.Enum((u'T',)), traits.api.List(traits.api.Str()), "
                    "traits.api.List(traits.api.Float())), traits.api.Tuple(traits.api.Str(), "
                    "traits.api.Enum((u'T',)), traits.api.List(traits.api.Str()), "
                    "traits.api.List(traits.api.Float()), traits.api.List(traits.api.Float())"
                    "))))))")

        for field, result in six.iteritems(to_test_fields):

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
