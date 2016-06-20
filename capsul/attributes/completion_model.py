
from soma.singleton import Singleton
from soma.controller import Controller, ControllerTrait
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline import Graph, ProcessNode
import traits.api as traits
import six


class ProcessCompletionModel(traits.HasTraits):
    ''' Parameters completion from attributes for a process instance, in the
    context of a specific data organization.

    ProcessCompletionModel is pure virtual, and has to be subclassed for a data
    organization framework.
    '''

    def __init__(self, name=None):
        super(ProcessCompletionModel, self).__init__()
        self.name = name
        self.completion_ongoing = False


    def get_attributes(self, process):
        ''' Get attributes list associated to a process.

        The default implementation just returns
        get_attribute_values(process).keys()

        Returns
        -------
        attributes: list of strings, or generator
        '''
        return self.get_attribute_values(process).keys()


    def get_attribute_values(self, process):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller

        The default implementation does nothing for a
        single Process instance, and merges attributes from its children if
        the process is a pipeline.

        '''
        if isinstance(process, Pipeline):
            t = self.trait('capsul_attributes')
            if t is not None:
                return self.capsul_attributes

            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            attributes = self.capsul_attributes
            name = process.name

            for node_name, node in six.iteritems(process.nodes):
                if node_name == '':
                    continue
                if hasattr(node, 'process'):
                    subprocess = node.process
                    pname = '.'.join([name, node_name])
                    subprocess_compl = \
                        ProcessCompletionModel.get_completion_model(
                            subprocess, pname)
                    try:
                        sub_attributes = subprocess_compl.get_attribute_values(
                            subprocess)
                    except:
                        try:
                            self.get_attribute_values(subprocess)
                        except:
                            continue
                    for attribute, trait \
                            in six.iteritems(sub_attributes.user_traits()):
                        if attributes.trait(attribute) is None:
                            attributes.add_trait(attribute, trait)
                            setattr(attributes, attribute,
                                    getattr(sub_attributes, attribute))
            return attributes

        else:
            # not a pipeline: no default implementation
            raise AttributeError(
                "ProcessCompletionModel.get_attribute_values() "
                "is a pure virtual method.")


    def complete_parameters(self, process, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.

        Parameters
        ----------
        process: Process instance (mandatory)
            the process (or pipeline) to be completed
        process_inputs: dict (optional)
            parameters to be set on the process. It may include "regular"
            process parameters, and attributes used for completion. Attributes
            should be in a sub-dictionary under the key "capsul_attributes".
        '''
        self.set_parameters(process, process_inputs)
        # if process is a pipeline, trigger completions for its nodes and
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
        use_topological_order = True
        if isinstance(process, Pipeline):
            attrib_values = self.get_attribute_values(process).export_to_dict()
            name = process.name

            if use_topological_order:
                # proceed in topological order
                graph = process.workflow_graph()
                for node_name, node_meta in graph.topological_sort():
                    pname = '.'.join([name, node_name])
                    if isinstance(node_meta, Graph):
                        nodes = [node_meta.pipeline]
                    else:
                        nodes = node_meta
                    for pipeline_node in nodes:
                        if isinstance(pipeline_node, ProcessNode):
                            subprocess = pipeline_node.process
                        else:
                            subprocess = pipeline_node
                        subprocess_compl = \
                            ProcessCompletionModel.get_completion_model(
                                subprocess, pname)
                        try:
                            subprocess_compl.complete_parameters(
                                subprocess, {'capsul_attributes':
                                             attrib_values})
                        except:
                            try:
                                self.complete_parameters(
                                    subprocess, {'capsul_attributes':
                                                attrib_values})
                            except:
                                pass
            else:
                for node_name, node in six.iteritems(process.nodes):
                    if node_name == '':
                        continue
                    if hasattr(node, 'process'):
                        subprocess = node.process
                        pname = '.'.join([name, node_name])
                        subprocess_compl = \
                            ProcessCompletionModel.get_completion_model(
                                subprocess, pname)
                        try:
                            subprocess_compl.complete_parameters(
                                subprocess, {
                                    'capsul_attributes': attrib_values})
                        except:
                            try:
                                self.complete_parameters(
                                    subprocess, {'capsul_attributes':
                                                attrib_values})
                            except:
                                pass

        # now complete process parameters:
        attributes = self.get_attribute_values(process).export_to_dict()
        for pname in process.user_traits():
            try:
                value = self.attributes_to_path(process, pname, attributes)
                if value is not None:  # should None be valid ?
                    setattr(process, pname, value)
            except:
                pass


    def attributes_to_path(self, process, parameter, attributes):
        ''' Build a path from attributes for a given parameter in a process.
        '''
        return self.get_path_completion_model(process) \
            .attributes_to_path(process, parameter, attributes)


    def set_parameters(self, process, process_inputs):
        ''' Set the given parameters dict to the given process.
        process_inputs may include regular parameters of the underlying
        process, and attributes (capsul_attributes: dict).
        '''

        # This convenience method only differs from the Controller
        # import_from_dict() method in the way that capsul_attributes items
        # will not completely replace all the attributes values, but only set
        # those specified here, and leave the others in place.
        dst_attributes = self.get_attribute_values(process)
        attributes = process_inputs.get('capsul_attributes')
        if attributes:
            avail_attrib = set(dst_attributes.user_traits().keys())
            attributes = dict((k, v) for k, v in six.iteritems(attributes)
                              if k in avail_attrib)
            dst_attributes.import_from_dict(attributes)
        process_inputs = dict((k, v) for k, v
                              in six.iteritems(process_inputs)
                              if k != 'capsul_attributes')
        process.import_from_dict(process_inputs)


    def attributes_changed(self, process, obj, name, old, new):
        ''' Traits changed callback which triggers parameters update.

        This method basically calls complete_parameters() (after some checks).
        It is normally used as a traits notification callback for the
        attributes controller, so that changes in attributes will automatically
        trigger parameters completion for file paths.

        It can be plugged this way:

        ::
            from soma.functiontools import SomaPartial
            completion_model.get_attribute_values(process).on_trait_change(
                SomaPartial(completion_model.attributes_changed, process),
                'anytrait')

        Then it can be disabled this way:

        ::
            completion_model.get_attribute_values(process).on_trait_change(
                SomaPartial(completion_model.attributes_changed, process),
                'anytrait', remove=True)
        '''
        if name != 'trait_added' and name != 'user_traits_changed' \
                and self.completion_ongoing is False:
            #setattr(self.capsul_attributes, name, new)
            self.completion_ongoing = True
            self.complete_parameters(process,
                                     {'capsul_attributes': {name: new}})
            self.completion_ongoing = False


    def get_path_completion_model(self, process):
        ''' Get a PathCompletionModel object for the given process.
        The default implementation queries PathCompletionModelFactory,
        but some specific ProcessCompletionModel implementations may override
        it for path completion at the process level (FOMs for instance).
        '''
        # FIXME: PathCompletionModelFactory instance problem
        return PathCompletionModelFactory().get_path_completion_model(process)


    @staticmethod
    def get_completion_model(process, name=None):
        ''' Get a ProcessCompletionModel instance for a given process within
        the framework of its StudyConfig: factory function.

        Same as ProcessCompletionModelFactory().get_completion_model(
            process, process.get_study_config(), name=name)
        '''
        return ProcessCompletionModelFactory().get_completion_model(
            process, process.get_study_config(), name=name)


