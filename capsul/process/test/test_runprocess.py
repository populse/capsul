# -*- coding: utf-8 -*-
##########################################################################
# Capsul - Copyright (C) CEA, 2019
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

from __future__ import absolute_import
import os
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
        ret = subprocess.call([sys.executable, "-m", "capsul.run", "--help"],
                              stdout=open(os.devnull, 'wb'),
                              stderr=open(os.devnull, 'wb'))
        self.assertEqual(ret, 0)

    def test_python_m_capsul(self):
        ret = subprocess.call([sys.executable, "-m", "capsul", "--help"],
                              stdout=open(os.devnull, 'wb'),
                              stderr=open(os.devnull, 'wb'))
        self.assertEqual(ret, 0)

    def test_run_process_help(self):
        ret = subprocess.call([
                sys.executable, "-m", "capsul.run",
                "--process-help",
                "capsul.process.test.test_runprocess.DummyProcess"
            ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
        self.assertEqual(ret, 0)

    def test_run_dummy_process(self):
        ret = subprocess.call([
            sys.executable, "-m", "capsul.run",
            "capsul.process.test.test_runprocess.DummyProcess",
            "f=0.5"
        ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
        self.assertEqual(ret, 0)
        ret = subprocess.call([
            sys.executable, "-m", "capsul.run",
            "capsul.process.test.test_runprocess.DummyProcess",
            "0.5"
        ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
        self.assertEqual(ret, 0)

    def test_run_dummy_process_wrong_args(self):
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
           "f=toto"
       ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
       self.assertNotEqual(ret, 0)
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
       ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
       self.assertNotEqual(ret, 0)
       ret = subprocess.call([
           sys.executable, "-m", "capsul.run",
           "capsul.process.test.test_runprocess.DummyProcess",
       ], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
       self.assertNotEqual(ret, 0)



def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRunProcess)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
