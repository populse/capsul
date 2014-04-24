#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from load_pilots import load_pilots
import capsul
import sys

error_message = """

##################################
#           GAME OVER            #
##################################

              +---+
              |   |
              O   |
             /|\  |
             / \  |
                  |
            =========
"""

valid_message = """

##################################
#        MODULE TEST PASSED      #
##################################

              +---+
              |   |
                  |
                  | \O/
                  |  |
                  | / \\
           ==============
            """


def run_all_tests():
    """ Execute all the unitests.

    Returns
    -------
    is_valid : bool
        True if all the tests are passed successfully,
        False otherwise.
    """
    module_path = capsul.__path__[0]
    tests = load_pilots(module_path, module_path)

    is_valid = True
    for module, ltest in tests.items():
        for test in ltest:
            is_valid = test() and is_valid

    return is_valid


def is_valid_module():
    is_valid = run_all_tests()
    if is_valid:
        print valid_message
    else:
        print error_message
    return is_valid


if __name__ == "__main__":
    is_valid = is_valid_module()
    if not is_valid:
        sys.exit(1)

