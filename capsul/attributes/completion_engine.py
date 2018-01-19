
from __future__ import print_function
from soma.singleton import Singleton
from soma.controller import Controller, ControllerTrait
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline import Graph, ProcessNode, Switch
from capsul.attributes.attributes_factory import AttributesFactory
from capsul.attributes.attributes_schema import ProcessAttributes, \
    EditableAttributes
import traits.api as traits
from soma.utils.weak_proxy import weak_proxy, get_ref
from soma.functiontools import SomaPartial
import six
import sys

if sys.version_info[0] >= 3:
    unicode = str


class ProcessCompletionEngine(traits.HasTraits):
    ''' Parameters completion from attributes for a process instance, in the
    context of a specific data organization.

    ProcessCompletionEngine can be used directly for a pipeline, which merely
    delegates completion to its nodes, and has to be subclassed for a data
    organization framework on a process.

    To get a completion engine, use:

    ::

        completion_engine = ProcessCompletionEngine.get_completion_engine(
            process, name)

    Note that this will assign permanently the ProcessCompletionEngine object
    to its associated process.
    To get and set the attributes set:

    ::

        attributes = completion_engine.get_attribute_values()
        print(attributes.user_traits().keys())
        attributes.specific_process_attribute = 'a value'

    Once attributes are set, to process with parameters completion:

    ::

        completion_engine.complete_parameters()

    It is possible to have complete_parameters() triggered automatically when attributes or switch nodes change. To set this up, use:

    ::

        completion_engine.install_auto_completion()

    ProcessCompletionEngine can (and should) be specialized, at least to
    provide the attributes set for a given process. A factory is used to create
    the correct type of ProcessCompletionEngine for a given process / name:
    :py:class:`ProcessCompletionEngineFactory`

    :py:class:`capsul.attributes.fom_completion_engine.FomProcessCompletionEngine` is a specialization of ``ProcessCompletionEngine`` to manage File Organization Models (FOM).

    Methods
    -------

    get_completion_engine
    get_attribute_values
    complete_parameters
    set_parameters
    attributes_to_path
    get_path_completion_engine
    install_auto_completion
    remove_auto_completion

    '''

    def __init__(self, process, name=None):
        super(ProcessCompletionEngine, self).__init__(
            process=process, name=name)
        self.process = weak_proxy(process, self._clear_process)
        self.name = name
        self.completion_ongoing = False
        self.add_trait('completion_progress', traits.Float(0.))
        self.add_trait('completion_progress_total', traits.Float(1.))
        self._rebuild_attributes = False


    def __del__(self):
        self.remove_switch_observers()
        self.remove_auto_completion()


    def _clear_process(self, wr):
        '''Called when the object behind the self.process proxy is about
        to be deleted
        '''
        self.process = None
    
    def get_attribute_values(self):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: ProcessAttributes instance

        The default implementation does nothing for a
        single Process instance, and merges attributes from its children if
        the process is a pipeline.

        '''
        if not self._rebuild_attributes \
                and self.trait('capsul_attributes') is not None \
                and hasattr(self, 'capsul_attributes'):
            return self.capsul_attributes

        schemas = self._get_schemas()

        study_config = self.process.get_study_config()
        proc_attr_cls = ProcessAttributes

        if 'AttributesConfig' in study_config.modules:
            factory = study_config.modules_data.attributes_factory
            names = [self.process.name]
            if hasattr(self.process, 'context_name'):
                names.insert(0, self.process.context_name)
            for name in names:
                try:
                    proc_attr_cls = factory.get('process_attributes', name)
                    found = True
                    break
                except ValueError:
                    pass

        if not hasattr(self, 'capsul_attributes'):
            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            self.capsul_attributes = proc_attr_cls(self.process, schemas)
        self._rebuild_attributes = False

        # if no specialized attributes set and process is a pipeline,
        # try building from children nodes
        if proc_attr_cls is ProcessAttributes \
                and isinstance(self.process, Pipeline):
            attributes = self.capsul_attributes
            name = getattr(self.process, 'context_name', self.process.name)

            for node_name, node in six.iteritems(self.process.nodes):
                if node_name == '':
                    continue
                subprocess = None
                if hasattr(node, 'process'):
                    subprocess = node.process
                elif isinstance(node, Switch):
                    subprocess = node
                if subprocess is not None:
                    pname = '.'.join([name, node_name])
                    subprocess_compl = \
                        ProcessCompletionEngine.get_completion_engine(
                            subprocess, pname)
                    try:
                        sub_attributes \
                            = subprocess_compl.get_attribute_values()
                    except:
                        try:
                            subprocess_compl = self.__class__(subprocess)
                            sub_attributes \
                                = subprocess_compl.get_attribute_values()
                        except:
                            continue
                    for attribute, trait \
                            in six.iteritems(sub_attributes.user_traits()):
                        if attributes.trait(attribute) is None:
                            attributes.add_trait(attribute, trait)
                            setattr(attributes, attribute,
                                    getattr(sub_attributes, attribute))

            self._get_linked_attributes()

        return self.capsul_attributes


    def _get_linked_attributes(self):
        # for parameters which still do not have attributes, we can try
        # using links: if a linked parameter in a sub-process has
        # attributes, then we can get them here.
        attributes = self.capsul_attributes
        schema = 'link'  # FIXME
        param_attributes = attributes.get_parameters_attributes()
        forbidden_attributes = set(['generated_by_parameter',
                                    'generated_by_process'])
        done_parameters = set(
            [p for p, al in six.iteritems(param_attributes)
              if len([a for a in al if a not in forbidden_attributes])
              != 0])
        traits_types = {str: traits.Str, unicode: traits.Str, int: traits.Int,
                        float: traits.Float, list: traits.List}
        name = self.process.name
        for pname, trait in six.iteritems(self.process.user_traits()):
            if pname in done_parameters:
                continue
            plug = self.process.pipeline_node.plugs.get(pname)
            if plug is None:
                continue
            if trait.output:
                links = plug.links_from
            else:
                links = plug.links_to
            for link in links:
                node = link[2]
                if hasattr(node, 'process'):
                    process = node.process
                else:
                    process = node
                completion_engine \
                    = ProcessCompletionEngine.get_completion_engine(
                        process, '.'.join([name, link[0]]))
                sub_attributes = completion_engine.get_attribute_values()
                sub_p_attribs = sub_attributes.get_parameters_attributes()
                if link[1] in sub_p_attribs:
                    s_p_attributes = sub_p_attribs[link[1]]
                    if len(s_p_attributes) != 0 \
                            and len([x for x in s_p_attributes.keys()
                                    if x not in forbidden_attributes]) != 0:
                        ea = EditableAttributes()
                        for attribute, value in six.iteritems(
                                s_p_attributes):
                            if attribute not in forbidden_attributes:
                                ttype = traits_types.get(type(value))
                                if ttype is not None:
                                    trait = ttype()
                                else:
                                    trait = value
                                ea.add_trait(attribute, ttype)
                                setattr(ea, attribute, value)

                        attributes.set_parameter_attributes(
                            pname, schema, ea, {})

                    break


    def complete_parameters(self, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.

        Parameters
        ----------
        process_inputs: dict (optional)
            parameters to be set on the process. It may include "regular"
            process parameters, and attributes used for completion. Attributes
            should be in a sub-dictionary under the key "capsul_attributes".
        '''
        self.completion_progress = 0.
        self.completion_progress_total = 1.
        self.set_parameters(process_inputs)

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
        if isinstance(self.process, Pipeline):
            attrib_values = self.get_attribute_values().export_to_dict()
            name = getattr(self.process, 'context_name', self.process.name)

            if use_topological_order:
                # proceed in topological order
                graph = self.process.workflow_graph(
                    remove_disabled_steps=False, remove_disabled_nodes=False)
                self.completion_progress_total = len(graph._nodes) + 0.05
                index = 0
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
                            ProcessCompletionEngine.get_completion_engine(
                                subprocess, pname)
                        self._install_subprogress_moniotoring(subprocess_compl)
                        try:
                            subprocess_compl.complete_parameters(
                                {'capsul_attributes': attrib_values})
                        except:
                            try:
                                self.__class__(subprocess).complete_parameters(
                                    {'capsul_attributes': attrib_values})
                            except:
                                pass
                        self._remove_subprogress_moniotoring(subprocess_compl)
                index += 1
                self.completion_progress = index
            else:
                self.completion_progress_total = len(self.process.nodes) + 0.05
                index = 0
                for node_name, node in six.iteritems(self.process.nodes):
                    if node_name == '':
                        continue
                    if hasattr(node, 'process'):
                        subprocess = node.process
                        pname = '.'.join([name, node_name])
                        subprocess_compl = \
                            ProcessCompletionEngine.get_completion_engine(
                                subprocess, pname)
                        self._install_subprogress_moniotoring(subprocess_compl)
                        try:
                            subprocess_compl.complete_parameters(
                                {'capsul_attributes': attrib_values})
                        except:
                            try:
                                self.__class__(subprocess).complete_parameters(
                                    {'capsul_attributes': attrib_values})
                            except:
                                pass
                        self._remove_subprogress_moniotoring(subprocess_compl)
                index += 1
                self.completion_progress = index

        # now complete process parameters:
        attributes = self.get_attribute_values()
        for pname in self.process.user_traits():
            try:
                value = self.attributes_to_path(pname, attributes)
                if value is not None:  # should None be valid ?
                    setattr(self.process, pname, value)
            except:
                pass
        self.completion_progress = self.completion_progress_total


    def attributes_to_path(self, parameter, attributes):
        ''' Build a path from attributes for a given parameter in a process.

        Parameters
        ----------
        parameter: str
        attributes: ProcessAttributes instance (Controller)
        '''
        return self.get_path_completion_engine() \
            .attributes_to_path(self.process, parameter, attributes)


    def set_parameters(self, process_inputs):
        ''' Set the given parameters dict to the given process.
        process_inputs may include regular parameters of the underlying
        process, and attributes (capsul_attributes: dict).
        '''

        # This convenience method only differs from the Controller
        # import_from_dict() method in the way that capsul_attributes items
        # will not completely replace all the attributes values, but only set
        # those specified here, and leave the others in place.
        dst_attributes = self.get_attribute_values()
        attributes = process_inputs.get('capsul_attributes')
        if attributes:
            avail_attrib = set(dst_attributes.user_traits().keys())
            attributes = dict((k, v) for k, v in six.iteritems(attributes)
                              if k in avail_attrib)
            dst_attributes.import_from_dict(attributes)
        process_inputs = dict((k, v) for k, v
                              in six.iteritems(process_inputs)
                              if k != 'capsul_attributes')
        self.process.import_from_dict(process_inputs)


    def attributes_changed(self, obj, name, old, new):
        ''' Traits changed callback which triggers parameters update.

        This method basically calls complete_parameters() (after some checks).

        Users do not normally have to use it directly, it is used internally
        when install_auto_completion() has been called.

        See :py:meth:`install_auto_completion`
        '''
        if name != 'trait_added' and name != 'user_traits_changed' \
                and self.completion_ongoing is False:
            #setattr(self.capsul_attributes, name, new)
            self.completion_ongoing = True
            self.complete_parameters({'capsul_attributes': {name: new}})
            self.completion_ongoing = False


    def nodes_selection_changed(self, obj, name, old, new):
        ''' Traits changed callback which triggers parameters update.

        This method basically calls complete_parameters() (after some checks).

        Users do not normally have to use it directly, it is used internally
        when install_auto_completion() has been called.

        See :py:meth:`install_auto_completion`
        '''
        if not self.completion_ongoing:
            self.completion_ongoing = True
            self._rebuild_attributes = True
            self.complete_parameters()
            self.completion_ongoing = False


    def install_auto_completion(self):
        ''' Monitor attributes changes and switches changes (which may
        influence attributes) and recompute parameters completion when needed.
        '''
        self.get_attribute_values().on_trait_change(
            self.attributes_changed, 'anytrait')

        if isinstance(self.process, Pipeline):
            for node_name, node in six.iteritems(self.process.nodes):
                if isinstance(node, Switch):
                    # a switch may change attributes dynamically
                    # so we must be notified if this happens.
                    node.on_trait_change(self.nodes_selection_changed,
                                         'switch')


    def remove_auto_completion(self):
        ''' Remove attributes monitoring and auto-recomputing of parameters.

        Reverts install_auto_completion()
        '''
        if self.process is not None:
            self.get_attribute_values().on_trait_change(
                self.attributes_changed, 'anytrait', remove=True)

            if isinstance(self.process, Pipeline):
                for node_name, node in six.iteritems(self.process.nodes):
                    if isinstance(node, Switch):
                        # a switch may change attributes dynamically
                        # so we must be notified if this happens.
                        node.on_trait_change(self.nodes_selection_changed,
                                            'switch', remove=True)


    def get_path_completion_engine(self):
        ''' Get a PathCompletionEngine object for the given process.
        The default implementation queries PathCompletionEngineFactory,
        but some specific ProcessCompletionEngine implementations may override
        it for path completion at the process level (FOMs for instance).
        '''
        study_config = self.process.get_study_config()
        engine_factory = None
        if 'AttributesConfig' in study_config.modules:
            try:
                engine_factory \
                    = study_config.modules_data.attributes_factory.get(
                        'path_completion', study_config.path_completion)
            except ValueError:
                pass # not found
        if engine_factory is None:
            engine_factory = PathCompletionEngineFactory()
        return engine_factory.get_path_completion_engine(self.process)


    @staticmethod
    def get_completion_engine(process, name=None):
        ''' Get a ProcessCompletionEngine instance for a given process within
        the framework of its StudyConfig: factory function.
        '''
        engine_factory = None
        if hasattr(process, 'get_study_config'):
            # switches don't have a study_config at the moment.
            study_config = process.get_study_config()
            if 'AttributesConfig' in study_config.modules:
                try:
                    engine_factory \
                        = study_config.modules_data.attributes_factory.get(
                            'process_completion',
                            study_config.process_completion)
                except ValueError:
                    pass # not found
        if engine_factory is None:
            engine_factory = ProcessCompletionEngineFactory()
        completion_engine = engine_factory.get_completion_engine(
            process, name=name)
        # set the completion engine into the process
        if completion_engine is not None:
            process.completion_engine = completion_engine
        return completion_engine


    def _get_schemas(self):
        ''' Get schemas dictionary from process and its StudyConfig
        '''
        schemas = {}
        study_config = self.process.get_study_config()
        factory = getattr(study_config.modules_data, 'attributes_factory',
                          None)
        if factory is not None:
            for dir_name, schema_name \
                    in six.iteritems(study_config.attributes_schemas):
                schemas[dir_name] = factory.get('schema', schema_name)
        return schemas


    def _install_subprogress_moniotoring(self, subprocess_compl):
        monitor_subprocess_progress = getattr(
            self, 'monitor_subprocess_progress', True)
        if monitor_subprocess_progress:
            self._old_monitor_sub = getattr(
                subprocess_compl, 'monitor_subprocess_progress', True)
            subprocess_compl.monitor_subprocess_progress = False
            self._current_progress = self.completion_progress
            self._monitoring_callback = SomaPartial(
                self.__class__._substep_completion_progress, weak_proxy(self),
                subprocess_compl)
            subprocess_compl.on_trait_change(
                self._monitoring_callback, 'completion_progress')


    def _remove_subprogress_moniotoring(self, subprocess_compl):
        monitor_subprocess_progress = getattr(
            self, 'monitor_subprocess_progress', True)
        if monitor_subprocess_progress:
            subprocess_compl.on_trait_change(
                self._monitoring_callback, 'completion_progress', remove=True)
            del self._current_progress
            del self._monitoring_callback
            if self._old_monitor_sub:
                del subprocess_compl.monitor_subprocess_progress
            del self._old_monitor_sub


    @staticmethod
    def _substep_completion_progress(self, substep_completion_engine, obj,
                                     name, old, new):
        sub_completion_rate \
            = substep_completion_engine.completion_progress \
                / substep_completion_engine.completion_progress_total
        self.completion_progress = self._current_progress \
            + sub_completion_rate


    def remove_attributes(self):
        '''Clear attributes controller cache, to allow rebuilding it after
        a change. This is generally a callback attached to switches changes.
        '''
        if self.trait('capsul_attributes') is not None \
                and hasattr(self, 'capsul_attributes'):
            self.remove_trait('capsul_attributes')


    def remove_switch_observers(self):
        '''Remove notification callbacks previously set to listen switches
        state changes.
        '''
        if isinstance(self.process, Pipeline):
            for name, node in six.iteritems(self.process.nodes):
                if isinstance(node, Switch) \
                        and hasattr(node, 'completion_engine'):
                    completion_engine = node.completion_engine
                    completion_engine.remove_switch_observer(self)


