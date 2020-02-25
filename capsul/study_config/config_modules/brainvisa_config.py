##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_

Classes
=======
:class:`BrainVISAConfig`
------------------------
'''

from __future__ import print_function
from __future__ import absolute_import
import os
from traits.api import Directory, Undefined
from soma import config as soma_config
from capsul.study_config.study_config import StudyConfigModule


class BrainVISAConfig(StudyConfigModule):
    '''
    Configuration module allowing to use `BrainVISA / Axon <http://brainvisa.info/axon/user_doc>`_ shared data in Capsul processes.

    This module adds the following options (traits) in the
    :class:`~capsul.study_config.study_config.StudyConfig` object:

    shared_directory: str (filename)
        Study shared directory
     '''

    def __init__(self, study_config, configuration):
        super(BrainVISAConfig, self).__init__(study_config, configuration)
        study_config.add_trait('shared_directory',Directory(
            Undefined,
            output=False,
            desc='Study shared directory'))

        study_config.shared_directory = soma_config.BRAINVISA_SHARE
        # the following would be good but if Axon is not present, it will
        # use an unavailable FOM and cause an error.
        #if 'FomConfig' in self.study_config.modules \
                #and self.study_config.shared_fom in (None, ''):
            #self.study_config.shared_fom = 'shared-brainvisa-1.0'


    def initialize_module(self):
        '''
        '''
        from capsul.engine import CapsulEngine

        if type(self.study_config.engine) is not CapsulEngine:
            # engine is a proxy, thus we are initialized from a real
            # CapsulEngine, which should hold the reference values,
            # BUT values are actuallu defined from here...
            old_shared = self.study_config.shared_directory
            if self.study_config.engine.global_config.axon.shared_directory \
                    is Undefined:
                self.study_config.engine.global_config.axon.shared_directory \
                    = old_shared
            self.sync_from_engine()
        else:
            # otherwise engine is "owned" by StudyConfig
            if 'capsul.engine.module.axon' \
                    not in self.study_config.engine.modules:
                self.study_config.engine.modules.append(
                    'capsul.engine.module.axon')
                self.study_config.engine.load_modules()
            self.sync_to_engine()


    def initialize_callbacks(self):
        self.study_config.on_trait_change(self.sync_to_engine,
                                          'shared_directory')

        self.study_config.engine.global_config.axon.on_trait_change(
            self.sync_from_engine, 'shared_directory')


    def sync_to_engine(self, param=None, value=None):
        if param is not None:
            setattr(self.study_config.engine.global_config.axon, param,
                    value)
        else:
            self.study_config.engine.global_config.axon.shared_directory \
                = self.study_config.shared_directory


    def sync_from_engine(self, param=None, value=None):
        if param is not None:
            setattr(self.study_config, param, value)
        else:
            self.study_config.shared_directory \
                = self.study_config.engine.global_config.axon.shared_directory

