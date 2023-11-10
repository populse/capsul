import unittest
import six

from capsul.api import Process, executable


class DummyProcess(Process):
    f : float

    def __init__(self, definition):
        super().__init__(definition=definition)
        self.add_field('ff', float)


class TestProcessUserTrait(unittest.TestCase):
    """ Class to test that process user fields are independent between
    instances.
    """
    def setUp(self):
        """ In the setup construct two processes with class and instance
        user parameters.
        """

        # Construct the processes
        self.p1 = executable(
            'capsul.process.test.test_fields.DummyProcess')
        self.p2 = executable(
            'capsul.process.test.test_fields.DummyProcess')

    def test_class_user_parameters(self):
        """ Method to test if class user parameters are not shared at
        the instance level.
        """
        # Go through all fields
        for field in self.p1.fields():
            # Check that only class fields are shared
            # between instances
            self.assertEqual(
                field._dataclass_field is
                    self.p2.field(field.name)._dataclass_field,
                field.class_field)



if __name__ == "__main__":
    unittest.main()
