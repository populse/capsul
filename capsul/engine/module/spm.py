# -*- coding: utf-8 -*-
from __future__ import absolute_import

from capsul import engine
import os
import six

#import glob
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


def activate_configurations():
    '''
    Activate the SPM module (set env variables) from the global configurations,
    in order to use them via :mod:`capsul.in_context.spm` functions
    '''
    conf = engine.configurations.get('capsul.engine.module.spm', {})
    mlab_conf = engine.configurations.get('capsul.engine.module.matlab', {})
    spm_dir = conf.get('directory')
    mcr_dir = mlab_conf.get('mcr_directory')
    if spm_dir:
        os.environ['SPM_DIRECTORY'] = six.ensure_str(spm_dir)
    elif 'SPM_DIRECTORY' in os.environ:
        del os.environ['SPM_DIRECTORY']
    spm_version = conf.get('version')
    if spm_version:
        os.environ['SPM_VERSION'] = six.ensure_str(spm_version)
    elif 'SPM_VERSION' in os.environ:
        del os.environ['SPM_VERSION']
    spm_standalone = conf.get('standalone')
    if spm_standalone is not None:
        os.environ['SPM_STANDALONE'] = 'yes' if spm_standalone else 'no'
        if spm_standalone and mcr_dir:
            os.environ['MCR_HOME'] = mcr_dir
    elif 'SPM_STANDALONE' in os.environ:
        del os.environ['SPM_STANDALONE']


def edition_widget(engine, environment, config_id='any'):
    ''' Edition GUI for SPM config - see
    :class:`~capsul.qt_gui.widgets.settings_editor.SettingsEditor`
    '''
    from soma.qt_gui.controller_widget import ScrollControllerWidget
    from soma.controller import Controller
    import types
    import traits.api as traits

    def validate_config(widget):
        widget.update_controller()
        controller = widget.controller_widget.controller
        with widget.engine.settings as session:
            values = {}
            if controller.directory in (None, traits.Undefined, ''):
                values['directory'] = None
            else:
                values['directory'] = controller.directory
            values['standalone'] = controller.standalone
            if controller.version in (None, traits.Undefined, ''):
                values['version'] = None
            else:
                values['version'] = controller.version
            id = 'spm%s%s' % (controller.version if
                              controller.version != traits.Undefined else '',
                              '-standalone' if controller.standalone else '')
            values['config_id'] = id
            query = 'config_id == "%s"' % id
            conf = session.config('spm', widget.environment, selection=query)
            if conf is None:
                session.new_config('spm', widget.environment, values)
            else:
                for k in ('directory', 'standalone', 'version'):
                    if (k == 'directory' and
                               values[k] and
                               not os.path.isdir(values[k])):
                        raise NotADirectoryError('\nSPM directory was not '
                                                 'updated:\n{} is not '
                                                 'existing!'.format(values[k]))
                    else:
                        setattr(conf, k, values[k])
            if id != widget.config_id:
                try:
                    session.remove_config('spm', widget.environment,
                                          widget.config_id)
                except Exception:
                    pass
                widget.config_id = id

    controller = Controller()
    controller.add_trait("directory", traits.Directory(
        traits.Undefined,
        output=False,
        desc="Directory containing SPM."))
    controller.add_trait("standalone", traits.Bool(
        False,
        desc="If True, use the standalone version of SPM."))
    controller.add_trait('version', traits.Str(
        traits.Undefined, output=False,
        desc='Version string for SPM: "12", "8", etc.'))

    conf = None
    if config_id == 'any':
        conf = engine.settings.select_configurations(
            environment, {'spm': 'any'})
    else:
        try:
            conf = engine.settings.select_configurations(
                environment, {'spm': 'config_id=="%s"' % config_id})
        except Exception:
            pass
    if conf:
        controller.directory = conf.get(
            'capsul.engine.module.spm', {}).get('directory',
                                                traits.Undefined)
        controller.standalone = conf.get(
            'capsul.engine.module.spm', {}).get('standalone', False)
        controller.version = conf.get(
            'capsul.engine.module.spm', {}).get('version', traits.Undefined)
        config_id = conf.get(
            'capsul.engine.module.spm', {}).get('config_id', config_id)

    # TODO handle several configs

    widget = ScrollControllerWidget(controller, live=True)
    widget.engine = engine
    widget.environment = environment
    widget.config_id = config_id
    widget.accept = types.MethodType(validate_config, widget)

    return widget
