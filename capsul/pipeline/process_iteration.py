# -*- coding: utf-8 -*-
'''
Utility class for iterated nodes in a pipeline. This is mainly internal infrastructure, which a normal programmer should not have to bother about.
A pipeline programmer will not instantiate :class:`ProcessIteration` directly, but rather use the :class:`~capsul.pipeline.pipeline.Pipeline` method :meth:`~capsul.pipeline.pipeline.Pipeline.add_iterative_process`.

Classes
=======
:class:`ProcessIteration`
-------------------------
'''

from soma.controller import undefined, Union

from capsul.process.process import Process
import capsul.application

class ProcessIteration(Process):

    _doc_path = 'api/pipeline.html#processiteration'

    def __init__(self, definition, process, iterative_parameters, 
                 context_name=None):
        super(ProcessIteration, self).__init__(definition=definition)

        self.process = capsul.application.executable(process)

        if context_name is not None:
            self.process.context_name = context_name
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)

        # Check that all iterative parameters are valid process parameters
        has_output = False
        inputs = []
        for parameter in self.iterative_parameters:
            if self.process.field(parameter) is None:
                raise ValueError('Cannot iterate on parameter %s '
                  'that is not a parameter of process %s'
                  % (parameter, self.process.id))
            if self.process.field(parameter).is_output():
                has_output = True
            else:
                inputs.append(parameter)

        # Create iterative process parameters by copying process parameter
        # and changing iterative parameters to list
        for field in self.process.user_fields():
            name = field.name
            if name in iterative_parameters:
                # allow undefined values in this list
                self.add_field(
                    name,
                    list[Union[field.type, type(undefined)]],
                    metadata=field.metadata())
                value = getattr(self.process, name, undefined)
                if value is not undefined:
                    setattr(self, name, [value])

            else:
                self.regular_parameters.add(name)
                self.add_field(name, field)
                # copy initial value of the underlying process to self
                # Note: should be this be done via a links system ?
                setattr(self, name, getattr(self.process, name, undefined))


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
            # Create iterative process parameter by copying process parameter
            # and changing iterative parameter to list
            self.add_field(parameter,
                           Union[list[field.type], type(undefined)],
                           metadata=field.metadata(),
                           default_factory=list)

            # if it is an output, the output list has to be
            # resized according to inputs
            if field.is_output():
                inputs = []
                for param in self.iterative_parameters:
                    if not self.process.field(param).is_output():
                        inputs.append(param)
                self.on_attribute_change(self._resize_outputs, inputs)

        else:

            # switch to non-iterative
            self.remove_field(parameter)
            self.iterative_parameters.remove(parameter)
            self.regular_parameters.add(parameter)
            self.add_field(parameter, field)
            # copy initial value of the underlying process to self
            setattr(self, parameter,
                    getattr(self.process, parameter, undefined))

    def iterate_over_process_parmeters(self):
        # Check that all iterative parameter value have the same size
        # or are undefined
        no_output_value = None
        size = None
        size_error = False
        for parameter in self.iterative_parameters:
            field = self.field(parameter)
            value = getattr(self, parameter, undefined)
            if value is undefined:
                continue
            psize = len(value)
            if psize and (not field.is_output()
                          or len([x for x in value
                                  if x in ('', undefined, None)]) == 0):
                if size is None:
                    size = psize
                elif size != psize:
                    size_error = True
                    break
                if field.is_output():
                    if no_output_value is None:
                        no_output_value = False
                    elif no_output_value:
                        size_error = True
                        break
            else:
                if field.is_output():
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
        for iteration in range(size):
            for parameter in self.iterative_parameters:
                values = getattr(self, parameter, undefined)
                if values is not undefined and len(values) > iteration:
                    value = values[iteration]
                else:
                    value = undefined
                setattr(self.process, parameter, value)
            yield self.process
    
    def json(self):
        return {
            'type': 'iterative_process',
            'definition': {
                'definition': self.definition,
                'process': self.process.json(),
                'iterative_parameters': list(self.iterative_parameters),
                'context_name': getattr(self.process, 'context_name', None),
            }
        }

