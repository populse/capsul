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
    print('init_execution_context nipype')
    pymods = execution_context.config.setdefault('python_modules', [])
    if 'capsul.runtime.nipype' not in pymods:
        pymods.append('capsul.runtime.nipype')

    config = execution_context.config['modules']['nipype']
    execution_context.nipype = NipypeConfiguration()
    execution_context.nipype.import_from_dict(config)
    for module in ('matlab', 'spm', 'fsl', 'freesurfer', 'afni', 'ants'):
        if module in execution_context.config['modules']:
            mod = __import__('.%s' % module)
            init = getattr(mod, 'init_execution_context', None)
            if init:
                init(execution_context)
