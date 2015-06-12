#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import List

from capsul.process import Process
from capsul.process import get_process_instance

class ProcessIteration(Process):
    def __init__(self, process, iterative_parameters):
        super(ProcessIteration, self).__init__()
        self.process = get_process_instance(process)
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)
        
        # Check that all iterative parameters are valid process parameters
        user_traits = self.process.user_traits()
        for parameter in self.iterative_parameters:
            if parameter not in user_traits:
                raise ValueError('Cannot iterate on parameter %s that is not a parameter of process %s' % (parameter, self.process.id))

        # Create iterative process parameters by copying process parameter
        # and changing iterative parameters to list
        for name, trait in user_traits.iteritems():
            if name in iterative_parameters:
                self.add_trait(name, List(trait))
            else:
                self.regular_parameters.add(name)
                self.add_trait(name, trait)
                
    def _run_process(self):
        # Check that all iterative parameter value have the same size
        size = set(len(getattr(self, i)) for i in self.iterative_parameters)
        if size:
            if len(size) > 1:
                raise ValueError('Iterative parameter values must be lists of the same size: %s' % ','.join('%s=%d' % (n, len(getattr(self,n))) for n in self.iterative_parameters))
            size = size.pop()
            
            for parameter in self.regular_parameters:
                setattr(self.process, parameter, getattr(self, parameter))
            for iteration in xrange(size):
                for parameter in self.iterative_parameters:
                    setattr(self.process, parameter, getattr(self, parameter)[iteration])
                self.process()
    