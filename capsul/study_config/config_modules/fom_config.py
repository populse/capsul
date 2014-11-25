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
        study_config.add_trait('use_fom', Bool(
            False,
            output=False,
            desc='Use File Organization Models for file parameters completion'))
        study_config.add_trait('input_fom', Str(Undefined, output=False,
            desc='input FOM'))
        study_config.add_trait('output_fom', Str(Undefined, output=False,
            desc='output FOM'))
        study_config.add_trait('shared_fom', Str(Undefined, output=False,
            desc='shared data FOM'))
        study_config.add_trait('volumes_format', Str(Undefined, output=False,
            desc='Format used for volumes'))
        study_config.add_trait('meshes_format', Str(Undefined, output=False,
            desc='Format used for meshes'))

        # defaults
        study_config.input_fom = 'morphologist-auto-1.0'
        study_config.output_fom = 'morphologist-auto-1.0'
        study_config.shared_fom = 'shared-brainvisa-1.0'

    def initialize_module(self, study_config):
        '''Load configured FOMs and create FOM completion data in
        study_config.modules_data
        '''
        soma_app = Application('capsul', plugin_modules=['soma.fom'])
        soma_app.initialize()
        study_config.modules_data.foms = {}
        foms = (('input', study_config.input_fom),
            ('output', study_config.output_fom),
            ('shared', study_config.shared_fom))
        for fom_type, fom_filename in foms:
            fom = soma_app.fom_manager.load_foms(fom_filename)
            study_config.modules_data.foms[fom_type] = fom

        # Create FOM completion data in study_config.modules_data
        formats = tuple(getattr(study_config, key) \
            for key in study_config.user_traits() \
            if key.endswith('_format') \
                and getattr(study_config, key) is not Undefined)

        directories = {}
        directories['spm'] = study_config.spm_directory
        directories['shared'] = study_config.shared_directory
        directories['input'] = study_config.input_directory
        directories['output'] = study_config.output_directory

        study_config.modules_data.fom_atp = {}
        study_config.modules_data.fom_pta = {}

        for fom_type, fom in study_config.modules_data.foms.iteritems():
            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                prefered_formats=set((formats)))
            study_config.modules_data.fom_atp[fom_type] = atp
            pta = PathToAttributes(fom, selection={})
            study_config.modules_data.fom_pta[fom_type] = pta

