# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class MatlabConfiguration(ModuleConfiguration):
    ''' Matlab configuration module
    '''
    executable: File = field(optional=True)
    mcr_directory: Directory = field(optional=True)
    version: str
    name = 'matlab'

    def is_valid_config(self, requirements):
        required_version = requirements.get('version')
        if required_version \
                and getattr(self, 'version', undefined) != required_version:
            return False
        return True

def init_execution_context(execution_context):
    '''
    Configure an execution context given a capsul_engine and some requirements.
    '''
    config =  execution_context.config['modules']['matlab']
    execution_context.matlab = MatlabConfiguration()
    execution_context.matlab.import_dict(config)
