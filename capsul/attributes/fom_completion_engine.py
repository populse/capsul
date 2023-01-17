# -*- coding: utf-8 -*-

'''
Completion engine for File Organization Models (FOM).

Classes
=======
:class:`FomProcessCompletionEngine`
-----------------------------------
:class:`FomPathCompletionEngine`
--------------------------------
:class:`FomProcessCompletionEngineIteration`
--------------------------------------------
'''

from __future__ import print_function
from __future__ import absolute_import

import os
import six
from traits.api import Str, HasTraits, List, Undefined

from soma.controller import Controller, ControllerTrait
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import Node, Switch, ProcessNode
from capsul.attributes.completion_engine import ProcessCompletionEngine, \
    ProcessCompletionEngineFactory, PathCompletionEngine, \
    PathCompletionEngineFactory
from capsul.attributes.completion_engine_iteration \
    import ProcessCompletionEngineIteration
from capsul.pipeline.process_iteration import ProcessIteration
from capsul.attributes.attributes_schema import ProcessAttributes, \
    EditableAttributes
from soma.fom import DirectoryAsDict
from soma.path import split_path
from soma.sorted_dictionary import SortedDictionary


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
    create_attributes_with_fom
    """
    def __init__(self, process, name=None):
        super(FomProcessCompletionEngine, self).__init__(
            process=process, name=name)
        self.input_fom = None
        self.output_fom = None
        self.shared_fom = None


    def get_attribute_values(self):
        ''' Get attributes Controller associated to a process

        Returns
        -------
        attributes: Controller
        '''
        if not self._rebuild_attributes \
                and self.trait('capsul_attributes') is not None \
                and hasattr(self, 'capsul_attributes'):
            return self.capsul_attributes

        self.create_attributes_with_fom()
        self._rebuild_attributes = False

        return self.capsul_attributes


    def create_attributes_with_fom(self):
        """To get useful attributes by the fom"""

        # print('create_attributes_with_fom for', self.process, ', FCE:', self)
        process = self.process
        if isinstance(process, ProcessNode):
            process = process.process

        study_config = process.study_config
        modules_data = study_config.modules_data

        #Get attributes in input fom
        id = getattr(process, 'id', None)
        names_search_list = [self.name]
        if id:
            names_search_list.append(id)
        names_search_list += [process.name,
                             getattr(process, 'context_name', '')]

        schemas = self._get_schemas()
        if not hasattr(self, 'capsul_attributes'):
            self.add_trait('capsul_attributes', ControllerTrait(Controller()))
            self.capsul_attributes = ProcessAttributes(self.process, schemas)
        capsul_attributes = self.capsul_attributes

        matching_fom = False
        input_found = False
        output_found = False
        shared_fom = None

        # print('create_attributes_with_fom for', self.process, ', FCE:', self, ', foms:', {n: f.fom_names[-1] for n, f in modules_data.foms.items()})

        foms = SortedDictionary()
        foms.update(modules_data.foms)
        if study_config.auto_fom:
            # in auto-fom mode, also search in additional and non-loaded FOMs
            foms.update(modules_data.all_foms)

        def editable_attributes(attributes, fom):
            ea = EditableAttributes()
            for attribute in attributes:
                if attribute.startswith('fom_'):
                    continue # skip FOM internals
                default_value = fom.attribute_definitions[attribute].get(
                    'default_value', '')
                ea.add_trait(attribute, Str(default_value, optional=True))
            return ea

        sel_foms = {}
        if study_config.input_fom:
            sel_foms['input'] = study_config.input_fom
        if study_config.output_fom:
            sel_foms['output'] = study_config.output_fom
        if study_config.shared_fom:
            sel_foms['shared'] = study_config.shared_fom

        for schema, fom in foms.items():
            if fom is None:
                fom, atp, pta \
                    = study_config.modules['FomConfig'].load_fom(schema)
                foms[schema] = fom

            if schema not in ('input', 'output', 'shared'):
                # exclude incompatible FOMs
                for fs in ('input', 'output', 'shared'):
                    found = False
                    f = modules_data.foms.get(fs)
                    if f is None:
                        if fs == 'shared':
                            if 'shared' in schema:
                                sel_foms['shared'] = schema
                                found = True
                        elif 'shared' not in schema:
                            sel_foms[fs] = schema
                            found = True
                    elif fom is not f:
                        if sum([n in fom.fom_names
                                for n in f.fom_names]) \
                                == len(f.fom_names):
                            # all sub-foms of f included in fom:
                            # possibly keep it
                            if fs != 'shared':
                                # print('extend fom:', schema, 'for', fs, ':', f.fom_names)
                                for name in names_search_list:
                                    fom_patterns = fom.patterns.get(name)
                                    if fom_patterns is not None:
                                        found = True
                                        break
                                #else:
                                    #print('process not found - discard it')
                            else:
                                found = True
                            if found:
                                sel_foms[fs] = schema

        # print('new foms:', sel_foms)

        fom_modified = False

        found = False
        for schema, fom_type in sel_foms.items():
            # print('schema:', schema, fom_type)
            fom = modules_data.all_foms[fom_type]
            atp = modules_data.fom_atp['all'].get(fom_type) \
                or modules_data.fom_atp.get(schema)

            if atp is None:
                continue
            for name in names_search_list:
                fom_patterns = fom.patterns.get(name)
                if fom_patterns is not None:
                    break
            else:
                # print('process', names_search_list, 'not found in', fom_type)
                continue

            found = True
            # print('completion using FOM:', schema, fom_type, 'for', process.id, ', atp:', atp)
            #break

            for parameter in fom_patterns:
                param_attributes = atp.find_discriminant_attributes(
                        fom_parameter=parameter, fom_process=name)
                ea = editable_attributes(param_attributes, fom)
                try:
                    capsul_attributes.set_parameter_attributes(
                        parameter, schema, ea, {})
                except KeyError:
                    # param already registered
                    pass

            if (schema not in modules_data.foms
                    or modules_data.foms[schema] != fom
                    or schema not in modules_data.fom_atp
                    or modules_data.fom_atp[schema] != atp
                    or getattr(study_config, '%s_fom' % schema) != fom_type):
                modules_data.foms[schema] = fom
                modules_data.fom_atp[schema] = atp
                setattr(study_config, '%s_fom' % schema, fom_type)
                fom_modified = True

        if not found:
            # no FOM contains the process
            raise KeyError('No matching FOM for process %s'
                           % repr(names_search_list))

        #if fom_modified:
            # the modif will trigger another completion
            #return

        # in a pipeline, we still must iterate over nodes to find switches,
        # which have their own behaviour.
        if isinstance(process, Pipeline):
            attributes = self.capsul_attributes
            name = process.name

            for node_name, node in list(process.nodes.items()):
                if isinstance(node, Switch):
                    subprocess = node
                    if subprocess is None:
                        continue
                    pname = '.'.join([name, node_name])
                    subprocess_compl = \
                        ProcessCompletionEngine.get_completion_engine(
                            subprocess, pname)
                    try:
                        sub_attributes \
                            = subprocess_compl.get_attribute_values()
                    except Exception:
                        try:
                            subprocess_compl = self.__class__(subprocess)
                            sub_attributes \
                                = subprocess_compl.get_attribute_values()
                        except Exception:
                            continue
                    for attribute, trait \
                            in six.iteritems(sub_attributes.user_traits()):
                        if attributes.trait(attribute) is None:
                            attributes.add_trait(attribute, trait)
                            setattr(attributes, attribute,
                                    getattr(sub_attributes, attribute))

            self._get_linked_attributes()

        # remember foms for later
        if 'input' in sel_foms:
            self.input_fom = sel_foms['input']
        else:
            self.input_fom = study_config.input_fom
        if 'output' in sel_foms:
            self.output_fom = sel_foms['output']
        else:
            self.output_fom = study_config.output_fom
        if 'shared' in sel_foms:
            self.shared_fom = sel_foms['shared']
        else:
            self.shared_fom = study_config.shared_fom

    @staticmethod
    def setup_fom(process):
        completion_engine \
            = ProcessCompletionEngine.get_completion_engine(process)
        if not isinstance(completion_engine, FomProcessCompletionEngine):
            return
        if not hasattr(completion_engine, 'input_fom') \
                or completion_engine.input_fom is None:
            if process.study_config.input_fom != completion_engine.input_fom \
                    or process.study_config.output_fom \
                        != completion_engine.output_fom \
                    or process.study_config.shared_fom \
                        != completion_engine.shared_fom:
                # FOMs have changed: rebuild attributes
                completion_engine._rebuild_attributes = True
            completion_engine.create_attributes_with_fom()
        if process.study_config.input_fom != completion_engine.input_fom:
            process.study_config.input_fom = completion_engine.input_fom
        if process.study_config.output_fom != completion_engine.output_fom:
            process.study_config.output_fom = completion_engine.output_fom
        if process.study_config.shared_fom != completion_engine.shared_fom:
            process.study_config.shared_fom = completion_engine.shared_fom


    def path_attributes(self, filename, parameter=None):
        """By the path, find value of attributes"""

        pta = self.process.study_config.modules_data.fom_pta['input']

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
                    path, st, attributes = next(pta.parse_directory(
                        DirectoryAsDict.paths_to_dict( new_value) ))
                    break
                except StopIteration:
                    if element == liste[-1]:
                        raise ValueError(
                            '%s is not recognized for parameter "%s" of "%s"'
                            % (new_value, parameter, self.process.name))

        attrib_values = self.get_attribute_values().export_to_dict()
        for att in attributes:
            if att in list(attrib_values.keys()):
                setattr(attrib_values, att, attributes[att])
        return attributes


    def get_path_completion_engine(self):
        '''
        '''
        return FomPathCompletionEngine()


    @staticmethod
    def _fom_completion_factory(process, name):
        ''' Factoty inserted in attributed_processFactory
        '''
        study_config = process.get_study_config()
        if study_config is None \
                or 'FomConfig' not in study_config.modules \
                or study_config.use_fom == False:
            #print("no FOM:", study_config, study_config.modules.keys())
            return None  # Non Fom config, no way it could work
        try:
            pfom = FomProcessCompletionEngine(process, name)
            return pfom
        except KeyError:
            # process not in FOM
            pass
        return None


class FomPathCompletionEngine(PathCompletionEngine):

    def attributes_to_path(self, process, parameter, attributes):
        ''' Build a path from attributes

        Parameters
        ----------
        process: Process instance
        parameter: str
        attributes: ProcessAttributes instance (Controller)
        '''
        FomProcessCompletionEngine.setup_fom(process)

        input_fom = process.study_config.modules_data.foms['input']
        output_fom = process.study_config.modules_data.foms['output']
        input_atp = process.study_config.modules_data.fom_atp['input']
        output_atp = process.study_config.modules_data.fom_atp['output']

        #Create completion
        names_search_list = []
        if isinstance(process, Node):
            trait = process.get_trait(parameter)
            name = process.name
            if hasattr(process, 'process'):
                if hasattr(process.process, 'context_name'):
                    names_search_list.append(process.process.context_name)
                names_search_list.append(process.process.name)
        else:
            trait = process.trait(parameter)
            name = process.id
            names_search_list.append(name)
        if trait.output:
            atp = output_atp
            fom = output_fom
        else:
            atp = input_atp
            fom = input_fom
        names_search_list += [process.name,
                              getattr(process, 'context_name', '')]
        for fname in names_search_list:
            fom_patterns = fom.patterns.get(fname)
            if fom_patterns is not None:
                name = fname
                break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))

        allowed_attributes = set(attributes.user_traits().keys())
        allowed_attributes.discard('parameter')
        allowed_attributes.discard('process_name')
        #allowed_attributes = set(attributes.get_parameters_attributes()[
            #parameter].keys())
        #allowed_attributes.discard('type')
        #allowed_attributes.discard('generated_by_parameter')
        #allowed_attributes.discard('generated_by_process')

        # Select only the attributes that are discriminant for this
        # parameter otherwise other attributes can prevent the appropriate
        # rule to match
        parameter_attributes = atp.find_discriminant_attributes(
            fom_parameter=parameter, fom_process=name)
        d = dict((i, getattr(attributes, i)) \
            for i in parameter_attributes if i in allowed_attributes)
        d['fom_process'] = name
        d['fom_parameter'] = parameter
        d['fom_format'] = 'fom_preferred'
        path_value = None
        #path_values = []
        #debug = getattr(self, 'debug', None)
        for h in atp.find_paths(d):  # , debug=debug):
            path_value = h[0]
            # find_paths() is a generator which can sometimes generate
            # several values (formats). We are only interested in the
            # first one.
            #path_values.append(h[0])
            break

        return path_value


    def open_values_attributes(self, process, parameter):
        ''' Attributes with "open" values, not restricted to a list of possible
        values
        '''
        # print('open_values_attributes', process.id, parameter)

        FomProcessCompletionEngine.setup_fom(process)

        for schema in ('input', 'output', 'shared'):
            fom = process.study_config.modules_data.foms[schema]
            atp = process.study_config.modules_data.fom_atp[schema]
            # print('fom:', fom.fom_names)
            # print('atp:', atp)

            name = getattr(process, 'id', process.name)
            names_search_list = []
            if hasattr(process, 'id'):
                names_search_list.append(process.id)
            names_search_list += [process.name,
                                  getattr(process, 'context_name', '')]
            for fname in names_search_list:
                fom_patterns = fom.patterns.get(fname)
                if fom_patterns is not None:
                    name = fname
                    break
            else:
                continue

            values = atp.find_attributes_values()
            attributes = [k for k, v in six.iteritems(values)
                          if k not in ('fom_name', 'fom_process',
                                       'fom_parameter', 'fom_format')
                            and len(v) == 2 and v[1] == (u'', )]
            return attributes

        return None


    def allowed_formats(self, process, parameter):
        ''' List of possible formats names associated with a parameter
        '''
        FomProcessCompletionEngine.setup_fom(process)

        formats = []
        for schema in ('input', 'output', 'shared'):
            atp = process.study_config.modules_data.fom_atp[schema]
            sub_f = atp.allowed_formats_for_parameter(process.name, parameter)
            formats += [f for f in sub_f if f not in formats]
        return formats


    def allowed_extensions(self, process, parameter):
        ''' List of possible file extensions associated with a parameter
        '''
        FomProcessCompletionEngine.setup_fom(process)

        exts = set()
        for schema in ('input', 'output', 'shared'):
            atp = process.study_config.modules_data.fom_atp[schema]
            sub_e = atp.allowed_extensions_for_parameter(
                process_name=process.name, param=parameter)
            exts.update(sub_e)
        # sort and add dots
        exts2 = sorted(['.%s' % e for e in exts if e])
        if '' in exts:
            exts2.append('')
        return exts2


class FomProcessCompletionEngineIteration(ProcessCompletionEngineIteration):

    def get_iterated_attributes(self):
        process = self.process
        if isinstance(process, ProcessNode):
            process = process.process
        subprocess = process.process

        FomProcessCompletionEngine.setup_fom(subprocess)

        input_fom = subprocess.study_config.modules_data.foms['input']
        output_fom = subprocess.study_config.modules_data.foms['output']
        input_atp = subprocess.study_config.modules_data.fom_atp['input']
        output_atp = subprocess.study_config.modules_data.fom_atp['output']

        name = subprocess.id
        names_search_list = (subprocess.id, subprocess.name,
                             getattr(subprocess, 'context_name', ''))
        for fom in (input_fom, output_fom):
            for fname in names_search_list:
                fom_patterns = fom.patterns.get(fname)
                if fom_patterns is not None:
                    name = fname
                    break
            else:
                continue
            break
        else:
            raise KeyError('Process not found in FOMs amongst %s' \
                % repr(names_search_list))

        iter_attrib = set()
        if not process.iterative_parameters:
            params = list(subprocess.user_traits().keys())
        else:
            params = process.iterative_parameters
        for parameter in params:
            if subprocess.trait(parameter).output:
                atp = output_atp
            else:
                atp = input_atp
            parameter_attributes = set([
                x for x in atp.find_discriminant_attributes(
                    fom_parameter=parameter, fom_process=name)
                if not x.startswith('fom_')])
            iter_attrib.update(parameter_attributes)
        return iter_attrib


#class FomPathCompletionEngineFactory(PathCompletionEngineFactory):

    #factory_id = 'fom'

    #def get_path_completion_engine(self, process):
        #return FomPathCompletionEngine(process)
