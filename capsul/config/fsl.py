# -*- coding: utf-8 -*-

from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class FSLConfiguration(ModuleConfiguration):
    ''' FSL configuration module
    '''
    directory: Directory = field(optional=True)
    version: str
    setup_script: File = field(optional=True)
    prefix: str = field(optional=True)

    def __init__(self):
        super().__init__()
        self.name = 'fsl'

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
        config =  execution_context.config['modules']['fsl']
        execution_context.fsl = FSLConfiguration(**config)
