##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from __future__ import print_function

# System import
import six

# CAPSUL import
from capsul.api import Process, Pipeline

# soma-base imports
from soma.controller import Controller, ControllerTrait
from soma.sorted_dictionary import SortedDictionary
from soma.singleton import Singleton


class AttributedProcess(Process):
    '''
    A Process with alternative attributes representation for some of its
    parameters.

    Attributes are a way to convert from/to file names through a database-like
    description.

    Some of the File parameters of a process can be deduced from its
    attributes.

    Attributes are stored in an additional parameter (Controller):
    "capsul_attributes", but normally accessed via the
    get_attributes_controller() method.

    AttributedProcess is mainly a "pure virtual" class, and has to be inherited
    to implement some completion strategies: the way attributes are used to
    build file names is not hard-coded in this class.
    '''
    capsul_attributes = ControllerTrait(Controller())


    def __init__(self, process, study_config, name=None):
        ''' Build an AttributedProcess instance from an existing Process
        instance and a StudyConfig.
        '''
        super(AttributedProcess, self).__init__()
        self.process = process
        self.study_config = study_config
        if name is None:
            self.name = process.name
        else:
            self.name = name
        self.completion_ongoing = False


    def __getattr__(self, attribute):
        ''' __getattr__() is overloaded to make a proxy for the underlying
        process.
        '''
        if 'process' not in self.__dict__:
            # in case it is invoked before process is setup in self
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, attribute))
        process = self.process
        return getattr(process, attribute)


    def __setattr__(self, attribute, value):
        ''' __setattr__() is overloaded to make a proxy for the underlying
        process.
        '''
        if attribute in self.__dict__:
            super(AttributedProcess, self).__setattr__(attribute, value)
            return
        if 'process' in self.__dict__:
            process = self.process
            if hasattr(process, attribute):
                setattr(process, attribute, value)
                return
        # not in proxy: set the variable to self
        super(AttributedProcess, self).__setattr__(attribute, value)


    def user_traits(self):
        ''' user_traits() is overloaded to make a proxy for the underlying
        process.
        '''
        traits = SortedDictionary()
        traits.update(super(AttributedProcess, self).user_traits())
        traits.update(self.process.user_traits())
        return traits


    def trait(self, trait_name):
        ''' trait() is overloaded to make a proxy for the underlying
        process.
        '''
        tr = super(AttributedProcess, self).trait(trait_name)
        if tr is None:
            tr = self.process.trait(trait_name)
        return tr


    def set_parameters(self, process_inputs):
        ''' Set the given parameters dict to the current process.
        process_inputs may include regular parameters of the underlying
        process, and attributes (capsul_attributes: dict).

        This convenience method only differs from the Controller
        import_from_dict() method in the way that capsul_attributes items
        will not completely replace the all attributes values, but only set
        those specified here, and leave the others in place.
        '''
        attributes = process_inputs.get('capsul_attributes')
        if attributes:
            # calling directly self.import_from_dict() will erase existing
            # attributes
            self.capsul_attributes.import_from_dict(attributes)
            process_inputs = dict((k, v) for k, v
                                  in six.iteritems(process_inputs)
                                  if k != 'capsul_attributes')
        self.import_from_dict(process_inputs)


    def complete_parameters(self, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.

        The default implementation in AttributedProcess does nothing for a
        single Process instance, and calls complete_parameters() on subprocess
        nodes if the process is a pipeline.
        '''
        self.set_parameters(process_inputs)
        # if process is a pipeline, create completions for its nodes and
        # sub-pipelines.
        #
        # Note: for now we do so first, so that parameters can be overwritten
        # afterwards by the higher-level pipeline FOM.
        # Ideally we should process the other way: complete high-level,
        # specific parameters first, then complete with lower-level, more
        # generic ones, while blocking already set ones.
        # as this blocking mechanism does not exist yet, we do it this way for
        # now, but it is sub-optimal since many parameters will be set many
        # times.
        if isinstance(self.process, Pipeline):
            name = self.name
            for node_name, node in six.iteritems(self.process.nodes):
                if node_name == '':
                    continue
                if hasattr(node, 'process'):
                    subprocess = node.process
                    pname = '.'.join([name, node_name])
                    subprocess_attr \
                        = AttributedProcessFactory().get_attributed_process(
                            subprocess, self.study_config, pname)
                    try:
                        #self.process_completion(subprocess, pname)
                        subprocess_attr.complete_parameters(
                            {'capsul_attributes':
                             self.capsul_attributes.export_to_dict()})
                    except Exception as e:
                        if verbose:
                            print('warning, node %s could not complete FOM' \
                                  % node_name)
                            print(e)


    def path_attributes(self, filename, parameter=None):
        ''' Get attributes from a path (file) name for a given parameter.

        The default implementation in AttributedProcess does nothing. Consider
        it as a "pure virtual" method.

        Returns
        -------
        attributes: dict
            dictionary of attributes parsed from the path name, ex:
            {'center': 'my_center', 'subject': 'ABCD',
             'acquisition': 'default_acquisition'}
        '''
        pass


    def get_attributes_controller(self):
        ''' Get a list of needed attributes for this process.

        Returns
        -------
        attributes: Controller instance
        '''
        return self.capsul_attributes


    def attributes_changed(self, obj, name, old, new):
        ''' Traits changed callback which triggers parameters update.

        This method basically calls complete_parameters() (after some checks).
        It is normally used as a traits notification callback for the
        attributes controller, so that changes in attributes will automatically
        trigger parameters completion for file paths.

        It can be plugged this way:

        ::
            attributed_process.get_attributes_controller().on_trait_change(
                attributed_process.attributes_changed, 'anytrait')

        Then it can be disabled this way:

        ::
            attributed_process.get_attributes_controller().on_trait_change(
                attributed_process.attributes_changed, 'anytrait', remove=True)
        '''
        if name != 'trait_added' and name != 'user_traits_changed' \
                and self.completion_ongoing is False:
            #setattr(self.capsul_attributes, name, new)
            self.completion_ongoing = True
            self.complete_parameters({'capsul_attributes': {name: new}})
            self.completion_ongoing = False


class AttributedProcessFactory(Singleton):
    '''
    '''
    def __singleton_init__(self):
        super(AttributedProcessFactory, self).__init__()
        self.factories = {100000: [self._default_factory]}


    def get_attributed_process(self, process, study_config, name=None):
        '''
        Factory for AttributedProcess: get an AttributedProcess instance for a
        process in the context of a given StudyConfig.

        The study_config should specify which completion system(s) is (are)
        used (FOM, ...)
        If nothing is configured, an AttributedProcess base instance will be
        returned. It will not be able to perform completion at all, but will
        conform to the API.
        '''
        for priority in sorted(self.factories.keys()):
            factories = self.factories[priority]
            for factory in factories:
                attributed_process = factory(process, study_config, name)
                if attributed_process is not None:
                    return attributed_process
        raise RuntimeError('No factory could produce an AttributedProcess '
            'instance for the process %s. This is a bug, it should not happen.'
            %process.id)


    def register_factory(self, factory_function, priority):
        '''
        '''
        self.unregister_factory(factory_function)
        self.factories.setdefault(priority, []).append(factory_function)


    def unregister_factory(self, factory_function):
        '''
        '''
        for priority, factories in six.iteritems(self.factories):
            if factory_function in factories:
                factory_function.remove(factory_function)


    @staticmethod
    def _default_factory(process, study_config, name):
        return AttributedProcess(process, study_config, name)

