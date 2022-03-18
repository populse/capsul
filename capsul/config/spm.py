# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined


class SPMConfiguration(ModuleConfiguration):
    ''' SPM configuration module
    '''
    directory: Directory
    version: str
    standalone: bool = False

    def __init__(self):
        super().__init__()
        self.name = 'spm'

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
        config =  execution_context.config['modules']['spm']
        execution_context.spm = SPMConfiguration(**config)
