# -*- coding: utf-8 -*-
# System import
from __future__ import absolute_import
from __future__ import print_function
import unittest
import tempfile
import shutil
import os

# Capsul import
from capsul.api import Process, get_process_instance
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
    def test_execution_with_cache(self):
        """ Execute a process with cache.
        """
        # Create a study configuration
        self.output_directory = tempfile.mkdtemp()
        self.study_config = StudyConfig(
            modules=["SmartCachingConfig"],
            use_smart_caching=True,
            output_directory=self.output_directory)

        # Call the test
        self.execution_dummy()

        # Rm temporary folder
        shutil.rmtree(self.output_directory)

    def test_execution_without_cache(self):
        """ Execute a process without cache.
        """
        # Create a study configuration
        self.output_directory = tempfile.mkdtemp()
        self.study_config = StudyConfig(
            modules=["SmartCachingConfig"],
            use_smart_caching=False,
            output_directory=self.output_directory)

        # Call the test
        self.execution_dummy()

        # Rm temporary folder
        shutil.rmtree(self.output_directory)

    def execution_dummy(self):
        """ Test to execute DummyProcess.
        """
        # Create a process instance
        process = self.study_config.get_process_instance(DummyProcess, output_directory=self.output_directory)

        # Test the cache mechanism
        for param in [(1., 2.3), (2., 2.), (1., 2.3)]:
            self.study_config.run(process, execute_qc_nodes=False, verbose=1,
                                  f1=param[0], f2=param[1])
            self.assertEqual(process.res, param[0] * param[1])
            self.assertEqual(
                process.output_directory,
                self.output_directory)


def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRunProcess)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
