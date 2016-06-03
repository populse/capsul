
class CompletionModel(object):
    ''' Parameters completion from attributes for a process instance, in the
    context of a specific data organization.

    CompletionModel is pure virtual, and has to be subclassed for a data
    organization framework.
    '''

    def __init__(self, name):
        self.name = name


    def get_attributes(self, process):
        ''' Get attributes list associated to a process

        Returns
        -------
        attributes: list of strings
        '''
        raise AttributeError("CompletionModel.get_attributes() is a pure "
                             "virtual method.")


    def get_attribute_values(self, process):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        #study_config = process.get_study_config()
        # TODO
        raise AttributeError("CompletionModel.get_attribute_values() is a "
                             "pure virtual method.")


    def complete_parameters(self, process, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.

        The default implementation does nothing for a
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
                        subprocess = pipeline_node.process
                        subprocess_compl = \
                            CompletionModel.get_completion_model(
                                subprocess, pname)
                        subprocess_compl.complete_parameters(
                            subprocess, {'capsul_attributes': attrib_values})
            else:
                for node_name, node in six.iteritems(process.nodes):
                    if node_name == '':
                        continue
                    if hasattr(node, 'process'):
                        subprocess = node.process
                        pname = '.'.join([name, node_name])
                        subprocess_compl = \
                            CompletionModel.get_completion_model(
                                subprocess, pname)
                        subprocess_compl.complete_parameters(
                            subprocess, {'capsul_attributes': attrib_values})


    def set_parameters(self, process, process_inputs):
        ''' Set the given parameters dict to the given process.
        process_inputs may include regular parameters of the underlying
        process, and attributes (capsul_attributes: dict).
        '''

        # This convenience method only differs from the Controller
        # import_from_dict() method in the way that capsul_attributes items
        # will not completely replace the all attributes values, but only set
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
        process.import_from_dict(process_inputs)


    @staticmethod
    def get_completion_model(process, name):
        ''' Get a CompletionModel instance for a given process within the
        framework of its StudyConfig: factory function.
        '''
        # TODO
        pass


