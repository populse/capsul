##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str, Undefined
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application
from capsul.study_config.study_config import StudyConfigModule


class FomConfig(StudyConfigModule):
    '''FOM (File Organization Model) configuration module for StudyConfig

    Note: FomConfig needs BrainVISAConfig to be part of StudyConfig modules.
    '''

    dependencies = ['BrainVISAConfig', 'SPMConfig']

    def __init__(self, study_config, configuration):
        super(FomConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait('use_fom', Bool(
            Undefined,
            output=False,
            desc='Use File Organization Models for file parameters completion'))
        self.study_config.add_trait('input_fom', Str(Undefined, output=False,
            desc='input FOM'))
        self.study_config.add_trait('output_fom', Str(Undefined, output=False,
            desc='output FOM'))
        self.study_config.add_trait('shared_fom', Str(Undefined, output=False,
            desc='shared data FOM'))
        self.study_config.add_trait('volumes_format', Str(Undefined, output=False,
            desc='Format used for volumes'))
        self.study_config.add_trait('meshes_format', Str(Undefined, output=False,
            desc='Format used for meshes'))

        # defaults
        self.study_config.input_fom = 'morphologist-auto-1.0'
        self.study_config.output_fom = 'morphologist-auto-1.0'
        self.study_config.shared_fom = 'shared-brainvisa-1.0'
        
            
    def initialize_module(self):
        '''Load configured FOMs and create FOM completion data in
        self.study_config.modules_data
        '''
        if self.study_config.use_fom is False:
            return
        
        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        soma_app.initialize()
        self.study_config.modules_data.foms = {}
        foms = (('input', self.study_config.input_fom),
            ('output', self.study_config.output_fom),
            ('shared', self.study_config.shared_fom))
        for fom_type, fom_filename in foms:
            fom = soma_app.fom_manager.load_foms(fom_filename)
            self.study_config.modules_data.foms[fom_type] = fom

        # Create FOM completion data in self.study_config.modules_data
        formats = tuple(getattr(self.study_config, key) \
            for key in self.study_config.user_traits() \
            if key.endswith('_format') \
                and getattr(self.study_config, key) is not Undefined)

        directories = {}
        directories['spm'] = self.study_config.spm_directory
        directories['shared'] = self.study_config.shared_directory
        directories['input'] = self.study_config.input_directory
        directories['output'] = self.study_config.output_directory

        self.study_config.modules_data.fom_atp = {}
        self.study_config.modules_data.fom_pta = {}

        for fom_type, fom in self.study_config.modules_data.foms.iteritems():
            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                prefered_formats=set((formats)))
            self.study_config.modules_data.fom_atp[fom_type] = atp
            pta = PathToAttributes(fom, selection={})
            self.study_config.modules_data.fom_pta[fom_type] = pta
        self.study_config.use_fom = True
    
    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module,
            ['use_fom', 'input_directory', 'input_fom', 'meshes_format',
             'output_directory', 'output_fom', 'shared_directory', 'shared_fom',
             'spm_directory', 'volumes_format'])

