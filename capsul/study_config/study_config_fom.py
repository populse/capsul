#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.study_config.study_config2 import StudyConfig
from soma.fom import AttributesToPaths, PathToAttributes
from soma.application import Application

class StudyConfigFomManager(object):

    @staticmethod
    def check_and_update_foms(study_config):
        study_config.internal_data.foms = {}
        foms = (('input', study_config.input_fom),
            ('output', study_config.output_fom))
        for fom_type, fom_filename in foms:
            fom = Application().fom_manager.load_foms(fom_filename)
            study_config.internal_data.foms[fom_type] = fom

        StudyConfigFomManager.create_attributes_with_fom(study_config)

    @staticmethod
    def create_attributes_with_fom(study_config):
        """To get useful attributes by the fom"""
        formats = tuple(getattr(study_config, key) \
            for key in study_config.user_traits() if key.startswith('format'))

        directories = {}
        directories['spm'] = study_config.spm_directory
        directories['shared'] = study_config.shared_directory
        directories['input'] = study_config.input_directory
        directories['output'] = study_config.output_directory

        study_config.internal_data.atp = {}
        study_config.internal_data.pta = {}

        for fom_type, fom in study_config.internal_data.foms.iteritems():
            atp = AttributesToPaths(
                fom,
                selection={},
                directories=directories,
                prefered_formats=set((formats)))
            study_config.internal_data.atp[fom_type] = atp
            pta = PathToAttributes(fom, selection={})
            study_config.internal_data.pta[fom_type] = pta

