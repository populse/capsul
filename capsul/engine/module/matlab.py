from __future__ import absolute_import
import os
import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from traits.api import File, Undefined, Instance

class MatlabConfig(Controller):
    '''
    Matlab software configuration module for :class:`~capsul.engine.capsulEngine`

    Configuration variables:

    executable: str
        Full path of the matlab executable
    '''
    executable = File(Undefined, output=False,
                      desc='Full path of the matlab executable')
    
def load_module(capsul_engine, module_name):
    capsul_engine.global_config.add_trait('matlab', Instance(MatlabConfig))
    capsul_engine.global_config.matlab = MatlabConfig()


def set_environ(config, environ):
    matlab_executable = config.get('matlab', {}).get('executable')
    if matlab_executable:
        environ['MATLAB_EXECUTABLE'] = matlab_executable
        error = check_environ(environ)
        if error:
            raise EnvironmentError(error)

def check_environ(environ):
    matlab_executable = environ.get('MATLAB_EXECUTABLE')
    if not matlab_executable:
        return 'MATLAB_EXECUTABLE is not defined'
    if not os.path.exists(matlab_executable):
        return 'Matlab executable is defined as "%s" but this path does not exist' % matlab_executable
    return None

    



