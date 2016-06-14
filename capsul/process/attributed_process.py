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
from capsul.process.process import Process
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.topological_sort import Graph
from capsul.attributes.completion_model \
    import CompletionModel, CompletionModelFactory

# soma-base imports
from soma.controller import Controller, ControllerTrait
from soma.sorted_dictionary import SortedDictionary
from soma.singleton import Singleton


class AttributedProcess(Process, CompletionModel):
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

    def __init__(self, process, completion_model, name=None):
        ''' Build an AttributedProcess instance from an existing Process
        instance and a StudyConfig.
        '''
        super(AttributedProcess, self).__init__()
        self.process = process
        self.completion_model = completion_model
        self.add_trait('capsul_attributes', ControllerTrait(Controller()))
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


    def get_attributes(self, process):
        ''' Get attributes list associated to a process

        Returns
        -------
        attributes: list of strings
        '''
        return self.completion_model.get_attributes(process)


    def get_attribute_values(self, process):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        return self.completion_model.get_attribute_values(process)


    def complete_parameters(self, process, process_inputs={}):
        return self.completion_model.complete_parameters(process,
                                                         process_inputs)


    def get_attributes_controller(self):
        ''' Get a list of needed attributes for this process.

        Returns
        -------
        attributes: Controller instance
        '''
        return self.capsul_attributes


    def get_nodes_attributes_controller(self):
        ''' Get a controller merging needed attributes for a pipeline sub-
        nodes. This is a convenience method that can be used in some pipelines
        but is not useful in all pipelines (some will completely overwrite
        their elements attributes).
        If the underlying process is not a pipeline, returns an empty
        controller.
        '''
        acontroller = Controller()
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
                            subprocess, self.process.study_config, pname)
                    sub_controller \
                        = subprocess_attr.get_attributes_controller()
                    self.merge_controllers(acontroller, sub_controller)
        return acontroller


    @staticmethod
    def merge_controllers(dest_controller, src_controller):
        ''' Utility function: merge 2 controllers

        Parameters
        ----------
        dest_controller: Controller
            destination: src_controller is added to dest_controller, which is
            modified during the operation
        src_controller: Controller
            source controller to be merged into dest_controller
        '''
        names = set(dest_controller.user_traits().keys())
        # merge traits
        for name, trait in six.iteritems(src_controller.user_traits()):
            if name not in names:
                names.add(name)
                dest_controller.add_trait(name, trait)
                setattr(dest_controller, name, getattr(src_controller, name))


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


    def get_attributed_process(self, process, study_config=None, name=None):
        '''
        Factory for AttributedProcess: get an AttributedProcess instance for a
        process in the context of a given StudyConfig.

        The study_config should specify which completion system(s) is (are)
        used (FOM, ...)
        If nothing is configured, an AttributedProcess base instance will be
        returned. It will not be able to perform completion at all, but will
        conform to the API.
        '''
        if study_config is not None:
            if process.get_study_config() is None:
                process.set_study_config(study_config)
            elif study_config is not process.get_study_config():
                raise ValueError('Mismatching StudyConfig in process (%s) and '
                    'get_attributed_process() (%s)\nin process:\n%s\n'
                    'passed:\n%s'
                    % (repr(process.get_study_config()), repr(study_config),
                      repr(process.get_study_config().export_to_dict()),
                      repr(study_config.export_to_dict())))
        completion_model = CompletionModel.get_completion_model(process, name)
        return AttributedProcess(process, completion_model)

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
        completion_model = CompletionModel.get_completion_model(process, name)
        return AttributedProcess(process, completion_model, name)

