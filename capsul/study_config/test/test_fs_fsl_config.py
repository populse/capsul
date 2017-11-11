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
import sys
from traits.api import Undefined

# Capsul import
from capsul.study_config.study_config import StudyConfig

class TestStudyConfigFsFsl(unittest.TestCase):

    def setUp(self):
        pass

    #skipIf decorator is only available on python > 2.7.2
    #@unittest.skipIf(sys.platform.startswith('win'), 
                    #'FSL is not available on Windows')
    def test_study_config_fsl(self):
        if not sys.platform.startswith('win'):
            fsl_h = "/etc/fsl/4.1/fsl.sh"
            
            if os.path.exists(fsl_h):
                study_config = StudyConfig(modules=['FSLConfig'],
                    fsl_config = fsl_h)
                if not study_config.use_fsl:
                    return # skip this test if FSL is not available
                for varname in ["FSLDIR", "FSLOUTPUTTYPE", "FSLTCLSH", 
                                "FSLWISH", "FSLREMOTECALL", "FSLLOCKDIR", 
                                "FSLMACHINELIST", "FSLBROWSER"]:
                    self.assertTrue(os.environ.get(varname) is not None, 
                                    msg='%s environment variable not set' 
                                        % varname)


def test():
    """ Function to execute unitest.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStudyConfigFsFsl)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    print("RETURNCODE: ", test())

