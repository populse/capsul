##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.process.attributed_process import AttributedProcess, \
    AttributedProcessFactory
from capsul.pipeline.process_iteration import ProcessIteration
from soma.controller import Controller
import traits.api as traits


class AttributedProcessIteration(AttributedProcess):
    ''' AttributedProcess specialization for iterative process.

    Iterated attributes are given by get_iterated_attributes().
    Completion performs a single iteration step, stored in
    self.capsul_iteration_step
    '''
    def __init__(self, process, study_config, name=None):
        super(AttributedProcessIteration, self).__init__(process, study_config,
                                                         name)
        self.add_trait('capsul_iteration_step', traits.Int(0))
        self.iterated_attributes = self.get_iterated_attributes()


    def get_iterated_attributes(self):
        '''
        '''
        # How do we provide that ?
        # Subclassing ?
        # Lookup in a table / sub object ?
        # Use a FOM-like description by process ?
        return []


    def complete_parameters(self, process_inputs={}):
        self.set_parameters(process_inputs)
        attributes_set = self.get_attributes_controller()
        # duplicate attributes before modification
        iter_attributes = Controller(attributes_set)
        for attribute in self.iterated_attributes:
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
        for parameter in self.process.regular_parameters:
            parameters[parameter] = getattr(self.process, parameter)
        for parameter in self.process.iterative_parameters:
            parameters[parameter] \
                = getattr(self.process, parameter)[self.capsul_iteration_step]
        attributed_process = AttributedProcessFactory().get_attributed_process(
            self.process.process, self.study_config, self.name)
        attributed_process.complete_parameters(parameters)


    @staticmethod
    def _iteration_factory(process, study_config, name):
        if not isinstance(process, ProcessIteration):
            return None
        return AttributedProcessIteration(process, study_config, name)


AttributedProcessFactory().register_factory(
    AttributedProcessIteration._iteration_factory, 50000)


