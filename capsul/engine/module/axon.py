
'''
Configuration module which links with `Axon <http://brainvisa.info/axon/user_doc>`_

Classes
=======
:class:`AxonConfig`
-------------------
'''

import os
import six
from soma.controller import Controller
from traits.api import Directory, Undefined, Instance
from soma import config as soma_config


class AxonConfig(Controller):
    '''
    Configuration module allowing to use `Axon <http://brainvisa.info/axon/user_doc>`_ shared data in Capsul processes

    Configuration variables:

    shared_directory: str
        directory for Brainvisa software shared data
    '''

    shared_directory = Directory(
        Undefined,
        output=False,
        desc='directory for Brainvisa software shared data')


def load_module(capsul_engine, module_name):
    capsul_engine.global_config.add_trait('axon',
                                          Instance(AxonConfig))
    capsul_engine.global_config.axon = AxonConfig()

    # link with StudyConfig
    if hasattr(capsul_engine, 'study_config') \
            and 'BrainVISAConfig' not in capsul_engine.study_config.modules:
        scmod = capsul_engine.study_config.load_module('BrainVISAConfig', {})
        scmod.initialize_module()
        scmod.initialize_callbacks()

