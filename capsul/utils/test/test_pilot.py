from __future__ import print_function

# System import
import numpy
import os
import unittest

# Capsul import
from capsul.utils.pilot import pilotfunction


# A class
class Dummy(object):
    """ A dummy class.
    """
    def __call__(self):
        print("Calling Dummy")


# The decorated pilot
@pilotfunction
def pilot():
    from capsul.utils.test.test_pilot import Dummy
    print(",".join(["t", "o"]))
    dummy = Dummy()
    dummy()


if __name__ == "__main__":
    pilot()
