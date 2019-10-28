#import os
#import os.path as osp
#import six
#import weakref

#from soma.controller import Controller
#from soma.functiontools import SomaPartial
#from soma.path import find_in_path
#from traits.api import File, Bool, Undefined, String, Directory, Instance
#from soma.path import find_in_path


def load_module(config, collection):
    config.add_field(collection, 'directory', 'string',
                     description='Directory where FSL is installed')
    config.add_field(collection, 'config', 'string',
                     description='fsl.sh path')
    config.add_field(collection, 'prefix', 'string',
                     description='Prefix to add to FSL commands')


#def set_environ(config, environ):
    #fsl_config = config.get('fsl', {})
    #use = fsl_config.get('use')
    #if  use is True or (use is None and fsl_config):
        #error_message = check_environ(environ)
        #if error_message:
            #complete_environ(config, environ)
        #error_message = check_environ(environ)
        #if error_message:
            #raise EnvironmentError(error_message)

    
#def check_environ(environ):
    #'''
    #Check if the configuration is valid to run FLS and returns an error
    #message if there is an error or None if everything is good.
    #'''
    #fsl_prefix = environ.get('FSL_PREFIX', '')
    #fsl_config = environ.get('FSL_CONFIG')
    #if not fsl_config:
        #if not find_in_path('%sbet' % fsl_prefix):
            #return 'FSL command "%sbet" cannot be found in PATH' % fsl_prefix
    #else:
        #if fsl_prefix:
            #return 'FSL configuration must either use fsl.config or fsl.prefix but not both'
        #if not osp.exists(fsl_config):
            #return 'File "%s" does not exists' % fsl_config
        #if not fsl_config.endswith('fsl.sh'):
            #return 'File "%s" is not a path to fsl.sh script' % fsl_config
    #return None


#def complete_environ(config, environ):
    #'''
    #Try to automatically set the capsul_engine configuration for FSL.
    #'''
    #fsl_config = config.get('fsl', {})
    #fsl_dir = fsl_config.get('directory', os.environ.get('FSLDIR'))
    #fsl_prefix = environ.get('FSL_PREFIX', '')
    #if fsl_dir and not fsl_prefix:
        ## Try to set fsl_config from FSLDIR environment variable
        #fsl_config = '%s/etc/fslconf/fsl.sh' % fsl_dir
        #if osp.exists(fsl_config):
            #environ['FSL_CONFIG'] = fsl_config
    #elif not fsl_prefix:
        ## Try to set fsl_prefix by searching fsl-*bet in PATH
        #bet = find_in_path('fsl*-bet')
        #if bet:
            #environ['FSL_PREFIX'] = osp.basename(bet)[:-3]
