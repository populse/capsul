# -*- coding: utf-8 -*-
# System import
from __future__ import absolute_import
import os
import unittest

# Capsul import
from capsul.api import get_process_instance
from capsul.api import NipypeProcess

try:
    import nipype
except ImportError:
    # if nipype is not installed, skip this test (without failure)
    nipype = None


class TestNipypeWrap(unittest.TestCase):
    """ Class to test the nipype interfaces wrapping.
    """

    def setUp(self):
        # output format and extensions depends on FSL config variables
        # so may change if FSL has been setup in a StudyConfig.
        fsl_output_format = os.environ.get('FSLOUTPUTTYPE', '')
        if fsl_output_format == 'NIFTI_GZ':
            self.output_extension = '.nii.gz'
        else:
            # default is nifti
            self.output_extension = '.nii'

    @unittest.skipIf(nipype is None, 'nipype is not installed')
    def test_nipype_automatic_wrap(self):
        """ Method to test if the automatic nipype interfaces wrap work
        properly.
        """
        from nipype.interfaces.fsl import BET
        nipype_process = get_process_instance("nipype.interfaces.fsl.BET")
        self.assertTrue(isinstance(nipype_process, NipypeProcess))
        self.assertTrue(isinstance(nipype_process._nipype_interface, BET))

    @unittest.skipIf(nipype is None, 'nipype is not installed')
    def test_nipype_monkey_patching(self):
        """ Method to test the monkey patching used to work in user
        specified directories.
        """
        nipype_process = get_process_instance("nipype.interfaces.fsl.BET")
        nipype_process.in_file = os.path.abspath(__file__)
        self.assertEqual(
            nipype_process._nipype_interface._list_outputs()["out_file"],
            os.path.join(os.getcwd(),
                         "test_nipype_wrap_brain%s" % self.output_extension))

def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNipypeWrap)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
