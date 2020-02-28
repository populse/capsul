# -*- coding: utf-8 -*-
'''
Classes
=======
:class:`Popen`
--------------

Functions
=========
:func:`find_spm`
----------------
:func:`check_spm_configuration`
-------------------------------
:func:`check_configuration_values`
----------------------------------
:func:`auto_configuration`
--------------------------
:func:`spm_command`
-------------------
:func:`call`
------------
:func:`check_call`
------------------
:func:`check_output`
--------------------
'''

from __future__ import absolute_import

import os.path as osp
import glob
import soma.subprocess
from traits.api import Undefined

from soma.path import find_in_path
from capsul.engine.module import spm as spm_engine

def find_spm(spm_version='', matlab_exec='matlab', matlab_path=None):
    """ Function to return the root directory of SPM.

    Parameters
    ----------
    spm_version: str (default='')
        if given, the version to use when running spm<version> in Matlab.
    matlab: str (default='matlab')
        if given, is the path to the Matlab executable.
    matlab_path: str (default None)
        if given, is a Matlab expression fed to addpath.

    Returns
    -------
    last_line: str
        the SPM root directory
    """
    # Script to execute with matlab in order to find SPM root dir
    script = ("spm%s;"
              "fprintf(1, '%%s', spm('dir'));"
              "exit();") % spm_version

    # Add matlab path if necessary
    if matlab_path:
        script = "addpath({0});".format(matlab_path) + script

    # Generate the matlab command
    command = [matlab_exec,
               "-nodisplay", "-nosplash", "-nojvm",
               "-r", script]

    # Try to execute the command
    try:
        last_line = soma.subprocess.check_output(command).decode('utf-8')
    except OSError:
        raise Exception("Could not find SPM.")

    # Do not consider weird data at the end of the line
    if '\x1b' in last_line:
        last_line = last_line[:last_line.index('\x1b')]

    # If the last line is empty, SPM not found
    if last_line == "":
        raise Exception("Could not find SPM.")

    return last_line

def check_spm_configuration(study_config):
    '''
    Obsolete.

    Check thas study_config configuration is valid to call SPM commands.
    If not, try to automatically configure SPM. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''
    if getattr(study_config, '_spm_config_checked', False):
        # Check SPM configuration only once
        return
    if 'SPMConfig' not in study_config.modules:
        raise EnvironmentError('SPMConfig module is missing in StudyConfig.')
    if study_config.use_spm is False:
        raise EnvironmentError('Configuration is set not to use SPM. Set use_spm to True in order to use SPM.')
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(study_config) is not None:
        auto_configuration(study_config)
        error_message = check_configuration_values(study_config)
        if error_message:
            raise EnvironmentError(error_message)
    study_config.use_spm = True
    study_config._spm_config_checked = True

def check_configuration_values(study_config):
    '''
    Obsolete.

    Check if the configuration is valid to run SPM and returns an error
    message if there is an error or None if everything is good.
    '''

    if study_config.spm_directory is Undefined:
        return 'No SPM directory defined'
    if not osp.isdir(study_config.spm_directory):
         return "'%s' is not a valid SPM directory" % study_config.spm_directory
    if study_config.spm_standalone is Undefined:
        return 'SPM standalone usage is undefined'
    if study_config.spm_standalone:
        if study_config.spm_exec is Undefined:
            return 'spm_exec must be defined to use SPM standalone'
        if not osp.isdir(study_config.spm_exec):
            return '"%s" is not a valid mrc directory for SPM standalone' % study_config.spm_exec
    else:
        if not study_config.use_matlab:
            return 'Matlab is disabled. Cannot use SPM via Matlab'



def auto_configuration(study_config):
    '''
    Obsolete.

    Try to automatically set the study_config configuration for SPM.
    '''
    if study_config.spm_directory is not Undefined and \
            osp.exists(study_config.spm_directory):
        spm_sh = glob.glob(osp.join(study_config.spm_directory, 'run_spm*.sh'))
        if spm_sh:
            if study_config.spm_standalone is Undefined:
                study_config.spm_standalone = True
            elif not study_config.spm_standalone:
                raise EnvironmentError('Requested SPM non standalone but '
                    'directory "%s" contains SPM standalone' % \
                        study_config.spm_directory)
            
            spm_version = spm_sh[0][:-3]
            spm_version = spm_version[spm_version.rfind('run_spm')+7:]
            if study_config.spm_version is Undefined:
                study_config.spm_version = spm_version
            elif study_config.spm_version != spm_version:
                raise EnvironmentError('Requested SPM %s but directory'
                    ' "%s" contains SPM %s' % (study_config.spm_version, 
                                               study_config.spm_directory, 
                                               spm_version))
            spm_exec = glob.glob(osp.join(study_config.spm_directory, 'mcr', 'v*'))
            if spm_exec:
                study_config.spm_exec = spm_exec[0]
        return
    
    # Matlab
    # determine SPM version (currently only 8 or 12 are supported)
    if study_config.spm_directory is not Undefined \
            and osp.isdir(osp.join(study_config.spm_directory, 'toolbox',
                                   'OldNorm')):
        spm_version = '12'
    elif study_config.spm_directory is not Undefined \
            and osp.isdir(osp.join(study_config.spm_directory, 'templates')):
        spm_version = '8'
    else:
        spm_version = Undefined
    if spm_version is not Undefined:
        if study_config.spm_version is Undefined:
            study_config.spm_version = spm_version
        elif study_config.spm_version != spm_version:
            raise EnvironmentError('Requested SPM %s but directory'
                ' "%s" contains SPM %s' % (study_config.spm_version, 
                                            study_config.spm_directory, 
                                            spm_version))


def spm_command(study_config, batch_file):
    if study_config.spm_standalone:
        cmd = [osp.join(study_config.spm_directory, 
                        'run_spm%s.sh' % study_config.spm_version),
               study_config.spm_exec,
               'script',
               batch_file]
        return cmd
    else:
        raise NotImplementedError('Running SPM with matlab is not '
                                  'implemented yet')

class Popen(soma.subprocess.Popen):
    '''
    Equivalent to Python soma.subprocess.Popen for SPM batch
    '''
    def __init__(self, study_config, batch_file, **kwargs):
        check_spm_configuration(study_config)
        cmd = spm_command(study_config, batch_file)
        super(Popen, self).__init__(cmd, **kwargs)
   

        
def call(study_config, batch_file, **kwargs):
    '''
    Equivalent to Python soma.subprocess.call for SPM batch
    '''
    check_spm_configuration(study_config)
    cmd = spm_command(study_config, batch_file)
    return soma.subprocess.call(cmd, **kwargs)

def check_call(study_config, batch_file, **kwargs):
    '''
    Equivalent to Python soma.subprocess.check_call for SPM batch
    '''
    check_spm_configuration(study_config)
    cmd = spm_command(study_config, batch_file)
    return soma.subprocess.check_call(cmd, **kwargs)


def check_output(study_config, batch_file, **kwargs):
    '''
    Equivalent to Python soma.subprocess.check_output for SPM batch
    '''
    check_spm_configuration(study_config)
    cmd = spm_command(study_config, batch_file)
    return soma.subprocess.check_output(cmd, **kwargs)

if __name__ == '__main__':
    from capsul.api import StudyConfig
    from capsul.soma.subprocess.spm import check_call as call_spm
    import tempfile
    
    sc = StudyConfig(spm_directory='/home/yc176684/spm12-standalone-7219')
    batch = tempfile.NamedTemporaryFile(suffix='.m')
    batch.write("fprintf(1, '%s', spm('dir'));")
    batch.flush()
    call_spm(sc, batch.name)
