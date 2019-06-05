import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from traits.api import File, Undefined, Instance

class MatlabConfig(Controller):
    executable = File(Undefined, output=False,
                      desc='Full path of the matlab executable')
    
def load_module(capsul_engine, module_name):
    capsul_engine.global_config.add_trait('matlab', Instance(MatlabConfig))
    capsul_engine.global_config.matlab = MatlabConfig()

def init_module(capul_engine, module_name, loaded_module):
    pass


def build_environ(config, environ):
  environ['MATLAB_EXECUTABLE'] = config['matlab']['executable']

