##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Config module for :mod:`File Organization models (FOMs) <capsul.attributes.fom_completion_engine>`

Classes
=======
:class:`FomConfig`
------------------
'''

import os
import six
from traits.api import Bool, Str, Undefined, Instance, Directory, List
from soma.controller import Controller
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from soma.sorted_dictionary import SortedDictionary
import weakref


class FomConfig(Controller):
    '''FOM (File Organization Model) configuration module for CapsulEngine

    See :ref:`completion` for a more complete documentation about
    parameters completion.

    .. note::
        :class:`~capsul.engine.modules.fom.FomConfig`
        needs :class:`~capsul.engine.modules.axon.AxonConfig`
        to be part of
        :class:`~capsul.engine.CapsulEngine` modules.

    This module adds the following options (traits) in the
    :class:`~capsul.engine.CapsulEngine` object:

    input_fom: str
        input FOM
    output_fom: str
        output FOM
    shared_fom: str
        shared data FOM
    volumes_format: str
        Format used for volumes
    meshes_format: str
        Format used for meshes
    auto_fom: bool (default: True)
        Look in all FOMs when a process is not found. Note that auto_fom
        looks for the first FOM matching the process to get
        completion for, and does not handle ambiguities. Moreover
        it brings an overhead (typically 6-7 seconds) the first
        time it is used since it has to parse all available FOMs.
    fom_path: list of directories
        list of additional directories where to look for FOMs (in addition to
        the standard share/foms)
    use: bool
        Use File Organization Models for file parameters completion'

    *Methods:*
    '''

    input_fom = Str("", output=False, desc='input FOM')
    output_fom = Str("", output=False, desc='output FOM')
    shared_fom = Str("", output=False, desc='shared data FOM')
    volumes_format = Str(Undefined, output=False,
                         desc='Format used for volumes')
    meshes_format = Str(Undefined, output=False,
                        desc='Format used for meshes')
    auto_fom = Bool(
        True, output=False,
        desc='Look in all FOMs when a process is not found (in '
        'addition to the standard share/foms). Note that auto_fom '
        'looks for the first FOM matching the process to get '
        'completion for, and does not handle ambiguities. Moreover '
        'it brings an overhead (typically 6-7 seconds) the first '
        'time it is used since it has to parse all available FOMs.')
    fom_path = List(
        Directory(output=False),
        desc='list of additional directories where to look for FOMs')
    use = Bool(
        Undefined,
        output=False,
        desc='Use File Organization Models for file parameters '
            'completion')

    # FIXME: until directories are included in another config module
    input_directory = Directory(output=False,
                                desc='input study data directory')
    output_directory = Directory(output=True,
                                 desc='output study data directory')

    def __init__(self):
        super(FomConfig, self).__init__()
        # defaults
        self.input_fom = ""
        self.output_fom = ""
        self.shared_fom = ""

        self.foms = {}
        self.all_foms = SortedDictionary()
        self.fom_atp = {'all': {}}
        self.fom_pta = {'all': {}}


    def update_fom(self):
        '''Load configured FOMs and create FOM completion data
        '''
        # print('***update_fom ***')
        if self.use is False:
            return

        capsul_config = self.study_config.engine.global_config
        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        if 'soma.fom' not in soma_app.loaded_plugin_modules:
            # WARNING: this is unsafe, may erase configured things, and
            # probably not thread-safe.
            soma_app.initialize()

        fom_path = [p for p in self.fom_path
                              if p not in soma_app.fom_path] \
            + soma_app.fom_path

        soma_app.fom_manager.paths = fom_path
        soma_app.fom_manager.fom_files()

        if self.auto_fom \
                and len(self.all_foms) <= 3:
            for schema in soma_app.fom_manager.fom_files():
                if schema not in self.all_foms:
                    self.all_foms[schema] = None # not loaded yet.

        foms = (('input', self.input_fom),
                ('output', self.output_fom),
                ('shared', self.shared_fom))
        for fom_type, fom_filename in foms:
            if fom_filename != "":
                fom = self.all_foms.get(fom_filename)
                if fom is None:
                    fom, atp, pta = self.load_fom(fom_filename, capsul_config)
                else:
                    atp = self.fom_atp['all'][fom_filename]
                    pta = self.fom_pta['all'][fom_filename]
                self.foms[fom_type] = fom
                self.fom_atp[fom_type] = atp
                self.fom_pta[fom_type] = pta

        # update directories
        directories = {}
        directories['spm'] = self.study_config.spm_directory
        directories['shared'] = self.study_config.shared_directory
        directories['input'] = self.study_config.input_directory
        directories['output'] = self.study_config.output_directory

        for atp in self.fom_atp['all'].values():
            atp.directories = directories

        self.use = True

        # backward compatibility for StudyConfig
        self.study_config.modules_data.foms = self.foms
        self.study_config.modules_data.all_foms = self.all_foms
        self.study_config.modules_data.fom_atp = self.fom_atp
        self.study_config.modules_data.fom_pta = self.fom_pta


    def update_formats(self):
        config = self.study_config.engine.global_config
        directories = {}
        if hasattr(config, 'spm'):
            directories['spm'] = config.spm.directory
        if hasattr(config, 'axon'):
            directories['shared'] = config.axon.shared_directory
        directories['input'] = self.input_directory
        directories['output'] = self.output_directory

        formats = tuple(getattr(self, key) \
            for key in self.user_traits() \
            if key.endswith('_format') \
                and getattr(self, key) is not Undefined)

        for schema, fom in self.all_foms.items():
            if fom is None:
                continue

            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                preferred_formats=set((formats)))
            old_atp = self.fom_atp['all'].get(schema)
            self.fom_atp['all'][schema] = atp
            if old_atp is not None:
                for t in ('input', 'output', 'shared'):
                    if self.fom_atp.get(t) is old_atp:
                        self.fom_atp[t] = atp


    def load_fom(self, schema, capsul_config):
        #print('=== load fom', schema, '===')
        #import time
        #t0 = time.time()
        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        if 'soma.fom' not in soma_app.loaded_plugin_modules:
            # WARNING: this is unsafe, may erase configured things, and
            # probably not thread-safe.
            soma_app.initialize()
        old_fom_path = soma_app.fom_path
        soma_app.fom_path = [p for p in self.fom_path
                              if p not in soma_app.fom_path] \
            + soma_app.fom_path
        fom = soma_app.fom_manager.load_foms(schema)
        soma_app.fom_path = old_fom_path
        self.all_foms[schema] = fom

        # Create FOM completion data
        formats = tuple(getattr(self, key) \
            for key in self.user_traits() \
            if key.endswith('_format') \
                and getattr(self, key) is not Undefined)

        directories = {}
        directories['spm'] = capsul_config.spm.directory
        directories['shared'] = capsul_config.axon.shared_directory
        directories['input'] = self.input_directory
        directories['output'] = self.output_directory

        atp = AttributesToPaths(
            fom,
            selection={},
            directories=directories,
            preferred_formats=set((formats)))
        self.fom_atp['all'][schema] = atp
        pta = PathToAttributes(fom, selection={})
        self.fom_pta['all'][schema] = pta
        #print('   load fom done:', time.time() - t0, 's')
        return fom, atp, pta


    def reset_foms(self):
        # print('reset foms, with path:', self.study_config.fom_path)
        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        if 'soma.fom' not in soma_app.loaded_plugin_modules:
            # WARNING: this is unsafe, may erase configured things, and
            # probably not thread-safe.
            soma_app.initialize()
        soma_app.fom_manager.clear_cache()
        self.update_fom()


def load_module(capsul_engine, module_name):
    # print('load_module FOM')
    capsul_engine.load_module('capsul.engine.module.axon')
    capsul_engine.load_module('capsul.engine.module.spm')
    capsul_engine.load_module('capsul.engine.module.attributes')
    capsul_engine.global_config.add_trait('fom', Instance(FomConfig))
    capsul_engine.global_config.fom = FomConfig()

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'FomConfig' not in capsul_engine.study_config.modules:
        scmod = capsul_engine.study_config.load_module('FomConfig', {})
        scmod.initialize_module()
        scmod.initialize_callbacks()

    # allow the methods to access StudyConfig (transciently)
    if isinstance(capsul_engine.study_config, weakref.ProxyType):
        capsul_engine.global_config.fom.study_config \
            = capsul_engine.study_config
    else:
        capsul_engine.global_config.fom.study_config \
            = weakref.proxy(capsul_engine.study_config)

    capsul_engine.global_config.fom.update_fom()

    capsul_engine.global_config.fom.on_trait_change(
        capsul_engine.global_config.fom.update_fom,
        ['input_fom', 'output_fom', 'shared_fom', 'volumes_format',
         'meshes_format', 'auto_fom', 'use', 'input_directory', 'output_directory'])
    capsul_engine.global_config.axon.on_trait_change(
        capsul_engine.global_config.fom.update_fom, 'shared_directory')
    capsul_engine.global_config.spm.on_trait_change(
        capsul_engine.global_config.fom.update_fom, 'directory')
    capsul_engine.global_config.fom.on_trait_change(
        capsul_engine.global_config.fom.update_formats,
        ['volumes_format', 'meshes_format'])
    capsul_engine.global_config.fom.on_trait_change(
        capsul_engine.global_config.fom.reset_foms, 'fom_path')
