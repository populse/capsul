##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import sys
import six
from traits.api import List, Undefined

from capsul.process.process import Process
from capsul.study_config.process_instance import get_process_instance

if sys.version_info[0] >= 3:
    xrange = range

class ProcessIteration(Process):
    def __init__(self, process, iterative_parameters):
        super(ProcessIteration, self).__init__()
        self.process = get_process_instance(process,
                                            study_config=self.study_config)
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)

        # Check that all iterative parameters are valid process parameters
        user_traits = self.process.user_traits()
        for parameter in self.iterative_parameters:
            if parameter not in user_traits:
                raise ValueError('Cannot iterate on parameter %s '
                  'that is not a parameter of process %s'
                  % (parameter, self.process.id))

        # Create iterative process parameters by copying process parameter
        # and changing iterative parameters to list
        for name, trait in six.iteritems(user_traits):
            if name in iterative_parameters:
                self.add_trait(name, List(trait, output=trait.output,
                                          optional=trait.optional))
            else:
                self.regular_parameters.add(name)
                self.add_trait(name, trait)
                # copy initial value of the underlying process to self
                # Note: should be this be done via a links system ?
                setattr(self, name, getattr(self.process, name))

    def _run_process(self):
        # Check that all iterative parameter value have the same size
        no_output_value = None
        size = None
        size_error = False
        for parameter in self.iterative_parameters:
            trait = self.trait(parameter)
            psize = len(getattr(self, parameter))
            if psize:
                if size is None:
                    size = psize
                elif size != psize:
                    size_error = True
                    break
                if trait.output:
                    if no_output_value is None:
                        no_output_value = False
                    elif no_output_value:
                        size_error = True
                        break
            else:
                if trait.output:
                    if no_output_value is None:
                        no_output_value = True
                    elif not no_output_value:
                        size_error = True
                        break
                else:
                    if size is None:
                        size = psize
                    elif size != psize:
                        size_error = True
                        break

        if size_error:
            raise ValueError('Iterative parameter values must be lists of the same size: %s' % ','.join('%s=%d' % (n, len(getattr(self,n))) for n in self.iterative_parameters))
        if size == 0:
            return

        for parameter in self.regular_parameters:
            setattr(self.process, parameter, getattr(self, parameter))
        if no_output_value:
            for parameter in self.iterative_parameters:
                trait = self.trait(parameter)
                if trait.output:
                    setattr(self, parameter, [])
            outputs = {}
            for iteration in xrange(size):
                for parameter in self.iterative_parameters:
                    if not no_output_value or not self.trait(parameter).output:
                        setattr(self.process, parameter,
                                getattr(self, parameter)[iteration])
                self.process()
                for parameter in self.iterative_parameters:
                    trait = self.trait(parameter)
                    if trait.output:
                        outputs.setdefault(parameter,[]).append(
                            getattr(self.process, parameter))
                        # reset empty value
                        setattr(self.process, parameter, Undefined)
            for parameter, value in six.iteritems(outputs):
                setattr(self, parameter, value)
        else:
            for iteration in xrange(size):
                for parameter in self.iterative_parameters:
                    setattr(self.process, parameter, getattr(self, parameter)[iteration])
                self.process()
            

