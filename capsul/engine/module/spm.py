import glob
import os
import os.path as osp
import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from traits.api import Directory, Undefined, Instance, String, Bool

class SPMConfig(Controller):
    directory = Directory(Undefined, output=False,
                          desc='Directory where SPM is installed')
    version = String(Undefined, output=False,
                     desc='Version of SPM release (8 or 12)')
    standalone = Bool(Undefined, output=False,
                      desc='If this parameter is set to True, use the '
                      'standalone SPM version, otherwise use Matlab.')
    use = Bool(Undefined, output=False,
               desc='If this parameter is set to True, the SPM '
                    'configuration is checked and must be valid '
                    'otherwise an error is raised.')
    
def load_module(capsul_engine, module_name):
    capsul_engine.load_module('capsul.engine.module.matlab')
    capsul_engine.add_trait('spm', Instance(SPMConfig))
    capsul_engine.spm = SPMConfig()
    capsul_engine.spm.on_trait_change(SomaPartial(update_execution_context, 
                                                  weakref.proxy(capsul_engine)))

def init_module(capul_engine, module_name, loaded_module):
    if capul_engine.spm.use is True:
        check_spm_configuration(capul_engine)


def update_execution_context(capsul_engine):
    for attr, var in (('directory', 'SPM_DIRECTORY'),
                      ('version', 'SPM_VERSION'),
                      ('standalone', 'SPM_STANDALONE')):
        value = getattr(capsul_engine.spm, attr)
        if value is not Undefined:
            capsul_engine.execution_context.environ[var] = str(value)

def check_spm_configuration(capsul_engine):
    '''
    Check thas capsul_engine configuration is valid to call SPM commands.
    If not, try to automatically configure SPM. Finally raises an
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
    Check if the configuration is valid to run SPM and returns an error
    message if there is an error or None if everything is good.
    '''
    if capsul_engine.spm.directory is Undefined:
        return 'SPM directory is not defined'
    if capsul_engine.spm.version is Undefined:
        return 'SPM version is not defined (maybe %s is not a valid SPM directory)' % capsul_engine.spm.directory
    if capsul_engine.spm.standalone is Undefined:
        return 'Selection of SPM installation type : Standalone or Matlab'
    if not osp.isdir(capsul_engine.spm.directory):
        return 'No valid SPM directory: %s' % capsul_engine.spm.directory
    if not capsul_engine.spm.standalone:
        if capsul_engine.matlab.executable is Undefined:
            return 'Matlab executable must be defined for SPM'
    return None

def auto_configuration(capsul_engine):
    '''
    Try to automatically set the capsul_engine configuration for SPM.
    '''
    if capsul_engine.spm.directory is not Undefined:
        mcr = glob.glob(osp.join(capsul_engine.spm.directory, 'spm*_mcr'))
        if mcr:
            capsul_engine.spm.version = osp.basename(mcr[0])[3:-4]
            capsul_engine.spm.standalone = True
        else:
            capsul_engine.spm.standalone = False
            # determine SPM version (currently 8 or 12)
            if osp.isdir(osp.join(
                    capsul_engine.spm.directory, 'toolbox', 'OldNorm')):
                capsul_engine.spm.version = '12'
            elif os.path.isdir(os.path.join(
                capsul_engine.spm.directory, 'templates')):
                capsul_engine.spm.version = '8'
            else:
                if capsul_engine.spm.version is not Undefined:
                    del capsul_engine.spm.version



