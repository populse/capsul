# -*- coding: utf-8 -*-
import unittest
import six

from capsul.api import Process


class DummyProcess(Process):
    f : float

    def __init__(self):
        super().__init__()
        self.add_field('ff', float)


class TestProcessUserTrait(unittest.TestCase):
    """ Class to test that process user traits are independent between
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
        the instance level.
        """
        # Go through all traits
        for field in self.p1.fields():
            # Check that only class fields are shared
            # between instances
            self.assertEqual(
                field is self.p2.field(field.name), field.metadata['class_field'])



if __name__ == "__main__":
    unittest.main()
