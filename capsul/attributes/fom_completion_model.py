# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import six
try:
    from traits.api import Str, HasTraits
except ImportError:
    from enthought.traits.api import Str, HasTraits

from soma.controller import Controller, ControllerTrait
from capsul.api import Pipeline
from capsul.attributes.completion_model import CompletionModel, \
    CompletionModelFactory
from soma.fom import DirectoryAsDict
from soma.path import split_path


class FomCompletionModel(CompletionModel, HasTraits):
    """
    Class who creates attributes and completion
    Associates a Process and FOMs.

    * A soma.Application needs to be created first, and associated with FOMS:

    ::

        from soma.application import Application
        soma_app = Application( 'soma.fom', '1.0' )
        soma_app.plugin_modules.append( 'soma.fom' )
        soma_app.initialize()

    * A capsul.study_config.StudyConfig also needs to be configured with FOM module, and
      selected FOMS and directories:

    ::

        from capsul.study_config import StudyConfig
        from capsul.study_config.config_modules.fom_config import FomConfig
        study_config = StudyConfig(modules=StudyConfig.default_modules + [FomConfig])
        study_config.update_study_configuration('study_config.json')
        FomConfig.check_and_update_foms(study_config)

    * Only then a ProcessWithFom can be created:

    ::

        process = get_process_instance('morphologist')
        process_with_fom = ProcessWithFom(process, study_config)

    Parameters
    ----------
    process: Process instance (mandatory)
        the process (or piprline) to be associated with FOMS
    study_config: StudyConfig (mandatory)
        config needed for FOMs, see capsul.study_config.study_config
    name: string (optional)
        name of the process in the FOM dictionary. By default the
        process.name variable will be used.

    Methods
    -------
    create_completion
    create_attributes_with_fom
    """
    def __init__(self, name=None):
        super(FomCompletionModel, self).__init__(name=name)


    def get_attribute_values(self, process):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        t = self.trait('capsul_attributes')
        if t is None:
            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
        return getattr(self, 'capsul_attributes')


    def create_attributes_with_fom(self, process):
        """To get useful attributes by the fom"""

        input_atp = process.study_config.modules_data.fom_atp['input']
        output_atp = process.study_config.modules_data.fom_atp['output']
        input_fom = process.study_config.modules_data.foms['input']
        output_fom = process.study_config.modules_data.foms['output']

        #Get attributes in input fom
        process_attributes = set()
        names_search_list = (self.name, process.id, process.name)
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

        capsul_attributes = self.get_attribute_values(process)

        for att in process_attributes:
            if not att.startswith('fom_'):
                default_value \
                    = input_fom.attribute_definitions[att].get(
                        'default_value')
                capsul_attributes.add_trait(att, Str(default_value))

        # Only search other attributes if fom not the same (by default merge
        # attributes of the same foms)
        if process.study_config.input_fom != process.study_config.output_fom:
            # Get attributes in output fom
            process_attributes2 = set()
            for parameter in output_fom.patterns[process.name]:
                process_attributes2.update(
                    output_atp.find_discriminant_attributes(
                        fom_parameter=parameter))

            for att in process_attributes2:
                if not att.startswith('fom_'):
                    default_value \
                        = output_fom.attribute_definitions[att].get(
                            'default_value')
                    if att in process_attributes \
                            and default_value != getattr(
                                capsul_attributes, att):
                        print('same attribute but not same default value so '
                              'nothing is displayed')
                    else:
                        setattr(capsul_attributes, att, default_value)


    def path_attributes(self, process, filename, parameter=None):
        """By the path, find value of attributes"""

        pta = process.study_config.modules_data.fom_pta['input']

        # Extract the attributes from the first result returned by
        # parse_directory
        liste = split_path(filename)
        len_element_to_delete = 1
        for element in liste:
            if element != os.sep:
                len_element_to_delete \
                    = len_element_to_delete + len(element) + 1
                new_value = filename[len_element_to_delete:len(filename)]
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
                            '%s is not recognized for parameter "%s" of "%s"'
                            % (new_value, parameter, process.name))

        attrib_values = self.get_attribute_values(process).export_to_dict()
        for att in attributes:
            if att in attrib_values.keys():
                setattr(attrib_values, att, attributes[att])
        return attributes


    def complete_parameters(self, process, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.

        The default implementation in AttributedProcess does nothing. Consider
        it as a "pure virtual" method.
        '''
        self.set_parameters(process, process_inputs)
        self.process_completion(process, name=process.name)


    def process_completion(self, process, name=None, verbose=False):
        '''Completes the given process parameters according to the attributes
        set.

        Parameters
        ----------
        process: Process / Pipeline: (mandatory)
            process on which perform completion
        name: string (optional)
            name under which the process will be searched in the FOM. This
            enables specialized used of otherwise generic processes in the
            context of a given pipeline
        verbose: bool (optional)
            issue warnings when a process cannot be found in the FOM list.
            Default: False
        '''
        if name is None:
            name = self.name or process.name

        #input_fom = process.study_config.modules_data.foms['input']
        output_fom = process.study_config.modules_data.foms['output']
        input_atp = process.study_config.modules_data.fom_atp['input']
        output_atp = process.study_config.modules_data.fom_atp['output']

        # TODO: here we could just call CompletionModel.complete_parameters()
        # which does this recursion but we need the name parameter

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
        attrib_values = self.get_attribute_values(process).export_to_dict()
        if isinstance(process, Pipeline):
            for node_name, node in six.iteritems(process.nodes):
                if node_name == '':
                    continue
                if hasattr(node, 'process'):
                    subprocess = node.process
                    pname = '.'.join([name, node_name])
                    subprocess_compl = CompletionModel.get_completion_model(
                        subprocess, pname)
                    try:
                        subprocess_compl.complete_parameters(
                            subprocess, {'capsul_attributes': attrib_values})
                    except Exception as e:
                        if verbose:
                            print('warning, node %s could not complete FOM'
                                  % node_name)
                            print(e)

        #Create completion
        names_search_list = (name, process.id, process.name)
        for fname in names_search_list:
            fom_patterns = output_fom.patterns.get(fname)
            if fom_patterns is not None:
                break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))

        allowed_attributes = set(attrib_values.keys())
        for parameter in fom_patterns:
            # Select only the attributes that are discriminant for this
            # parameter otherwise other attibutes can prevent the appropriate
            # rule to match
            if parameter in process.user_traits():
                if process.trait(parameter).output:
                    atp = output_atp
                else:
                    atp = input_atp
                parameter_attributes = atp.find_discriminant_attributes(
                    fom_parameter=parameter)
                d = dict((i, attrib_values[i]) \
                    for i in parameter_attributes if i in allowed_attributes)
                #d = dict( ( i, getattr(self, i) or self.attributes[ i ] ) \
                #    for i in parameter_attributes if i in self.attributes )
                d['fom_process'] = name
                d['fom_parameter'] = parameter
                d['fom_format'] = 'fom_prefered'
                for h in atp.find_paths(d):
                    setattr(process, parameter, h[0])

    @staticmethod
    def _fom_completion_factory(process, name):
        ''' Factoty inserted in attributed_processFactory
        '''
        study_config = process.get_study_config()
        if study_config is None \
                or 'FomConfig' not in study_config.modules:
            #print("no FOM:", study_config, study_config.modules.keys())
            return None  # Non Fom config, no way it could work
        try:
            pfom = FomCompletionModel(name)
            if pfom is not None:
                pfom.create_attributes_with_fom(process)
                return pfom
        except:
            pass
        return None


# register ProcessWithFom factory into AttributedProcessFactory
CompletionModelFactory().register_factory(
    FomCompletionModel._fom_completion_factory, 10000)
