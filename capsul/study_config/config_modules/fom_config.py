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
from traits.api import Bool, Str, Undefined
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from capsul.study_config.study_config import StudyConfigModule
from capsul.engine import CapsulEngine
import weakref


class FomConfig(StudyConfigModule):
    '''FOM (File Organization Model) configuration module for StudyConfig

    Note: FomConfig needs BrainVISAConfig to be part of StudyConfig modules.
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
        if 'capsul.engine.module.fom' \
                not in self.study_config.engine._loaded_modules:
            self.study_config.engine.load_module('capsul.engine.module.fom')

        # allow the methods to access StudyConfig (transciently)
        if isinstance(self.study_config, weakref.ProxyType):
            self.study_config.engine.global_config.fom.study_config \
                = self.study_config
        else:
            self.study_config.engine.global_config.fom.study_config \
                = weakref.proxy(self.study_config)

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which holds the reference values
            self.sync_from_engine()
        else:
            self.sync_to_engine()
            # 1st sync may have changed things
            self.sync_from_engine()



    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.sync_to_engine,
            ['use_fom', 'input_directory', 'input_fom', 'meshes_format',
             'output_directory', 'output_fom', 'shared_directory',
             'shared_fom', 'spm_directory', 'volumes_format'])
        self.study_config.engine.global_config.fom.on_trait_change(
            self.sync_from_engine,
            ['use','input_directory', 'input_fom', 'meshes_format',
             'output_directory', 'output_fom', 'shared_fom', 'volumes_format'])
        self.study_config.engine.global_config.spm.on_trait_change(
            self.sync_from_engine, 'directory')
        self.study_config.engine.global_config.axon.on_trait_change(
            self.sync_from_engine, 'shared_directory')


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


