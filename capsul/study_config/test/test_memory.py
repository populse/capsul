#! /usr/bin/env python
##########################################################################
# Capsul - Copyright (C) CEA, 2014
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import unittest

# Capsul import
from capsul.process import Process
from capsul.study_config.memory import Memory

# Trait import
from traits.api import Float


class DummyProcess(Process):
    """ Dummy. 
    """
    f = Float(output=False, optional=False, desc="float")

    def __init__(self):
        super(DummyProcess, self).__init__()
        self.add_trait("ff", Float(output=False, optional=True, desc="float"))
        self.add_trait("res", Float(output=True, desc="float"))

    def _run_process(self):
        self.res = self.f * self.ff

# Create the memory object     
mem = Memory("/home/ag239446/tmp/")

# Create a process instance
instance = DummyProcess()

# create a decarted instance
dec_instance = mem.cache(instance)
print dec_instance
print dec_instance.__doc__

# Clear all the cache
mem.clear()

# Test the cache mechanism
for param in [(1., 2.3), (2., 2.), (1., 2.3)]:
    result = dec_instance(f=param[0], ff=param[1])
    print dec_instance.res

