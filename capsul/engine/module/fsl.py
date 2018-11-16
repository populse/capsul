import os
import os.path as osp
import six
import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from traits.api import File, Bool, Undefined, String, Instance

class FSLConfig(Controller):
    config = File(Undefined, output=False,
                  desc='Parameter to specify the fsl.sh path')
    prefix = String(Undefined,
                    desc='Prefix to add to FSL commands')
    use = Bool(Undefined,
               desc='Parameter to tell that FSL must be configured')
    
def load_module(capsul_engine, module_name):
    capsul_engine.add_trait('fsl', Instance(FSLConfig))
    capsul_engine.fsl = FSLConfig()
    capsul_engine.fsl.on_trait_change(SomaPartial(update_execution_context, 
                                                  weakref.proxy(capsul_engine)))

def init_module(capul_engine, module_name, loaded_module):
    if capul_engine.fsl.use is True:
        check_fsl_configuration(capul_engine)

def update_execution_context(capsul_engine):
    if capsul_engine.fsl.config is not Undefined:
        capsul_engine.execution_context.environ['FSL_CONFIG'] \
            = capsul_engine.fsl.config
        capsul_engine.study_config.fsl_config = capsul_engine.fsl.config
    if capsul_engine.fsl.prefix is not Undefined:
        capsul_engine.execution_context.environ['FSL_PREFIX'] \
            = capsul_engine.fsl.prefix
        capsul_engine.study_config.fsl_prefix = capsul_engine.fsl.prefix
    if capsul_engine.fsl.use is not Undefined:
        capsul_engine.study_config.use_fsl = capsul_engine.fsl.use


def check_fsl_configuration(study_config):
    '''
    Check thas study_config configuration is valid to call FSL commands.
    If not, try to automatically configure FSL. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''
    if getattr(study_config, '_fsl_config_checked', False):
        # Check FLS configuration only once
        return
    if 'FSLConfig' not in study_config.modules:
        raise EnvironmentError('FSLConfig module is missing in StudyConfig.')
    if study_config.use_fsl is False:
        raise EnvironmentError('Configuration is set not to use FLS. Set use_fsl to True in order to use FSL.')
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(study_config) is not None:
        auto_configuration(study_config)
        error_message = check_configuration_values(study_config)
        if error_message:
            raise EnvironmentError(error_message)
    study_config.use_fsl = True
    study_config._fsl_config_checked = True
    
def check_configuration_values(study_config):
    '''
    Check if the configuration is valid to run FLS and returns an error
    message if there is an error or None if everything is good.
    '''
    fsl_prefix = getattr(study_config, 'fsl_prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if study_config.fsl_config is Undefined:
        if not find_in_path('%sbet' % fsl_prefix):
            return 'FSL command "%sbet" cannot be found in PATH' % fsl_prefix
    else:
        if fsl_prefix:
            return 'FSL configuration must either use fsl_config or fsl_prefix but not both'
        if not osp.exists(study_config.fsl_config):
            return 'File "%s" does not exists' % study_config.fsl_config
        if not study_config.fsl_config.endswith('fsl.sh'):
            return 'File "%s" is not a path to fsl.sh script' % study_config.fsl_config    
    return None

def auto_configuration(study_config):
    '''
    Try to automatically set the study_config configuration for FSL.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    fsl_prefix = getattr(study_config, 'fsl_prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if fsl_dir and not fsl_prefix:
        # Try to set fsl_config from FSLDIR environment variable
        fsl_config = '%s/etc/fslconf/fsl.sh' % fsl_dir
        if osp.exists(fsl_config):
            study_config.fsl_config = fsl_config
    elif not fsl_prefix:
        # Try to set fsl_prefix by searching fsl-*bet in PATH
        bet = find_in_path('fsl*-bet')
        if bet:
            study_config.fsl_prefix = osp.basename(bet)[:-3]