class PathCompletionModel(object):
    ''' Implements building of a single path from a set of attributes for a
    specific process / parameter
    '''
    def attributes_to_path(self, process, parameter, attributes):
        ''' Build a path from attributes for a given parameter in a process.

        This method has to be specialized. The default implementation returns
        None.
        '''
        return None



class ProcessCompletionModelFactory(Singleton):
    '''
    '''
    def __singleton_init__(self):
        super(ProcessCompletionModelFactory, self).__init__()
        self.factories = {100000: [self._default_factory]}


    def get_completion_model(self, process, study_config=None, name=None):
        '''
        Factory for ProcessCompletionModel: get an ProcessCompletionModel
        instance for a process in the context of a given StudyConfig.

        The study_config should specify which completion system(s) is (are)
        used (FOM, ...)
        If nothing is configured, a ProcessCompletionModel base instance will
        be returned. It will not be able to perform completion at all, but will
        conform to the API.
        '''
        if hasattr(process, 'completion_model'):
            return process.completion_model
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

        for priority in sorted(self.factories.keys()):
            factories = self.factories[priority]
            for factory in factories:
                completion_model = factory(process, name)
                if completion_model is not None:
                    return completion_model
        raise RuntimeError('No factory could produce a ProcessCompletionModel '
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
    def _default_factory(process, name):
        return ProcessCompletionModel(name)


class PathCompletionModelFactory(object):

  def get_path_completion_model(self, process):
      raise RuntimeError('PathCompletionModelFactory is pure virtual. '
                         'It must be derived to do actual work.')

