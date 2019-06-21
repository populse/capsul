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
from traits.api import Bool, Str, Undefined, Instance, Directory
from soma.controller import Controller
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
import weakref


class FomConfig(Controller):
    '''FOM (File Organization Model) configuration module for CapsulEngine
    '''

    input_fom = Str("", output=False, desc='input FOM')
    output_fom = Str("", output=False, desc='output FOM')
    shared_fom = Str("", output=False, desc='shared data FOM')
    volumes_format = Str(Undefined, output=False,
                         desc='Format used for volumes')
    meshes_format = Str(Undefined, output=False,
                        desc='Format used for meshes')
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


    def update_fom(self, capsul_config):
        '''Load configured FOMs and create FOM completion data
        '''
        print('***update_fom ***')
        if self.use is False:
            print('do nothing.')
            return

        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        if 'soma.fom' not in soma_app.loaded_plugin_modules:
            # WARNING: this is unsafe, may erase configured things, and
            # probably not thread-safe.
            soma_app.initialize()
        self.foms = {}
        foms = (('input', self.input_fom),
            ('output', self.output_fom),
            ('shared', self.shared_fom))
        for fom_type, fom_filename in foms:
            if fom_filename != "":
                fom = soma_app.fom_manager.load_foms(fom_filename)
                self.foms[fom_type] = fom

        # Create FOM completion data
        formats = tuple(getattr(self, key) \
            for key in self.user_traits() \
            if key.endswith('_format') and getattr(self, key) is not Undefined)

        directories = {}
        if hasattr(capsul_config, 'spm'):
            directories['spm'] = capsul_config.spm.directory
        if hasattr(capsul_config, 'axon'):
            directories['shared'] = capsul_config.axon.shared_directory
        directories['input'] = self.input_directory
        directories['output'] = self.output_directory

        self.fom_atp = {}
        self.fom_pta = {}

        for fom_type, fom in six.iteritems(self.foms):
            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                preferred_formats=set((formats)))
            self.fom_atp[fom_type] = atp
            pta = PathToAttributes(fom, selection={})
            self.fom_pta[fom_type] = pta
        self.use = True
        print('use: True')

        # backward compatibility for StudyConfig
        self.study_config.modules_data.foms = self.foms
        self.study_config.modules_data.fom_atp = self.fom_atp
        self.study_config.modules_data.fom_pta = self.fom_pta


def load_module(capsul_engine, module_name):
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

    capsul_engine.global_config.fom.on_trait_change(
        capsul_engine.global_config.fom.update_fom,
        ['input_fom', 'output_fom', 'shared_fom', 'volumes_format',
         'meshes_format', 'use', 'input_directory', 'output_directory'])
    capsul_engine.global_config.axon.on_trait_change(
        capsul_engine.global_config.fom.update_fom, 'shared_directory')
    capsul_engine.global_config.spm.on_trait_change(
        capsul_engine.global_config.fom.update_fom, 'directory')


