from __future__ import print_function

import unittest
import tempfile
from capsul.engine import engine

class TestCapsulEngine(unittest.TestCase):
    def test_default_engine(self):
        tmp = tempfile.mktemp(suffix='.json')
        ce = engine(tmp)
        ce.save()
        ce2 = engine(tmp)
        self.assertEqual(ce.execution_context.to_json(),
                         ce2.execution_context.to_json())
        

def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapsulEngine)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
