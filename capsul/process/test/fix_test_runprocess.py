from __future__ import print_function

import subprocess
import sys
import unittest

from capsul.api import Process
from traits.api import Float, Undefined


class DummyProcess(Process):
    """Description of DummyProcess"""
    f = Float(Undefined, output=False, optional=False,
              desc="help for parameter f")
    def _run_process(self):
        print("DummyProcess exec, f={0}".format(self.f))


class TestRunProcess(unittest.TestCase):
    """Test case for CAPSUL command-line usage."""
    def test_help(self):
        ret = subprocess.call([sys.executable, "-m", "capsul.run", "--help"])
        self.assertEqual(ret, 0)

    def test_python_m_capsul(self):
        # No __main__.py in Python 2.6, no unittest.skipif either...
        if sys.version_info >= (2, 7):
            ret = subprocess.call([sys.executable, "-m", "capsul", "--help"])
            self.assertEqual(ret, 0)

    def test_run_process_help(self):
        ret = subprocess.call([
            sys.executable, "-m", "capsul.run",
            "--process-help",
            "capsul.process.test.test_runprocess.DummyProcess"
        ])
        self.assertEqual(ret, 0)

    def test_run_dummy_process(self):
        ret = subprocess.call([
            sys.executable, "-m", "capsul.run",
            "capsul.process.test.test_runprocess.DummyProcess",
            "f=0.5"
        ])
        self.assertEqual(ret, 0)
        ret = subprocess.call([
            sys.executable, "-m", "capsul.run",
            "capsul.process.test.test_runprocess.DummyProcess",
            "0.5"
        ])
        self.assertEqual(ret, 0)

    def test_run_dummy_process_wrong_args(self):
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
           "f=toto"
       ])
       self.assertNotEqual(ret, 0)
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
       ])
       self.assertNotEqual(ret, 0)
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
       ])
       self.assertNotEqual(ret, 0)



def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRunProcess)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
