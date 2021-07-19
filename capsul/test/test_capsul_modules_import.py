# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import unittest
import sys
import os


class TestCapsulModulesImport(unittest.TestCase):

    def setUp(self):
        pass

    def test_capsul_import(self):
        import capsul

    def test_capsul_studyconfig_import(self):
        import capsul.study_config

    def test_capsul_process_import(self):
        import capsul.process

    def test_capsul_pipeline_import(self):
        import capsul.pipeline

    def test_capsul_pipeline_pipeline_workflow_import(self):
        import capsul.pipeline.pipeline_workflow

    def test_capsul_utils_import(self):
        import capsul.utils



def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCapsulModulesImport)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
