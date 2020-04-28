# -*- coding: utf-8 -*-
from __future__ import absolute_import

#import glob
#import os
#import os.path as osp
#import weakref
##import subprocess # Only in case of matlab call (auto_configuration func)

#from soma.controller import Controller
#from traits.api import Directory, Undefined, Instance, String, Bool

#from . import matlab
    

def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('spm',
            [dict(name='directory',
                type='string',
                description='Directory where SPM is installed'),
            dict(name='version',
                type='string',
                description='Version of SPM release (8 or 12)'),
            dict(name='standalone',
                type='boolean',
                description='If this parameter is set to True, use the '
                            'standalone SPM version, otherwise use Matlab.')
            ])
        settings


def config_dependencies(config):
        if not config['standalone']:
            return {'matlab': 'any'}

#def set_environ(config, environ):
    #spm_config = config.get('spm', {})
    #use = spm_config.get('use')
    #if  use is True or (use is None and 'directory' in spm_config):
        #error_message = check_environ(environ)
        #if error_message:
            #complete_environ(config, environ)
        #error_message = check_environ(environ)

        #if error_message:
            #raise EnvironmentError(error_message)

    
#def check_environ(environ):
    #'''
    #Check if the configuration is valid to run SPM and returns an error
    #message if there is an error or None if everything is good.
    #'''
    #if not environ.get('SPM_DIRECTORY'):
        #return 'SPM directory is not defined'
    #if not environ.get('SPM_VERSION'):
        #return 'SPM version is not defined (maybe %s is not a valid SPM directory)' % environ['SPM_DIRECTORY']
    #if not environ.get('SPM_STANDALONE'):
        #return 'No selection of SPM installation type : Standalone or Matlab'
    #if not osp.isdir(environ['SPM_DIRECTORY']):
        #return 'No valid SPM directory: %s' % environ['SPM_DIRECTORY']
    #if environ['SPM_STANDALONE'] != 'yes':
        #matlab_error = matlab.check_environ(environ)
        #if matlab_error:
            #return 'Matlab configuration must be valid for SPM: ' + matlab_error
    #return None

#def complete_environ(config, environ):
    #'''
    #Try to automatically complete environment for SPM
    #'''
    #spm_directory = config.get('spm', {}).get('directory')
    #if spm_directory:
        #environ['SPM_DIRECTORY'] = spm_directory
        #mcr = glob.glob(osp.join(spm_directory, 'spm*_mcr'))
        #if mcr:
            #fileName = osp.basename(mcr[0])
            #inc = 1

            #while fileName[fileName.find('spm') + 3:
                           #fileName.find('spm') + 3 + inc].isdigit():
                #environ['SPM_VERSION'] = fileName[fileName.find('spm') + 3:
                                                  #fileName.find('spm') + 3
                                                                       #+ inc]
                #inc+=1
        
            #environ['SPM_STANDALONE'] = 'yes'
            
        #else:
            #environ['SPM_STANDALONE'] = 'no'
            ## determine SPM version (currently 8 or 12)
            #if osp.isdir(osp.join(spm_directory, 'toolbox', 'OldNorm')):
                #environ['SPM_VERSION'] = '12'
            #elif osp.isdir(osp.join(spm_directory, 'templates')):
                #environ['SPM_VERSION'] = '8'
            #else:
                #environ.pop('SPM_VERSION', None)

# For SPM with MATLAB license, if we want to get the SPM version from a system
# call to matlab:.
#            matlab_cmd = ('addpath("' + capsul_engine.spm.directory + '");'
#                          ' [name, ~]=spm("Ver");'
#                          ' fprintf(2, \"%s\", name(4:end));'
#                          ' exit')
#
#            try:
#                p = subprocess.Popen([capsul_engine.matlab.executable,
#                                       '-nodisplay', '-nodesktop',
#                                       '-nosplash', '-singleCompThread',
#                                       '-batch', matlab_cmd],
#                                     stdin=subprocess.PIPE,
#                                     stdout=subprocess.PIPE,
#                                     stderr=subprocess.PIPE)
#                output, err = p.communicate()
#                rc = p.returncode
#
#            except FileNotFoundError as e:
#                print('\n {0}'.format(e))
#                rc = 111
#
#            except Exception as e:
#                print('\n {0}'.format(e))
#                rc = 111
#
#            if (rc != 111) and (rc != 0):
#                print(err)
#
#            if rc == 0:
#                 capsul_engine.spm.version = err.decode("utf-8")
#
