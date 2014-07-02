# -*- coding: utf-8 -*-
import os
try:
    from traits.api import Str
except ImportError:
    from enthought.traits.api import Str

from soma.controller import Controller
from capsul.pipeline import Pipeline
from soma.application import Application
from soma.fom import DirectoryAsDict
from soma.path import split_path
from capsul.study_config.study_config2 import StudyConfig


class ProcessWithFom(Controller):
    """
    Class who creates attributes and completion
    Associates a Process and FOMs.

    * A soma.Application needs to be created first, and associated with FOMS:

    ::

        from soma.application import Application
        soma_app = Application( 'soma.fom', '1.0' )
        soma_app.plugin_modules.append( 'soma.fom' )
        soma_app.initialize()

    * A StudyConfig also needs to be configured with selected FOMS and directories:

    ::

        from capsul.study_config.study_config2 import StudyConfig
        from capsul.study_config.study_config_fom import StudyConfigFomManager
        study_config = StudyConfig()
        study_config.load('study_config.json')
        StudyConfigFomManager.check_and_update_foms(study_config)

    * Only then a ProcessWithFom can be created:

    ::

        process = get_process_instance('morphologist')
        process_with_fom = ProcessWithFom(process, study_config)

    Parameters
    ----------
    process: Process instance (mandatory)
        the process (or piprline) to be associated with FOMS
    study_config: StudyConfig (mandatory)
        config needed for FOMs, see capsul.study_config.study_config2
    name: string (optional)
        name of the process in the FOM dictionary. By default the
        process.name variable will be used.

    Methods
    -------
    create_completion()
    create_attributes_with_fom()
    """
    def __init__(self, process, study_config, name=None):
        super(ProcessWithFom, self).__init__()
        self.process = process
        if name is None:
            self.name = process.name
        else:
            self.name = name
        self.study_config = study_config
        self.list_process_iteration = []
        self.attributes = {}
        self.create_attributes_with_fom()
        self.completion_ongoing = False

    def iteration(self, process, newfile):
        # FIXME: what is newfile ?
        self.list_process_iteration.append(process)
        pwd = ProcessWithFom(process)
        pwd.create_attributes_with_fom()
        pwd.create_completion()
        return pwd

    def iteration_run(self):
        # this method should be replaced by a call to
        # pipeline_workflow.workflow_from_pipeline()
        # (but first, the iteration has to be an actual pipeline)
        from soma_workflow.client import Job, Workflow, WorkflowController

        print 'ITERATION RUN'
        jobs = {}
        i = 0
        for process in self.list_process_iteration:
            jobs['job'+str(i)] = Job(command=process.command())
            i = i+1

        wf = Workflow(jobs=[value for value in \
            jobs.itervalues()], name='test')
        # Helper.serialize('/tmp/test_wf',wf)
        controller = WorkflowController()
        controller.submit_workflow(workflow=wf, name='test run')


    def create_attributes_with_fom(self):
        """To get useful attributes by the fom"""

        input_atp = self.study_config.internal_data.atp['input']
        output_atp = self.study_config.internal_data.atp['output']
        input_fom = self.study_config.internal_data.foms['input']
        output_fom = self.study_config.internal_data.foms['output']

        #Get attributes in input fom
        process_attributes = set()
        names_search_list = (self.name, self.process.id, self.process.name)
        for name in names_search_list:
            fom_patterns = input_fom.patterns.get(name)
            if fom_patterns is not None:
                break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))
        for parameter in fom_patterns:
            process_attributes.update(
                input_atp.find_discriminant_attributes(
                    fom_parameter=parameter))

        for att in process_attributes:
            if not att.startswith('fom_'):
                default_value \
                    = input_fom.attribute_definitions[att].get(
                        'default_value')
                self.attributes[att] = default_value
                self.add_trait(att, Str(self.attributes[att]))

        # Only search other attributes if fom not the same (by default merge
        # attributes of the same foms)
        if self.study_config.input_fom != self.study_config.output_fom:
            # Get attributes in output fom
            process_attributes2 = set()
            for parameter in output_fom.patterns[self.process.name]:
                process_attributes2.update(
                    output_atp.find_discriminant_attributes(
                        fom_parameter=parameter))

            for att in process_attributes2:
                if not att.startswith('fom_'):
                    default_value \
                        = output_fom.attribute_definitions[att].get(
                            'default_value')
                    if att in process_attributes \
                            and default_value != self.attributes[att]:
                        print 'same attribute but not same default value so ' \
                            'nothing is displayed'
                    else:
                        self.attributes[att] = default_value
                        self.add_trait(att, Str(self.attributes[att]))


    def find_attributes(self, value):
        """By the path, find value of attributes"""

        pta = self.study_config.internal_data.pta['input']

        # Extract the attributes from the first result returned by
        # parse_directory
        liste = split_path(value)
        len_element_to_delete = 1
        for element in liste:
            if element != os.sep:
                len_element_to_delete \
                    = len_element_to_delete + len(element) + 1
                new_value = value[len_element_to_delete:len(value)]
                try:
                    #import logging
                    #logging.root.setLevel( logging.DEBUG )
                    #path, st, self.attributes = pta.parse_directory(
                    #    DirectoryAsDict.paths_to_dict( new_value),
                    #        log=logging ).next()
                    path, st, attributes = pta.parse_directory(
                        DirectoryAsDict.paths_to_dict( new_value) ).next()
                    break
                except StopIteration:
                    if element == liste[-1]:
                        raise ValueError(
                            '%s is not recognized for parameter "%s" of "%s"' \
                                % ( new_value,None, self.process.name ) )

        for att in attributes:
            if att in self.attributes:
                setattr(self, att, attributes[att])


    def create_completion(self):
        '''Completes the underlying process parameters according to the
        attributes set.

        This is equivalent to:

        >>> proc_with_fom.process_completion(proc_with_fom.process,
                proc_with_fom.name)
        '''
        # print 'CREATE COMPLETION, name:', self.name
        self.process_completion(self.process, self.name)


    def process_completion(self, process, name=None):
        '''Completes the given process parameters according to the attributes
        set.

        Parameters
        ----------
        process: Process / Pipeline: (mandatory)
            process on which perform completion
        name: string (optional)
            name under which the process will be sear'ched in the FOM. This
            enables specialized used of otherwise generic processes in the
            context of a given pipeline
        '''
        if name is None:
            name = self.name

        #input_fom = self.study_config.internal_data.foms['input']
        output_fom = self.study_config.internal_data.foms['output']
        input_atp = self.study_config.internal_data.atp['input']
        output_atp = self.study_config.internal_data.atp['output']

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
        if isinstance(process, Pipeline):
            for node_name, node in process.nodes.iteritems():
                if node_name == '':
                    continue
                if hasattr(node, 'process'):
                    subprocess = node.process
                    try:
                        pname = '.'.join([name, node_name])
                        self.process_completion(subprocess, pname)
                    except Exception, e:
                        print 'warning, node %s could not complete FOM' \
                            % node_name
                        print e

        #Create completion
        names_search_list = (name, process.id, process.name)
        for fname in names_search_list:
            fom_patterns = output_fom.patterns.get(fname)
            if fom_patterns is not None:
                break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))

        for parameter in fom_patterns:
            # Select only the attributes that are discriminant for this
            # parameter otherwise other attibutes can prevent the appropriate
            # rule to match
            if parameter in process.user_traits():
                if process.trait(parameter).output:
                    atp = output_atp
                else:
                    atp = input_atp
                parameter_attributes = [ 'fom_process' ] \
                    + atp.find_discriminant_attributes(
                        fom_parameter=parameter )
                d = dict( ( i, self.attributes[ i ] ) \
                    for i in parameter_attributes if i in self.attributes )
                #d = dict( ( i, getattr(self, i) or self.attributes[ i ] ) \
                #    for i in parameter_attributes if i in self.attributes )
                d['fom_parameter'] = parameter
                d['fom_format'] = 'fom_prefered'
                for h in atp.find_paths(d):
                    setattr(process, parameter, h[0])


    def attributes_changed(self, obj, name, old, new):
        # FIXME: what is obj for ?
        print 'attributes changed', name
        print self.completion_ongoing
        if name != 'trait_added' and name != 'user_traits_changed' \
                and self.completion_ongoing is False:
            self.attributes[name] = new
            self.completion_ongoing = True
            self.create_completion()
            self.completion_ongoing = False




