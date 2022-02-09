# -*- coding: utf-8 -*-
'''
Utility class for iterated nodes in a pipeline. This is mainly internal infrastructure, which a normal programmer should not have to bother about.
A pipeline programmer will not instantiate :class:`ProcessIteration` directly, but rather use the :class:`~capsul.pipeline.pipeline.Pipeline` method :meth:`~capsul.pipeline.pipeline.Pipeline.add_iterative_process`.

Classes
=======
:class:`ProcessIteration`
-------------------------
'''

from __future__ import print_function

from __future__ import absolute_import
import sys
import six
from traits.api import List, Undefined

from capsul.process.process import Process
from capsul.study_config.process_instance import get_process_instance
import capsul.study_config as study_cmod
from traits.api import File, Directory
from six.moves import range

if sys.version_info[0] >= 3:
    xrange = range

class ProcessIteration(Process):

    _doc_path = 'api/pipeline.html#processiteration'

    def __init__(self, process, iterative_parameters, study_config=None,
                 context_name=None):
        super(ProcessIteration, self).__init__()

        if self.study_config is None and hasattr(Process, '_study_config'):
            study_config = study_cmod.default_study_config()
        if study_config is not None:
            self.study_config = study_config

        self.process = get_process_instance(process,
                                            study_config=study_config)

        if context_name is not None:
            self.process.context_name = context_name
        self.regular_parameters = set()
        self.iterative_parameters = set(iterative_parameters)

        # use the completion system (if any) to get induced (additional)
        # iterated parameters
        if study_config is not None:
            # don't import this at module level to avoid cyclic imports
            from capsul.attributes.completion_engine \
                import ProcessCompletionEngine

            completion_engine \
                = ProcessCompletionEngine.get_completion_engine(self)
            if hasattr(completion_engine, 'get_induced_iterative_parameters'):
                induced_iterative_parameters \
                    = completion_engine.get_induced_iterative_parameters()
                self.iterative_parameters.update(induced_iterative_parameters)
                iterative_parameters = self.iterative_parameters

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
        for name, trait in six.iteritems(user_traits):
            if name in iterative_parameters:
                kw = {}
                if trait.input_filename is False:
                    kw['input_filename'] = False
                self.add_trait(name, List(trait, output=trait.output,
                                          optional=trait.optional, **kw))
                if trait.groups:
                    self.trait(name).groups = trait.groups
                if trait.forbid_completion is not None:
                    # we don't have access to the pipeline or even the
                    # node in self, we cannot propagate the forbid_completion
                    # value outside of self.
                    # However this will be done in Pipeline.add_process() when
                    # inserting self in a pipeline, so this is OK.
                    trait(name).forbid_completion \
                        = trait.forbid_completion
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
        if parameter not in self.process.user_traits():
            raise ValueError('Cannot iterate on parameter %s '
              'that is not a parameter of process %s'
              % (parameter, self.process.id))

        is_iterative = parameter in self.iterative_parameters
        if is_iterative == iterative:
            return # nothing to be done
        if iterative is None:
            iterative = not is_iterative

        trait = self.process.trait(parameter)
        if iterative:

            # switch to iterative
            self.regular_parameters.remove(parameter)
            self.iterative_parameters.add(parameter)
            self.remove_trait(parameter)
            # Create iterative process parameter by copying process parameter
            # and changing iterative parameter to list
            self.add_trait(parameter, List(trait, output=trait.output,
                                      optional=trait.optional))
            if trait.groups:
                self.trait(parameter).groups = trait.groups

            # if it is an output, the output list has to be
            # resized according to inputs
            if trait.output:
                inputs = []
                for param in self.iterative_parameters:
                    if not self.process.trait(param).output:
                        inputs.append(param)
                self.on_trait_change(self._resize_outputs, inputs)

        else:

            # switch to non-iterative
            self.remove_trait(parameter)
            self.iterative_parameters.remove(parameter)
            self.regular_parameters.add(parameter)
            self.add_trait(parameter, trait)
            # copy initial value of the underlying process to self
            setattr(self, parameter, getattr(self.process, parameter))

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
            for iteration in range(size):
                for parameter in self.iterative_parameters:
                    #if not no_output_value or not self.trait(parameter).output:
                    value = getattr(self, parameter)
                    if len(value) > iteration:
                        setattr(self.process, parameter,
                                getattr(self, parameter)[iteration])
                # operate completion
                self.complete_iteration(iteration)
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
            for iteration in range(size):
                for parameter in self.iterative_parameters:
                    setattr(self.process, parameter,
                            getattr(self, parameter)[iteration])
                # operate completion
                self.complete_iteration(iteration)
                self.process()

    def set_study_config(self, study_config):
        super(ProcessIteration, self).set_study_config(study_config)
        self.process.set_study_config(study_config)

    def complete_iteration(self, iteration):
        # don't import this at module level to avoid cyclic imports
        from capsul.attributes.completion_engine import ProcessCompletionEngine

        completion_engine = ProcessCompletionEngine.get_completion_engine(
            self)
        # check if it is an iterative completion engine
        if hasattr(completion_engine, 'complete_iteration_step'):
            completion_engine.complete_iteration_step(iteration)
