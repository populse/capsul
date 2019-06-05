import os
import os.path as osp
import six
import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from soma.path import find_in_path
from traits.api import File, Bool, Undefined, String, Instance
from soma.path import find_in_path

class FSLConfig(Controller):
    config = File(Undefined, output=False,
                  desc='Parameter to specify the fsl.sh path')
    prefix = String(Undefined,
                    desc='Prefix to add to FSL commands')
    use = Bool(Undefined,
               desc='Parameter to tell that FSL must be configured')
    
def load_module(capsul_engine, module_name):
    capsul_engine.global_config.add_trait('fsl', Instance(FSLConfig))
    capsul_engine.global_config.fsl = FSLConfig()


def init_module(capul_engine, module_name, loaded_module):
    if capul_engine.global_config.  fsl.use is True:
        check_fsl_configuration(capul_engine)

def build_environ(config, environ):
    if 'fsl' in config:
        environ['FSL_CONFIG'] = config['fsl']['config']
        environ['FSL_PREFIX'] = config['fsl'].get('prefix', '')


def check_fsl_configuration(capsul_engine):
    '''
    Check thas capsul_engine configuration is valid to call FSL commands.
    If not, try to automatically configure FSL. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(capsul_engine) is not None:
        auto_configuration(capsul_engine)
        error_message = check_configuration_values(capsul_engine)
        if error_message:
            raise EnvironmentError(error_message)
    
def check_configuration_values(capsul_engine):
    '''
    Check if the configuration is valid to run FLS and returns an error
    message if there is an error or None if everything is good.
    '''
    fsl_prefix = getattr(capsul_engine.global_config.fsl, 'prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if capsul_engine.global_config.fsl.config is Undefined:
        if not find_in_path('%sbet' % fsl_prefix):
            return 'FSL command "%sbet" cannot be found in PATH' % fsl_prefix
    else:
        if fsl_prefix:
            return 'FSL configuration must either use fsl.config or fsl.prefix but not both'
        if not osp.exists(capsul_engine.global_config.fsl.config):
            return 'File "%s" does not exists' % capsul_engine.global_config.fsl.config
        if not capsul_engine.global_config.fsl.config.endswith('fsl.sh'):
            return 'File "%s" is not a path to fsl.sh script' % capsul_engine.global_config.fsl.config
    return None

def auto_configuration(capsul_engine):
    '''
    Try to automatically set the capsul_engine configuration for FSL.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    fsl_prefix = getattr(capsul_engine.global_config.fsl, 'prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if fsl_dir and not fsl_prefix:
        # Try to set fsl_config from FSLDIR environment variable
        fsl_config = '%s/etc/fslconf/fsl.sh' % fsl_dir
        if osp.exists(fsl_config):
            capsul_engine.global_config.fsl.config = fsl_config
    elif not fsl_prefix:
        # Try to set fsl_prefix by searching fsl-*bet in PATH
        bet = find_in_path('fsl*-bet')
        if bet:
            capsul_engine.global_config.fsl.prefix = osp.basename(bet)[:-3]

