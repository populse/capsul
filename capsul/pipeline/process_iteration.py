# -*- coding: utf-8 -*-
'''
Utility class for iterated nodes in a pipeline. This is mainly internal infrastructure, which a normal programmer should not have to bother about.
A pipeline programmer will not instantiate :class:`ProcessIteration` directly, but rather use the :class:`~capsul.pipeline.pipeline.Pipeline` method :meth:`~capsul.pipeline.pipeline.Pipeline.add_iterative_process`.

Classes
=======
:class:`ProcessIteration`
-------------------------
'''

from soma.controller import undefined

from capsul.process.process import Process

class ProcessIteration(Process):

    _doc_path = 'api/pipeline.html#processiteration'

    def __init__(self, definition, process, iterative_parameters, 
                 context_name=None):
        # Avoid circular import
        from capsul.api import executable

        super(ProcessIteration, self).__init__(definition=definition)

        self.process = executable(process)

        if context_name is not None:
            self.process.context_name = context_name
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)

        # Check that all iterative parameters are valid process parameters
        inputs = []
        for parameter in self.iterative_parameters:
            if self.process.field(parameter) is None:
                raise ValueError('Cannot iterate on parameter %s '
                  'that is not a parameter of process %s'
                  % (parameter, self.process.id))
            if not self.process.field(parameter).is_output():
                inputs.append(parameter)

        # Create iterative process parameters by copying process parameter
        # and changing iterative parameters to list
        for field in self.process.user_fields():
            name = field.name
            if name in iterative_parameters:
                self.add_list_proxy(name, self.process, name)
            else:
                self.regular_parameters.add(name)
                self.add_proxy(name, self.process, name)
            parameter = {
                "name": name,
                "output": field.is_output(),
                "optional": field.optional,
                "has_default_value": field.has_default(),
            }
            # generate plug with input parameter and identifier name
            self._add_plug(parameter)

        self.metadata_schema = getattr(self.process, 'metadata_schema', {})

    def change_iterative_plug(self, parameter, iterative=None):
        '''
        Change a parameter to be iterative (or non-iterative)

        Parameters
        ----------
        parameter: str
            parameter name
        iterative: bool or None
            if None, the iterative state will be toggled. If True or False, the
            parameter state will be set accordingly.
        '''
        if self.process.field(parameter) is None:
            raise ValueError('Cannot iterate on parameter %s '
              'that is not a parameter of process %s'
              % (parameter, self.process.id))

        is_iterative = parameter in self.iterative_parameters
        if is_iterative == iterative:
            return # nothing to be done
        if iterative is None:
            iterative = not is_iterative

        field = self.process.field(parameter)
        if iterative:
            # switch to iterative
            self.regular_parameters.remove(parameter)
            self.iterative_parameters.add(parameter)
            self.remove_field(parameter)
            self.add_list_proxy(parameter, self.process, parameter)
        else:
            # switch to non-iterative
            self.remove_field(parameter)
            self.iterative_parameters.remove(parameter)
            self.regular_parameters.add(parameter)
            self.add_proxy(parameter, self.process, parameter)

    def iteration_size(self):
        # Check that all iterative parameter value have the same size
        # or are undefined
        size = None
        for parameter in self.iterative_parameters:
            value = getattr(self, parameter, undefined)
            if value is undefined:
                continue
            psize = len(value)
            if size is None:
                size = psize
            else:
                if size != psize:
                   raise ValueError('Iterative parameter values must be lists of the same size: %s' % ','.join('%s=%d' % (n, len(getattr(self,n))) for n in self.iterative_parameters))
        return size
    
    def iterate_over_process_parmeters(self):
        size = self.iteration_size()
        if size is None:
            return
        for iteration_index in range(size):
            self.select_iteration_index(iteration_index)
            yield self.process
    
    def select_iteration_index(self, iteration_index):
        for parameter in self.regular_parameters:
            setattr(self.process, parameter, getattr(self, parameter, undefined))
        for parameter in self.iterative_parameters:
            values = getattr(self, parameter, undefined)
            if values is not undefined and len(values) > iteration_index:
                value = values[iteration_index]
            else:
                value = undefined
            setattr(self.process, parameter, value)

    def json(self, include_parameters=True):
        result = {
            'type': 'iterative_process',
            'definition': {
                'definition': self.definition,
                'process': self.process.json(include_parameters=False),
                'iterative_parameters': list(self.iterative_parameters),
                'context_name': getattr(self.process, 'context_name', None),
            },
            'uuid': self.uuid,
        }
        if include_parameters:
            result['parameters'] = super(Process,self).json()
        return result
