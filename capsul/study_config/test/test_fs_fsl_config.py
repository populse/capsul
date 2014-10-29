#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import unittest

# Capsul import
from capsul.study_config.study_config import StudyConfig
from capsul.study_config.config_modules.freesurfer_config import FreeSurferConfig
from capsul.study_config.config_modules.fsl_config import FSLConfig


class TestStudyConfigFsFsl(unittest.TestCase):

    def setUp(self):
        pass

    def test_study_config_fs(self):
        study_config = StudyConfig(modules=[FreeSurferConfig])
        study_config.fs_config = "/i2bm/local/freesurfer/SetUpFreeSurfer.sh"
        study_config.use_fs = True
        for varname in ["FREESURFER_HOME", "FSF_OUTPUT_FORMAT", "MNI_DIR",
                        "FSFAST_HOME", "FMRI_ANALYSIS_DIR", "FUNCTIONALS_DIR",
                        "MINC_BIN_DIR", "MNI_DATAPATH"]:
            self.assertTrue(os.environ.get(varname) is not None)

    def test_study_config_fsl(self):
        study_config = StudyConfig(modules=[FSLConfig])
        study_config.fsl_config = "/etc/fsl/4.1/fsl.sh"
        study_config.use_fsl = True
        for varname in ["FSLDIR", "FSLOUTPUTTYPE", "FSLTCLSH", "FSLWISH",
                        "FSLREMOTECALL", "FSLLOCKDIR", "FSLMACHINELIST",
                        "FSLBROWSER"]:
            self.assertTrue(os.environ.get(varname) is not None)


def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStudyConfigFsFsl)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

