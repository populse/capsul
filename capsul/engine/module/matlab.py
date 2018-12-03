import weakref

from soma.controller import Controller
from soma.functiontools import SomaPartial
from traits.api import File, Undefined, Instance

class MatlabConfig(Controller):
    executable = File(Undefined, output=False,
                      desc='Full path of the matlab executable')
    
def load_module(capsul_engine, module_name):
    capsul_engine.add_trait('matlab', Instance(MatlabConfig))
    capsul_engine.matlab = MatlabConfig()
    capsul_engine.matlab.on_trait_change(SomaPartial(update_execution_context, 
                                                     weakref.proxy(capsul_engine)))

def init_module(capul_engine, module_name, loaded_module):
    pass


def update_execution_context(capsul_engine):
    if capsul_engine.matlab.executable is not Undefined:
        capsul_engine.execution_context.environ['MATLAB_EXECUTABLE'] \
            = capsul_engine.matlab.executable

