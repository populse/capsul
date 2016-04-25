##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

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
