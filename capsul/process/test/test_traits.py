##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import six

# Capsul import
from capsul.api import Process

# Trait import
from traits.api import Float


class DummyProcess(Process):
    f = Float(output=False)

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("ff", Float(output=False))


class TestProcessUserTrait(unittest.TestCase):
    """ Class to test that process user traits are independant between
    instances.
    """
    def setUp(self):
        """ In the setup construct two processes with class and instance
        user parameters.
        """
        # Construct the processes
        self.p1 = DummyProcess()
        self.p2 = DummyProcess()

    def test_class_user_parameters(self):
        """ Method to test if class user parameters are not shared at
        the instane level.
        """
        # Go through all traits
        for trait_name, trait in six.iteritems(self.p1.__base_traits__):

            # Select user parameters
            if self.p1.is_user_trait(trait):

                # Check that the current parameters are not the same
                # between instances
                self.assertFalse(
                    self.p1.trait(trait_name) is self.p2.trait(trait_name))


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProcessUserTrait)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