class SwitchCompletionEngine(ProcessCompletionEngine):
    ''' Completion engine specislization for a switch. The switch will
    propagate attributes from its selected inputs to corresponding outputs,
    if they can be retreived from parameters links. Otherwise the countrary
    will be tried (propagated from outputs to inputs).
    '''

    def __del__(self):
        self.remove_switch_observer()

    def get_attribute_values(self):
        if self.trait('capsul_attributes') is not None \
                and hasattr(self, 'capsul_attributes'):
            return self.capsul_attributes

        self.add_trait('capsul_attributes', ControllerTrait(Controller()))
        capsul_attributes = ProcessAttributes(self.process, {})
        self.capsul_attributes = capsul_attributes
        outputs = self.process._outputs
        schema = 'switch'  # FIXME
        name = getattr(self.process, 'context_name', self.name)
        pipeline_name = '.'.join(name.split('.')[:-1])
        if pipeline_name == '':
            pipeline_name = []
        else:
            pipeline_name = [pipeline_name]
        forbidden_attributes = set(['generated_by_parameter',
                                    'generated_by_process'])
        traits_types = {str: traits.Str, unicode: traits.Str, int: traits.Int,
                        float: traits.Float, list: traits.List}
        for out_name in outputs:
            in_name = '_switch_'.join((self.process.switch, out_name))
            found = False
            for output, name in ((False, in_name), (True, out_name)):
                plug = self.process.plugs.get(name)
                if plug is None:
                    continue
                if output:
                    links = plug.links_to
                else:
                    links = plug.links_from
                for link in links:
                    node = link[2]
                    if isinstance(node, Switch):
                        # FIXME: just for now
                        continue
                    if link[0] == '':
                        # link to the parent pipeline: don't call it to avoid
                        # an infinite loop.
                        # Either it will provide attributes by its own, either
                        # we must not take them into account, so skip it.
                        continue
                    if hasattr(node, 'process'):
                        process = node.process
                    else:
                        process = node
                    proc_name = '.'.join(pipeline_name + [link[0]])
                    completion_engine \
                        = ProcessCompletionEngine.get_completion_engine(
                            process, name=proc_name)
                    attributes = completion_engine.get_attribute_values()
                    try:
                        param_attributes \
                            = attributes.get_parameters_attributes()[link[1]]
                    except:
                        continue

                    if len(param_attributes) != 0 \
                            and len([x for x in param_attributes.keys()
                                     if x not in forbidden_attributes]) != 0:
                        ea = EditableAttributes()
                        for attribute, value in six.iteritems(
                                param_attributes):
                            if attribute not in forbidden_attributes:
                                ttype = traits_types.get(type(value))
                                if ttype is not None:
                                    trait = ttype()
                                else:
                                    trait = value
                                ea.add_trait(attribute, ttype)
                                setattr(ea, attribute, value)

                        capsul_attributes.set_parameter_attributes(
                            name, schema, ea, {})
                        found = True
                        break
                if found:
                    break
            if found:
                # propagate from input/output to other side
                ea = EditableAttributes()
                for attribute, value in six.iteritems(
                        param_attributes):
                    ttype = traits_types.get(type(value))
                    if ttype is not None:
                        trait = ttype()
                    else:
                        trait = value
                    ea.add_trait(attribute, ttype)
                    setattr(ea, attribute, value)
                if output:
                    capsul_attributes.set_parameter_attributes(
                        in_name, schema, ea, {})
                else:
                    capsul_attributes.set_parameter_attributes(
                        out_name, schema, ea, {})

        self.install_switch_observer()
        return capsul_attributes


    def install_switch_observer(self, observer=None):
        '''Setup a switch change observation, to remove parameters attributes
        when the switch state changes.

        Parameters
        ----------
        observer: ProcessCompletionEngine instance
            The observer which should change attributes after switch change.
            If not specified, the observer is the switch completion engine
            (self).
            Notification will call the observer remove_attributes() method.
        '''
        if observer is None:
            observer = self
        self.process.on_trait_change(observer.remove_attributes, 'switch')


    def remove_switch_observer(self, observer=None):
        '''Remove notification previously set by install_switch_observer()
        '''
        if observer is None:
            observer = self
        self.process.on_trait_change(observer.remove_attributes, 'switch',
                                     remove=True)



