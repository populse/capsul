#! /usr/bin/env python
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################


from capsul.process import Process
from traits.api import Float


class DummyProcess(Process):
    f = Float(output=False)

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("ff", Float(output=False))


if __name__ == "__main__":

    di_1 = DummyProcess()
    di_2 = DummyProcess()

    print DummyProcess.__base_traits__

    print di_1.user_traits()
    print di_2.user_traits()

    di_1.trait("f").output = True
    print di_1.trait("f").output, di_2.trait("f").output
    print di_1.trait("f") is di_2.trait("f")
