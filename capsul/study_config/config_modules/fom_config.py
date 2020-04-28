# -*- coding: utf-8 -*-
'''
Config module for :mod:`File Organization models (FOMs) <capsul.attributes.fom_completion_engine>`

Classes
=======
:class:`FomConfig`
------------------
'''

from __future__ import absolute_import
import os
import six
from traits.api import Bool, Str, Undefined, List, Directory
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
import weakref


class FomConfig(StudyConfigModule):
    '''FOM (File Organization Model) configuration module for StudyConfig

    .. note::
        :class:`~capsul.study_config.config_modules.fom_config.FomConfig`
        needs :class:`~capsul.study_config.config_modules.brainvisa_config.BrainVISAConfig`
        to be part of
        :class:`~capsul.study_config.study_config.StudyConfig` modules.

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

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
    use_fom: bool
        Use File Organization Models for file parameters completion'

    *Methods:*
    '''

    dependencies = ['BrainVISAConfig', 'SPMConfig', 'AttributesConfig']

    def __init__(self, study_config, configuration):
        super(FomConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('input_fom', Str(Undefined, output=False,
            desc='input FOM'))
        self.study_config.add_trait('output_fom', Str(Undefined, output=False,
            desc='output FOM'))
        self.study_config.add_trait('shared_fom', Str(Undefined, output=False,
            desc='shared data FOM'))
        self.study_config.add_trait('volumes_format',
                                    Str(Undefined, output=False,
            desc='Format used for volumes'))
        self.study_config.add_trait('meshes_format',
                                    Str(Undefined, output=False,
            desc='Format used for meshes'))
        self.study_config.add_trait(
            'auto_fom',
            Bool(True, output=False,
                 desc='Look in all FOMs when a process is not found (in '
                 'addition to the standard share/foms). Note that auto_fom '
                 'looks for the first FOM matching the process to get '
                 'completion for, and does not handle ambiguities. Moreover '
                 'it brings an overhead (typically 6-7 seconds) the first '
                 'time it is used since it has to parse all available FOMs.'))
        self.study_config.add_trait(
            'fom_path',
            List(Directory(output=False),
                 desc='list of additional directories where to look for FOMs'))
        self.study_config.add_trait('use_fom', Bool(
            Undefined,
            output=False,
            desc='Use File Organization Models for file parameters '
                'completion'))

        # defaults
        self.study_config.input_fom = ""
        self.study_config.output_fom = ""
        self.study_config.shared_fom = ""
        self.study_config.modules_data.foms = {}
        self.study_config.modules_data.fom_atp = {}
        self.study_config.modules_data.fom_pta = {}


    def initialize_module(self):
        # Comment the following code to make tests work before removing StudyConfig
        pass
        #if 'capsul.engine.module.fom' \
                #not in self.study_config.engine._loaded_modules:
            #self.study_config.engine.load_module('capsul.engine.module.fom')

        # allow the methods to access StudyConfig (transciently)
        #if isinstance(self.study_config, weakref.ProxyType):
            #self.study_config.engine.global_config.fom.study_config \
                #= self.study_config
        #else:
            #self.study_config.engine.global_config.fom.study_config \
                #= weakref.proxy(self.study_config)

        # Comment the following code to make tests work before removing StudyConfig
        #if type(self.study_config.engine) is not CapsulEngine:
            ## engine is a proxy, thus we are initialized from a real
            ## CapsulEngine, which holds the reference values
            #self.sync_from_engine()
        #else:
            #self.sync_to_engine()
            ## 1st sync may have changed things
            #self.sync_from_engine()



    # Comment the following code to make tests work before removing StudyConfig
    #def initialize_callbacks(self):
        #self.study_config.on_trait_change(
            #self.sync_to_engine,
            #['use_fom', 'input_directory', 'input_fom', 'meshes_format',
             #'output_directory', 'output_fom', 'shared_directory',
             #'shared_fom', 'spm_directory', 'volumes_format', 'auto_fom',
             #'fom_path'])
        #self.study_config.engine.global_config.fom.on_trait_change(
            #self.sync_from_engine,
            #['use','input_directory', 'output_directory', 'input_fom',
             #'output_fom', 'meshes_format', 'shared_fom', 'volumes_format',
             #'auto_fom', 'fom_path'])
        #self.study_config.engine.global_config.spm.on_trait_change(
            #self.sync_from_engine, 'directory')
        #self.study_config.engine.global_config.axon.on_trait_change(
            #self.sync_from_engine, 'shared_directory')


    def sync_to_engine(self, param=None, value=None):
        params = {'input_fom': None, 'meshes_format': None,
                  'output_fom': None, 'shared_fom': None,
                  'volumes_format': None, 'input_directory': None,
                  'output_directory': None,
                  'shared_directory': 'axon.shared_directory',
                  'spm_directory': 'spm.directory',
                  'use_fom': 'use'}
        if param is not None:
            params = {param: params.get(param)}

        for ps, pe in six.iteritems(params):
            if pe is None:
                mod = 'fom'
                p = ps
            else:
                mod_p = pe.split('.')
                p = mod_p[-1]
                if len(mod_p) >= 2:
                    mod = mod_p[0]
                else:
                    mod = 'fom'
            setattr(getattr(self.study_config.engine.global_config, mod), p,
                    getattr(self.study_config, ps))


    def sync_from_engine(self, controller=None, param=None, value=None):
        params = {'input_fom': None, 'meshes_format': None,
                  'output_fom': None, 'shared_fom': None,
                  'volumes_format': None, 'input_directory': None,
                  'output_directory': None,
                  'use': 'use_fom',
                  ('axon', 'shared_directory'): 'shared_directory',
                  ('spm', 'directory'): 'spm_directory'}
        if param is not None:
            mod = controller.__class__.__module__.split('.')[-1]
            if mod == 'fom':
                params = {param: params.get(param)}
            else:
                params = {(mod, param): params.get((mod, param))}

        for pe, ps in six.iteritems(params):
            if ps is None:
                mod = 'fom'
                if isinstance(pe, tuple):
                    ps = pe[1]
                    p = pe[0]
                else:
                    ps = pe
                    p = pe
            else:
                if isinstance(pe, tuple):
                    mod, p = pe
                    ps = p
                else:
                    mod = 'fom'
                    p = pe
            #print('sync_from_engine:', mod, p)
            setattr(self.study_config, ps,
                    getattr(getattr(self.study_config.engine.global_config,
                                    mod), p))


    def load_fom(self, schema):
        return self.study_config.engine.global_config.fom.load_fom(
            schema, self.study_config.engine.global_config)

