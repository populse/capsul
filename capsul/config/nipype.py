# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class NipypeConfiguration(ModuleConfiguration):
    ''' Nipype configuration module
    '''
    name = 'nipype'

    def is_valid_config(self, requirements):
        return True

def init_execution_context(execution_context):
    '''
    Configure an execution context given a capsul_engine and some requirements.
    '''
    config =  execution_context.config['modules']['nipype']
    execution_context.nipype = NipypeConfiguration()
    execution_context.nipype.import_from_dict(config)
