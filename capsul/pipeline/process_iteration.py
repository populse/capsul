#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import List, Undefined

from capsul.process import Process
from capsul.process import get_process_instance
from traits.api import File, Directory

class ProcessIteration(Process):
    def __init__(self, process, iterative_parameters):
        super(ProcessIteration, self).__init__()
        self.process = get_process_instance(process)
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)

        # Check that all iterative parameters are valid process parameters
        user_traits = self.process.user_traits()
        has_output = False
        inputs = []
        for parameter in self.iterative_parameters:
            if parameter not in user_traits:
                raise ValueError('Cannot iterate on parameter %s '
                  'that is not a parameter of process %s'
                  % (parameter, self.process.id))
            if user_traits[parameter].output:
                has_output = True
            else:
                inputs.append(parameter)

        # Create iterative process parameters by copying process parameter
        # and changing iterative parameters to list
        for name, trait in user_traits.iteritems():
            if name in iterative_parameters:
                self.add_trait(name, List(trait, output=trait.output,
                                          optional=trait.optional))
            else:
                self.regular_parameters.add(name)
                self.add_trait(name, trait)
                # copy initial value of the underlying process to self
                # Note: should be this be done via a links system ?
                setattr(self, name, getattr(self.process, name))

        # if the process has iterative outputs, the output lists have to be
        # resized according to inputs
        if has_output:
            self.on_trait_change(self._resize_outputs, inputs)

    def _resize_outputs(self):
        num = 0
        outputs = []
        for param in self.iterative_parameters:
            if self.process.trait(param).output:
                if isinstance(self.process.trait(param).trait_type,
                              (File, Directory)):
                    outputs.append(param)
            else:
                num = max(num, len(getattr(self, param)))
        for param in outputs:
            value = getattr(self, param)
            mod = False
            if len(value) > num:
                new_value = value[:num]
                mod = True
            else:
                if len(value) < num:
                    new_value = value \
                        + [self.process.trait(param).default] \
                            * (num - len(value))
                    mod = True
            if mod:
                setattr(self, param, new_value)

    def _run_process(self):
        # Check that all iterative parameter value have the same size
        no_output_value = None
        size = None
        size_error = False
        for parameter in self.iterative_parameters:
            trait = self.trait(parameter)
            value = getattr(self, parameter)
            psize = len(value)
            if psize and (not trait.output
                          or len([x for x in value
                                  if x in ('', Undefined, None)]) == 0):
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
                    #if not no_output_value or not self.trait(parameter).output:
                    value = getattr(self, parameter)
                    if len(value) > iteration:
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
            for parameter, value in outputs.iteritems():
                setattr(self, parameter, value)
        else:
            for iteration in xrange(size):
                for parameter in self.iterative_parameters:
                    setattr(self.process, parameter, getattr(self, parameter)[iteration])
                self.process()

