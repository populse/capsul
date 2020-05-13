# -*- coding: utf-8 -*-
from __future__ import print_function

from __future__ import absolute_import
import os
import os.path as osp
import unittest
import sys
import tempfile
from glob import glob

from traits.api import File, Undefined

from capsul.study_config.study_config import StudyConfig, Process
from capsul.subprocess import fsl
    
class Bet(Process):
    input_image = File(optional=False, output=False)
    output_image = File(optional=False, output=True)
    

    def _run_process(self):
        fsl.check_call(self.study_config, ['bet', self.input_image, self.output_image])
    

class TestFSL(unittest.TestCase):

    def setUp(self):
        pass

    def test_study_config_fsl(self):
        if not sys.platform.startswith('win'):
            try:
                study_config = StudyConfig(use_fsl=True)
            except EnvironmentError as e:
                # If FSL cannot be configured automatically, skip the test
                print('WARNING: Skip FSL test because it cannot be configured automatically:', str(e), file=sys.stderr)
                return
            test_image = '/usr/share/data/fsl-mni152-templates/MNI152_T1_1mm_brain.nii.gz'
            if not osp.exists(test_image):
                fsl_dir = os.environ.get('FSLDIR')
                test_image = None
                if not fsl_dir and study_config.fsl_config is not Undefined:
                    fsl_dir = osp.dirname(osp.dirname(osp.dirname(study_config.fsl_config)))
                if fsl_dir:
                    test_image = glob(osp.join(fsl_dir, 'fslpython/envs/fslpython/lib/python*/site-packages/nibabel/tests/data/anatomical.nii'))
                    if test_image:
                        test_image = test_image[0]
                if not test_image:
                    print('WARNING: Skip FSL test because test data cannot be found', file=sys.stderr)
                    return
            bet = study_config.get_process_instance(Bet)
            with tempfile.NamedTemporaryFile(suffix='.nii.gz') as tmp:
                bet.run(
                    input_image=test_image,
                    output_image=tmp.name)
                self.assertTrue(os.stat(tmp.name).st_size != 0)


def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFSL)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())
