#import os
#import weakref

#from soma.controller import Controller
#from traits.api import File, Undefined, Instance

    
def load_module(config, collection):
    config.add_field(collection, 'executable',
                     description='Full path of the matlab executable')


#def set_environ(config, environ):
    #matlab_executable = config.get('matlab', {}).get('executable')
    #if matlab_executable:
        #environ['MATLAB_EXECUTABLE'] = matlab_executable
        #error = check_environ(environ)
        #if error:
            #raise EnvironmentError(error)

#def check_environ(environ):
    #matlab_executable = environ.get('MATLAB_EXECUTABLE')
    #if not matlab_executable:
        #return 'MATLAB_EXECUTABLE is not defined'
    #if not os.path.exists(matlab_executable):
        #return 'Matlab executable is defined as "%s" but this path does not exist' % matlab_executable
    #return None

    



