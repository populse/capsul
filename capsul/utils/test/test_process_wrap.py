##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest

# Capsul import
from capsul.utils.test.process import AFunctionToWrap


class TestProcessWrap(unittest.TestCase):
    """ Class to test the function used to wrap a function to a process
    """
    def setUp(self):
        """ In the setup construct set some process input parameters.
        """
        # Get the wraped test process process
        self.process = AFunctionToWrap()

        # Set some input parameters
        self.process.fname = "fname"
        self.process.directory = "directory"
        self.process.value = 1.2
        self.process.enum = "choice1"
        self.process.list_of_str = ["a_string"]

    def test_process_wrap(self):
        """ Method to test if the process has been wraped properly.
        """
        # Execute the process
        self.process()
        self.assertEqual(getattr(self.process, "reference"), ["27"])
        self.assertEqual(
            getattr(self.process, "string"),
            "ALL FUNCTION PARAMETERS::\n\nfnamedirectory1.2choice1['a_string']")


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProcessWrap)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
