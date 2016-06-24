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
    def __init__(self, name=None):
        super(ProcessCompletionEngineIteration, self).__init__(name)
        #self.add_trait('capsul_iteration_step', traits.Int(0))
        self.capsul_iteration_step = 0
        #self.iterated_attributes = self.get_iterated_attributes()


    def get_iterated_attributes(self, process):
        '''
        '''
        # How do we provide that ?
        # Subclassing ?
        # Lookup in a table / sub object ?
        # Use a FOM-like description by process ?
        return []


    def get_attribute_values(self, process):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        t = self.trait('capsul_attributes')
        if t is None:
            try:
                pattributes = ProcessCompletionEngine.get_completion_engine(
                    process.process).get_attribute_values(process.process)
            except AttributeError:
                # ProcessCompletionEngine not implemented for this process:
                # no completion
                return

            schemas = self._get_schemas(process)
            attributes = ProcessAttributes(process, schemas)

            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            self.capsul_attributes = attributes
            iter_attrib = self.get_iterated_attributes(process)
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


    def complete_parameters(self, process, process_inputs={}):
        try:
            self.set_parameters(process, process_inputs)
            attributes_set = self.get_attribute_values(process)
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                process.process, self.name)
            step_attributes = completion_engine.get_attribute_values(
                process.process)
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return
        iterated_attributes = self.get_iterated_attributes(process)
        for attribute in attributes_set.user_traits():
            if attribute not in iterated_attributes:
                setattr(step_attributes, attribute,
                        getattr(attributes_set, attribute))
        parameters = {}
        for parameter in process.regular_parameters:
            parameters[parameter] = getattr(process, parameter)

        size = max([len(getattr(attributes_set, attribute))
                    for attribute in iterated_attributes])

        # complete each step to get iterated parameters.
        # This is generally "too much" but it's difficult to perform a partial
        # completion only on iterated parameters

        iterative_parameters = dict([(key, [])
                                     for key in process.iterative_parameters])

        for it_step in xrange(size):
            for attribute in iterated_attributes:
                iterated_values = getattr(attributes_set, attribute)
                step = min(len(iterated_values) - 1, it_step)
                value = iterated_values[step]
                setattr(step_attributes, attribute, value)
            for parameter in process.iterative_parameters:
                values = getattr(process, parameter)
                if isinstance(values, list) and len(values) > it_step:
                    parameters[parameter] = values[it_step]
            completion_engine.complete_parameters(process.process, parameters)
            for parameter in process.iterative_parameters:
                value = getattr(process.process, parameter)
                iterative_parameters[parameter].append(value)
            for parameter, values in six.iteritems(iterative_parameters):
                setattr(process, parameter, values)


    def complete_iteration_step(self, process, step):
        ''' Complete the parameters on the iterated process for a given
        iteration step.
        '''
        try:
            attributes_set = self.get_attribute_values(process)
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                process.process, self.name)
            step_attributes = completion_engine.get_attribute_values(
                process.process)
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return
        iterated_attributes = self.get_iterated_attributes(process)
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
        for parameter in process.regular_parameters:
            parameters[parameter] = getattr(process, parameter)
        for parameter in process.iterative_parameters:
            values = getattr(process, parameter)
            if len(values) > self.capsul_iteration_step:
                parameters[parameter] = values[self.capsul_iteration_step]
        completion_engine.complete_parameters(process.process, parameters)


    @staticmethod
    def _iteration_factory(process, name):
        if not isinstance(process, ProcessIteration):
            return None
        return ProcessCompletionEngineIteration(name)


ProcessCompletionEngineFactory().register_factory(
    ProcessCompletionEngineIteration._iteration_factory, 50000)


