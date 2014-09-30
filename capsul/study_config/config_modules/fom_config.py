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

class FomConfig(object):
    '''FOM (File Organization Model) configuration module for StudyConfig
    '''
    def __init__(self, study_config):
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

        # defaults
        study_config.input_fom = 'morphologist-auto-1.0'
        study_config.output_fom = 'morphologist-auto-1.0'
        study_config.shared_fom = 'shared-brainvisa-1.0'

    @staticmethod
    def check_and_update_foms(study_config):
        '''Load configured FOMs and create FOM completion data in
        study_config.modules_data
        '''
        study_config.modules_data.foms = {}
        foms = (('input', study_config.input_fom),
            ('output', study_config.output_fom),
            ('shared', study_config.shared_fom))
        for fom_type, fom_filename in foms:
            fom = Application().fom_manager.load_foms(fom_filename)
            study_config.modules_data.foms[fom_type] = fom

        FomConfig.create_attributes_with_fom(study_config)

    @staticmethod
    def create_attributes_with_fom(study_config):
        '''Create FOM completion data in study_config.modules_data
        '''
        formats = tuple(getattr(study_config, key) \
            for key in study_config.user_traits() if key.startswith('format'))

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

