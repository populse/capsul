# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import six
try:
    from traits.api import Str, HasTraits
except ImportError:
    from enthought.traits.api import Str, HasTraits

from soma.controller import Controller, ControllerTrait
from capsul.pipeline.pipeline import Pipeline
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    ProcessCompletionEngineFactory, PathCompletionEngine
from capsul.attributes.completion_engine_iteration \
    import ProcessCompletionEngineIteration
from capsul.pipeline.process_iteration import ProcessIteration
from soma.fom import DirectoryAsDict
from soma.path import split_path


class FomProcessCompletionEngine(ProcessCompletionEngine):
    """
    FOM (File Organization Model) implementation of completion engine.

    * A capsul.study_config.StudyConfig also needs to be configured with FOM
      module, and selected FOMS and directories:

    ::

        from capsul.api import StudyConfig
        from capsul.study_config.config_modules.fom_config import FomConfig
        study_config = StudyConfig(modules=StudyConfig.default_modules
                                   + ['FomConfig', 'BrainVISAConfig'])
        study_config.update_study_configuration('study_config.json')

    * Only then a FomProcessCompletionEngine can be created:

    ::

        process = get_process_instance('morphologist')
        fom_completion_engine = FomProcessCompletionEngine(
            process, study_config)

    But generally this creation is handled via the
    ProcessCompletionEngine.get_completion_engine() function:

    ::

        fom_completion_engine = ProcessCompletionEngine.get_completion_engine(
            process)

    Parameters
    ----------
    name: string (optional)
        name of the process in the FOM dictionary. By default the
        process.name variable will be used.

    Methods
    -------
    create_completion
    create_attributes_with_fom
    """
    def __init__(self, name=None):
        super(FomProcessCompletionEngine, self).__init__(name=name)


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
                    if att in process_attributes:
                        if default_value != getattr(capsul_attributes, att):
                            print('same attribute in input/output FOMs but '
                                  'with different default values')
                        else:
                            setattr(capsul_attributes, att, default_value)
                    else:
                        capsul_attributes.add_trait(att, Str(default_value))


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


    def complete_parameters_xx(self, process, process_inputs={}):
        ''' Completes file parameters from given inputs parameters, which may
        include both "regular" process parameters (file names) and attributes.
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

        # TODO: here we could just call
        # ProcessCompletionEngine.complete_parameters()
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
                    subprocess_compl \
                        = ProcessCompletionEngine.get_completion_engine(
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
                    # find_paths() is a generator which can sometimes generate
                    # several values (formats). We are only interested in the
                    # first one.
                    break


    def get_path_completion_engine(self, process):
        '''
        '''
        return FomPathCompletionEngine()


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
            pfom = FomProcessCompletionEngine(name)
            if pfom is not None:
                pfom.create_attributes_with_fom(process)
                return pfom
        except:
            pass
        return None


class FomPathCompletionEngine(PathCompletionEngine):

    def attributes_to_path(self, process, parameter, attributes):
        ''' Build a path from attributes
        '''
        input_fom = process.study_config.modules_data.foms['input']
        output_fom = process.study_config.modules_data.foms['output']
        input_atp = process.study_config.modules_data.fom_atp['input']
        output_atp = process.study_config.modules_data.fom_atp['output']

        #Create completion
        if process.trait(parameter).output:
            atp = output_atp
            fom = output_fom
        else:
            atp = input_atp
            fom = input_fom
        name = process.id
        names_search_list = (process.id, process.name,
                             getattr(process, 'context_name', ''))
        for fname in names_search_list:
            fom_patterns = fom.patterns.get(fname)
            if fom_patterns is not None:
                name = fname
                break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))

        allowed_attributes = set(attributes.keys())
        allowed_attributes.discard('parameter')
        allowed_attributes.discard('process_name')
        # Select only the attributes that are discriminant for this
        # parameter otherwise other attibutes can prevent the appropriate
        # rule to match
        parameter_attributes = atp.find_discriminant_attributes(
            fom_parameter=parameter)
        d = dict((i, attributes[i]) \
            for i in parameter_attributes if i in allowed_attributes)
        #d = dict( ( i, getattr(self, i) or self.attributes[ i ] ) \
        #    for i in parameter_attributes if i in self.attributes )
        d['fom_process'] = name
        d['fom_parameter'] = parameter
        d['fom_format'] = 'fom_prefered'
        path_value = None
        for h in atp.find_paths(d):
            path_value = h[0]
            # find_paths() is a generator which can sometimes generate
            # several values (formats). We are only interested in the
            # first one.
            break
        return path_value


class FomProcessCompletionEngineIteration(ProcessCompletionEngineIteration):

    def get_iterated_attributes(self, process):
        subprocess = process.process
        input_atp = subprocess.study_config.modules_data.fom_atp['input']
        output_atp = subprocess.study_config.modules_data.fom_atp['output']

        #name = subprocess.id
        #names_search_list = (subprocess.id, subprocess.name,
                             #getattr(subprocess, 'context_name', ''))
        #for fname in names_search_list:
            #fom_patterns = fom.patterns.get(fname)
            #if fom_patterns is not None:
                #name = fname
                #break
        #else:
            #raise KeyError('Process not found in FOMs amongst %s' \
                #% repr(names_search_list))

        iter_attrib = set()
        for parameter in process.iterative_parameters:
            if subprocess.trait(parameter).output:
                atp = output_atp
            else:
                atp = input_atp
            parameter_attributes = set([
                x for x in atp.find_discriminant_attributes(
                    fom_parameter=parameter) if not x.startswith('fom_')])
            iter_attrib.update(parameter_attributes)
        return iter_attrib


    @staticmethod
    def _iteration_factory(process, name):
        if not isinstance(process, ProcessIteration):
            return None
        if not isinstance(
                ProcessCompletionEngine.get_completion_engine(process.process),
                FomProcessCompletionEngine):
            # iterated process doesn't use FOM
            return None
        return FomProcessCompletionEngineIteration(name)


# register FomProcessCompletionEngine factory into
# ProcessCompletionEngineFactory
ProcessCompletionEngineFactory().register_factory(
    FomProcessCompletionEngine._fom_completion_factory, 10000)
ProcessCompletionEngineFactory().register_factory(
    FomProcessCompletionEngineIteration._iteration_factory, 40000)

