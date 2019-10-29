from __future__ import print_function

from .load_pilots import load_pilots
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
#         ALL TESTS PASSED       #
##################################

              +---+
              |   |
                  |
                  | \O/
                  |  |
                  | / \\
           ==============
"""

partial_message = """

##################################
#     AVAILABLE TESTS PASSED     #
##################################

              +---+
              |   |
                  |
                  |  O 
                  | |||
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
    has_warnings = False
    is_valid = True
    for module, ltest in tests.items():
        if isinstance(ltest, Warning):
            print('=' * 60)
            print("WARNING when loading module {0}: {1}".format(module, ltest))
            print('=' * 60)
            has_warnings = True
        elif isinstance(ltest, Exception):
            print('=' * 60)
            print("ERROR when loading module {0}: {1}".format(module, ltest))
            print('=' * 60)
            is_valid = False
        else:
            for test in ltest:
                is_valid = test() and is_valid
    return is_valid, has_warnings


def is_valid_module():
    is_valid, has_warnings = run_all_tests()
    if is_valid:
        if has_warnings:
            print(partial_message)
        else:
            print(valid_message)
    else:
        print(error_message)
    return is_valid


if __name__ == "__main__":
    is_valid = is_valid_module()
    if not is_valid:
        sys.exit(1)

