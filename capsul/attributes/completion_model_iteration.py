##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.pipeline.process_iteration import ProcessIteration
from capsul.attributes.completion_model import ProcessCompletionModel, \
    ProcessCompletionModelFactory
from soma.controller import Controller,ControllerTrait
import traits.api as traits
import six


class ProcessCompletionModelIteration(ProcessCompletionModel):
    ''' ProcessCompletionModel specialization for iterative process.

    Iterated attributes are given by get_iterated_attributes().
    Completion performs a single iteration step, stored in
    self.capsul_iteration_step
    '''
    def __init__(self, name=None):
        super(ProcessCompletionModelIteration, self).__init__(name)
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
        pattributes = ProcessCompletionModel.get_completion_model(
            process.process).get_attribute_values(process.process)
        t = self.trait('capsul_attributes')
        if t is None:
            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            attributes = self.capsul_attributes
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
        self.set_parameters(process, process_inputs)
        attributes_set = self.get_attribute_values(process)
        completion_model = ProcessCompletionModel.get_completion_model(
            process.process, self.name)
        # duplicate attributes before modification
        step_attributes = completion_model.get_attribute_values(
            process.process)
        iterated_attributes = self.get_iterated_attributes(process)
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
            if isinstance(values, list) \
                    and len(values) > self.capsul_iteration_step:
                parameters[parameter] = values[self.capsul_iteration_step]
        completion_model.complete_parameters(process.process, parameters)


    @staticmethod
    def _iteration_factory(process, name):
        if not isinstance(process, ProcessIteration):
            return None
        return ProcessCompletionModelIteration(name)


ProcessCompletionModelFactory().register_factory(
    ProcessCompletionModelIteration._iteration_factory, 50000)


