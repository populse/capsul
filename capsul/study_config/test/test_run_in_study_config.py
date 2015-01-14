#! /usr/bin/env python
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest
import tempfile
import shutil
import os

# Capsul import
from capsul.process import Process
from capsul.study_config.study_config import StudyConfig

# Trait import
from traits.api import Float, Directory


class DummyProcess(Process):
    """ A dummy process.
    """
    f1 = Float(output=False, optional=False, desc="a float")
    f2 = Float(output=False, optional=False, desc="a float")
    output_directory = Directory(output=False, optional=False,
                                 exists=False, desc="a directory")
    res = Float(output=True, desc="a float")

    def _run_process(self):
        self.res = self.f1 * self.f2


class TestRunProcess(unittest.TestCase):
    """ Execute a process.
    """
    def __init__(self, testname, dirpath, cachepath=None):
        """ Initilaize the TestRunProcess class.
        """
        # Inheritance
        super(TestRunProcess, self).__init__(testname)

        # Create the memory object
        self.cachedir = cachepath
        self.output_dir = dirpath

        # Create a study configuration
        self.study_config = StudyConfig(modules=[])
        self.study_config.output_directory = dirpath

    def test_execution_1(self):
        """ Test to execute DummyProcess.
        """
        # Create a process instance
        process = DummyProcess()

        # Test the cache mechanism
        for param in [(1., 2.3), (2., 2.), (1., 2.3)]:
            self.study_config.run(process, executer_qc_nodes=False, verbose=1,
                                  f1=param[0], f2=param[1])
            self.assertEqual(process.res, param[0] * param[1])
            self.assertEqual(
                process.output_directory,
                os.path.join(self.output_dir, "{0}-{1}".format(
                    self.study_config.process_counter - 1, process.name)))


def test():
    """ Function to execute unitest.
    """
    dirpath = tempfile.mkdtemp()
    suite = unittest.TestSuite()
    suite.addTest(TestRunProcess("test_execution_1", dirpath, dirpath))
    suite.addTest(TestRunProcess("test_execution_1", dirpath, None))
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    shutil.rmtree(dirpath)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())