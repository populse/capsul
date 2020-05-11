# -*- coding: utf-8 -*-
from __future__ import with_statement

# System import
from __future__ import absolute_import
from __future__ import print_function
import unittest

# Capsul import
import capsul.sphinxext.test as my_module
#from capsul.utils.pilot import pilotfunction
from capsul.sphinxext.usecasesdocgen import UseCasesHelperWriter
from capsul.sphinxext.load_pilots import load_pilots


#@pilotfunction
def pilot_dummy_test():
    """
    Test pilot doc generation.
    ==========================

    .. topic:: Objective

        Just a simple test to check if everything is all right.

    Import
    ------

    Start with some imports."""
    import socket

    """
    Processings
    -----------

    Now print host name.
    """
    print(socket.gethostname())


class TestUseCases(unittest.TestCase):
    """ Class to test that we can properly generate the use cases rst
    documentation.
    """
    def test_use_cases_doc(self):
        """ Method to test the use cases rst documentation.
        """
        # Get all the use cases
        module_path = my_module.__path__[0]
        pilots = load_pilots(module_path, module_path,
                             "capsul.sphinxext.test")
        self.assertTrue(len(pilots) == 1)
        self.assertTrue("capsul.sphinxext.test.test_usercases_doc" in pilots)
        self.assertTrue(
            len(pilots["capsul.sphinxext.test.test_usercases_doc"]) == 1)

        # Generate the writer object
        docwriter = UseCasesHelperWriter(
            pilots["capsul.sphinxext.test.test_usercases_doc"])
        rstdoc = docwriter.write_usecases_docs(returnrst=True)
        self.assertTrue(
            "capsul.sphinxext.test.test_usercases_doc.pilot_dummy_test" in
            rstdoc)


def test():
    """ Function to execute unitest
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUseCases)
    runtime = unittest.TextTestRunner(verbosity=2).run(suite)
    return runtime.wasSuccessful()


if __name__ == "__main__":
    test()
