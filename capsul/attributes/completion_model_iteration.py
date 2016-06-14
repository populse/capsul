##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.pipeline.process_iteration import ProcessIteration
from capsul.attributes.completion_model import CompletionModel, \
    CompletionModelFactory
from soma.controller import Controller
import traits.api as traits


class CompletionModelIteration(CompletionModel):
    ''' CompletionModel specialization for iterative process.

    Iterated attributes are given by get_iterated_attributes().
    Completion performs a single iteration step, stored in
    self.capsul_iteration_step
    '''
    def __init__(self, name=None):
        super(CompletionModelIteration, self).__init__(name)
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


    def complete_parameters(self, process, process_inputs={}):
        self.set_parameters(process, process_inputs)
        attributes_set = self.get_attribute_values(process)
        # duplicate attributes before modification
        iter_attributes = Controller(attributes_set)
        for attribute in self.get_iterated_attributes(process):
            trait = attributes_set.trait(attribute)
            inner_trait = trait.inner_traits[0].trait_type
            iter_attributes.remove_trait(attribute)
            iter_attributes.add_trait(attribute, inner_trait())
            iterated_values = getattr(attributes_set, attribute)
            if isinstance(iterated_values, (list, tuple)) \
                    and len(iterated_values) > self.capsul_iteration_step:
                value = iterated_values[self.capsul_iteration_step]
                setattr(iter_attributes, attribute, value)
        parameters = {'capsul_attributes': iter_attributes}
        for parameter in process.regular_parameters:
            parameters[parameter] = getattr(process, parameter)
        for parameter in process.iterative_parameters:
            parameters[parameter] \
                = getattr(process, parameter)[self.capsul_iteration_step]
        completion_model = CompletionModel.get_completion_model(
            process.process, self.name)
        completion_model.complete_parameters(process.process, parameters)


    @staticmethod
    def _iteration_factory(process, name):
        if not isinstance(process, ProcessIteration):
            return None
        return CompletionModelIteration(process, name)


CompletionModelFactory().register_factory(
    CompletionModelIteration._iteration_factory, 50000)


