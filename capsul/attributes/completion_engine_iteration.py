# -*- coding: utf-8 -*-
'''
:class:`~capsul.attributes.completion_engine.ProcessCompletionEngine` dealing with process iterations.
This is an internal machinery.

Classes
=======
:class:`ProcessCompletionEngineIteration`
-----------------------------------------
'''

from capsul.pipeline.process_iteration import ProcessIteration
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    ProcessCompletionEngineFactory
from capsul.attributes.attributes_schema import ProcessAttributes
from soma.controller import Controller, undefined
import sys


class ProcessCompletionEngineIteration(ProcessCompletionEngine):
    '''
    :class:`~capsul.attributes.completion_engine.ProcessCompletionEngine`
    specialization for iterative process.

    Iterated attributes are given by get_iterated_attributes().
    Completion performs a single iteration step, stored in
    self.capsul_iteration_step
    '''
    def __init__(self, process, name=None):
        super(ProcessCompletionEngineIteration, self).__init__(
            process=process, name=name)
        #self.add_field('capsul_iteration_step', int, default=0)
        self.capsul_iteration_step = 0
        #self.iterated_attributes = self.get_iterated_attributes()


    def get_iterated_attributes(self):
        '''
        '''
        process = self.process
        try:
            pattributes = ProcessCompletionEngine.get_completion_engine(
                process.process).get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return []
        param_attributes = pattributes.get_parameters_attributes()
        attribs = set()
        for parameter in process.iterative_parameters:
            attribs.update(list(param_attributes.get(parameter, {}).keys()))
        # if no iterative parameter has been declared, use all attributes
        if not process.iterative_parameters:
            return set(f.name for f in pattributes.fields())
        return [f.name for f in pattributes.fields() if f.name in attribs]


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
        process = self.process
        pattributes = ProcessCompletionEngine.get_completion_engine(
            process.process).get_attribute_values()
        param_attributes = pattributes.get_parameters_attributes()
        induced_params = []
        for field in process.process.user_fields():
            parameter = field.name
            if parameter not in process.iterative_parameters:
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
        if self.field('capsul_attributes') is None:
            process = self.process
            try:
                pattributes = ProcessCompletionEngine.get_completion_engine(
                    process.process).get_attribute_values()
            except AttributeError:
                # ProcessCompletionEngine not implemented for this process:
                # no completion
                return

            schemas = self._get_schemas()
            attributes = ProcessAttributes(self.process, schemas)

            self.add_field('capsul_attributes', Controller,
                           default_factory=Controller)
            self.capsul_attributes = attributes
            iter_attrib = self.get_iterated_attributes()
            for field in pattributes.fields():
                attrib = field.name
                if attrib not in iter_attrib:
                    attributes.add_field(attrib, field)
            for attrib in iter_attrib:
                field = pattributes.field(attrib)
                if field is not None:
                    attributes.field(
                        attrib, list[field.type], output=field.is_output())
                value = getattr(pattributes, attrib, None)
                if value is not None and value is not undefined:
                    setattr(attributes, attrib, [value])
        return self.capsul_attributes


    def iteration_size(self, process_inputs={}):
        process = self.process
        try:
            attributes_set = self.get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return

        # attributes lists sizes
        sizes = [len(getattr(attributes_set, attribute))
                 for attribute in self.get_iterated_attributes()]
        if sizes:
            size = max(sizes)
        else:
            size = 0
        sizes = []
        for param in process.iterative_parameters:
            value = process_inputs.get(param)
            if value is not None:
                sizes.append(len(value))
            else:
                value = getattr(process, param)
                if value:
                    sizes.append(len(value))

        if sizes:
            psize = max(sizes)
        else:
            psize = 0
        size = max(size, psize)

        return size


    def complete_parameters(self, process_inputs={},
                            complete_iterations=True):

        if not complete_iterations:
            # then do nothing...
            return

        self.completion_progress = 0.

        process = self.process

        try:
            self.set_parameters(process_inputs)
            attributes_set = self.get_attribute_values()
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                process.process, self.name)
            step_attributes = completion_engine.get_attribute_values()
        except AttributeError:
            # ProcessCompletionEngine not implemented for this process:
            # no completion
            return

        size = self.iteration_size()

        iterated_attributes = self.get_iterated_attributes()
        for attribute in attributes_set.fields():
            if attribute not in iterated_attributes:
                setattr(step_attributes, attribute,
                        getattr(attributes_set, attribute, undefined))
        parameters = {}
        for parameter in process.regular_parameters:
            parameters[parameter] = getattr(process, parameter)

        # complete each step to get iterated parameters.
        # This is generally "too much" but it's difficult to perform a partial
        # completion only on iterated parameters

        iterative_parameters = dict(
            [(key, []) for key in process.iterative_parameters])

        self.completion_progress_total = size
        for it_step in range(size):
            self.capsul_iteration_step = it_step
            for attribute in iterated_attributes:
                iterated_values = getattr(attributes_set, attribute)
                step = min(len(iterated_values) - 1, it_step)
                value = iterated_values[step]
                setattr(step_attributes, attribute, value)
            for parameter in process.iterative_parameters:
                values = getattr(process, parameter)
                if isinstance(values, list) and len(values) > it_step:
                    parameters[parameter] = values[it_step]
            completion_engine.complete_parameters(
                parameters, complete_iterations=complete_iterations)
            for parameter in process.iterative_parameters:
                value = getattr(process.process, parameter)
                iterative_parameters[parameter].append(value)
            self.completion_progress = it_step + 1
        for parameter, values in iterative_parameters.items():
            try:
                setattr(process, parameter, values)
            except Exception as e:
                print('assign iteration parameter', parameter, ':\n', e,
                      file=sys.stderr)


    def complete_iteration_step(self, step):
        ''' Complete the parameters on the iterated process for a given
        iteration step.
        '''
        process = self.process
        try:
            attributes_set = self.get_attribute_values()
            completion_engine = ProcessCompletionEngine.get_completion_engine(
                process.process, self.name)
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
        for field in attributes_set.fields():
            attribute = field.name
            if attribute not in iterated_attributes:
                setattr(step_attributes, attribute,
                        getattr(attributes_set, attribute, undefined))
        parameters = {}
        for parameter in process.regular_parameters:
            parameters[parameter] = getattr(process, parameter)
        for parameter in process.iterative_parameters:
            values = getattr(process, parameter)
            if len(values) > self.capsul_iteration_step:
                parameters[parameter] = values[self.capsul_iteration_step]
        completion_engine.complete_parameters(parameters)
