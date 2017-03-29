##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.pipeline.process_iteration import ProcessIteration
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    ProcessCompletionEngineFactory
from capsul.attributes.attributes_schema import ProcessAttributes
from soma.controller import Controller,ControllerTrait
import traits.api as traits
import six
import sys

if sys.version_info[0] >= 3:
    xrange = range


class ProcessCompletionEngineIteration(ProcessCompletionEngine):
    ''' ProcessCompletionEngine specialization for iterative process.

    Iterated attributes are given by get_iterated_attributes().
    Completion performs a single iteration step, stored in
    self.capsul_iteration_step
    '''
    def __init__(self, process, name=None):
        super(ProcessCompletionEngineIteration, self).__init__(
            process=process, name=name)
        #self.add_trait('capsul_iteration_step', traits.Int(0))
        self.capsul_iteration_step = 0
        #self.iterated_attributes = self.get_iterated_attributes()


    def get_iterated_attributes(self):
        '''
        '''
        try:
            pattributes = ProcessCompletionEngine.get_completion_engine(
                self.process.process).get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return []
        param_attributes = pattributes.get_parameters_attributes()
        attribs = set()
        for parameter in self.process.iterative_parameters:
            attribs.update(param_attributes.get(parameter, {}).keys())
        return [param for param in pattributes.user_traits().keys()
                if param in attribs]


    def get_induced_iterative_parameters(self):
        '''Iterating over some parameters, and triggering completion through
        attributes, imply that some other parameters will also vary with the
        iteration.
        Ex: process A has 2 parameters, "input" and "output", which are linked
        by the completion system. If we iterate on A.input, then A.output will
        also change with the iteration: parameter "output" should thus be
        included in iterative parameters: it is induced by the iteration over
        "input".

        This method gives the induced iterative parameters.
        '''
        # 1st get iterated attributes
        attributes = self.get_iterated_attributes()
        # now look on which parameters they are acting
        pattributes = ProcessCompletionEngine.get_completion_engine(
            self.process.process).get_attribute_values()
        param_attributes = pattributes.get_parameters_attributes()
        induced_params = []
        for parameter in self.process.process.user_traits():
            if parameter not in self.process.iterative_parameters:
                par_attributes = param_attributes.get(parameter)
                if par_attributes:
                    par_attributes = set(par_attributes.keys())
                    if [attribute for attribute in attributes
                        if attribute in par_attributes]:
                        induced_params.append(parameter)

        return induced_params


    def get_attribute_values(self):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        t = self.trait('capsul_attributes')
        if t is None or not hasattr(self, 'capsul_attributes'):
            try:
                pattributes = ProcessCompletionEngine.get_completion_engine(
                    self.process.process).get_attribute_values()
            except AttributeError:
                # ProcessCompletionEngine not implemented for this process:
                # no completion
                return

            schemas = self._get_schemas()
            attributes = ProcessAttributes(self.process, schemas)

            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            self.capsul_attributes = attributes
            iter_attrib = self.get_iterated_attributes()
            for attrib, trait in six.iteritems(pattributes.user_traits()):
                if attrib not in iter_attrib:
                    attributes.add_trait(attrib, trait)
            for attrib in iter_attrib:
                trait = pattributes.trait(attrib)
                if trait is not None:
                    attributes.add_trait(
                        attrib, traits.List(trait, output=trait.output))
                value = getattr(pattributes, attrib, None)
                if value is not None and value is not traits.Undefined:
                    setattr(attributes, attrib, [value])
        return self.capsul_attributes


    def complete_parameters(self, process_inputs={}):
        self.completion_progress = 0.
        try:
            self.set_parameters(process_inputs)
            attributes_set = self.get_attribute_values()
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                self.process.process, self.name)
            step_attributes = completion_engine.get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return
        iterated_attributes = self.get_iterated_attributes()
        for attribute in attributes_set.user_traits():
            if attribute not in iterated_attributes:
                setattr(step_attributes, attribute,
                        getattr(attributes_set, attribute))
        parameters = {}
        for parameter in self.process.regular_parameters:
            parameters[parameter] = getattr(self.process, parameter)

        size = max([len(getattr(attributes_set, attribute))
                    for attribute in iterated_attributes])

        # complete each step to get iterated parameters.
        # This is generally "too much" but it's difficult to perform a partial
        # completion only on iterated parameters

        iterative_parameters = dict(
            [(key, []) for key in self.process.iterative_parameters])

        self.completion_progress_total = size
        for it_step in xrange(size):
            self.capsul_iteration_step = it_step
            for attribute in iterated_attributes:
                iterated_values = getattr(attributes_set, attribute)
                step = min(len(iterated_values) - 1, it_step)
                value = iterated_values[step]
                setattr(step_attributes, attribute, value)
            for parameter in self.process.iterative_parameters:
                values = getattr(self.process, parameter)
                if isinstance(values, list) and len(values) > it_step:
                    parameters[parameter] = values[it_step]
            completion_engine.complete_parameters(parameters)
            for parameter in self.process.iterative_parameters:
                value = getattr(self.process.process, parameter)
                iterative_parameters[parameter].append(value)
            self.completion_progress = it_step + 1
        for parameter, values in six.iteritems(iterative_parameters):
            setattr(self.process, parameter, values)


    def complete_iteration_step(self, step):
        ''' Complete the parameters on the iterated process for a given
        iteration step.
        '''
        try:
            attributes_set = self.get_attribute_values()
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                self.process.process, self.name)
            step_attributes = completion_engine.get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return
        iterated_attributes = self.get_iterated_attributes()
        self.capsul_iteration_step = step
        for attribute in iterated_attributes:
            iterated_values = getattr(attributes_set, attribute)
            step = min(len(iterated_values) - 1, self.capsul_iteration_step)
            value = iterated_values[step]
            setattr(step_attributes, attribute, value)
        for attribute in attributes_set.user_traits():
            if attribute not in iterated_attributes:
                setattr(step_attributes, attribute,
                        getattr(attributes_set, attribute))
        parameters = {}
        for parameter in self.process.regular_parameters:
            parameters[parameter] = getattr(self.process, parameter)
        for parameter in self.process.iterative_parameters:
            values = getattr(self.process, parameter)
            if len(values) > self.capsul_iteration_step:
                parameters[parameter] = values[self.capsul_iteration_step]
        completion_engine.complete_parameters(parameters)