class PathCompletionEngine(object):
    ''' Implements building of a single path from a set of attributes for a
    specific process / parameter
    '''
    def attributes_to_path(self, process, parameter, attributes):
        ''' Build a path from attributes for a given parameter in a process.

        This method has to be specialized. The default implementation returns
        None.

        Parameters
        ----------
        process: Process instance
        parameter: str
        attributes: ProcessAttributes instance (Controller)
        '''
        return None


class ProcessCompletionEngineFactory(object):
    '''
    '''
    factory_id = 'basic'

    def get_completion_engine(self, process, name=None):
        '''
        Factory for ProcessCompletionEngine: get an ProcessCompletionEngine
        instance for a process in the context of a given StudyConfig.

        The study_config should specify which completion system(s) is (are)
        used (FOM, ...)
        If nothing is configured, a ProcessCompletionEngine base instance will
        be returned. It will not be able to perform completion at all, but will
        conform to the API.

        The base class implementation returns a base ProcessCompletionEngine
        instance, which is quite incomplete.
        '''
        if hasattr(process, 'completion_engine'):
            return process.completion_engine

        if isinstance(process, Switch):
            return SwitchCompletionEngine(process, name=name)
        return ProcessCompletionEngine(process, name=name)


class PathCompletionEngineFactory(object):

    factory_id = 'null'

    def get_path_completion_engine(self, process):
        raise RuntimeError('PathCompletionEngineFactory is pure virtual. '
                           'It must be derived to do actual work.')

