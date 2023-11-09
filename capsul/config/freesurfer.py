from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field


class FreesurferConfiguration(ModuleConfiguration):
    ''' Freesurfer configuration module
    '''
    version: str
    setup_script: File = field(optional=True)
    subjects_dir: Directory = field(optional=True)
    name = 'freesurfer'

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
    config =  execution_context.config['modules']['freesurfer']
    execution_context.freesurfer = FreesurferConfiguration()
    execution_context.freesurfer.import_from_dict(config)
