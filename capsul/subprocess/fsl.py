# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call FSL taking into account a 
potential configuration done in StudyConfig. If a StudyConfig is not
configured to use FSL, it may be automatically configured. Automatic
configuration had been tested in the two following cases:

- FSL was installed from the FMRIB site and, at least, FSLDIR 
  environment variable is set (fsl.sh can be sourced or not)
- FSL was installed from Neurodebian packages

For calling FSL command with this module, the first arguent of
command line must be the FSL executable without any path nor prefix. 
Prefix areused  in Neurodebian install. For instance on Ubuntu 16.04 
Neurodebian FSL commands are prefixed with "fsl5.0-".
The appropriate path and eventually prefix are added from the configuration
of the StudyConfig instance.

Classes
=======
:class:`Popen`
--------------

Functions
=========
:func:`fsl_command_with_environment`
------------------------------------
:func:`check_fsl_configuration`
-------------------------------
:func:`check_configuration_values`
----------------------------------
:func:`auto_configuration`
--------------------------
:func:`call`
------------
:func:`check_call`
------------------
:func:`check_output`
--------------------

'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess

from traits.api import Undefined

from soma.path import find_in_path
from capsul.engine.module import fsl as fsl_engine


def fsl_command_with_environment(study_config, command):
    '''
    Given an FSL command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the study_config FSL configuration.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir:
        dir_prefix = '%s/bin/' % fsl_dir
    else:
        dir_prefix = ''
    fsl_prefix = getattr(study_config, 'fsl_prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if getattr(study_config, 'fsl_config', Undefined) is Undefined:
        cmd = ['%s%s%s' % (dir_prefix, 
                           fsl_prefix, 
                           command[0])] + command[1:]
    else:
        fsldir = osp.dirname(osp.dirname(osp.dirname(study_config.fsl_config)))
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c', 
                'setenv FSLDIR "{0}";source {0}/etc/fslconf/fsl.csh;exec {0}/bin/{1}{2} '.format(fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c', 
                'export FSLDIR="{0}";. {0}/etc/fslconf/fsl.sh;exec {0}/bin/{1}{2} '.format(fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
    return cmd

def check_fsl_configuration(study_config):
    '''
    Check thas study_config configuration is valid to call FSL commands.
    If not, try to automatically configure FSL. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''

    if getattr(study_config, '_fsl_config_checked', False):
        # Check FLS configuration only once
        return
    if 'FSLConfig' not in study_config.modules:
        raise EnvironmentError('FSLConfig module is missing in StudyConfig.')
    if study_config.use_fsl is False:
        raise EnvironmentError('Configuration is set not to use FLS. Set use_fsl to True in order to use FSL.')
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(study_config) is not None:
        auto_configuration(study_config)
        error_message = check_configuration_values(study_config)
        if error_message:
            raise EnvironmentError(error_message)
    study_config.use_fsl = True
    study_config._fsl_config_checked = True
    
def check_configuration_values(study_config):
    '''
    Check if the configuration is valid to run FLS and returns an error
    message if there is an error or None if everything is good.
    '''

    fsl_prefix = getattr(study_config, 'fsl_prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if study_config.fsl_config is Undefined:
        if not find_in_path('%sbet' % fsl_prefix):
            return 'FSL command "%sbet" cannot be found in PATH' % fsl_prefix
    else:
        if fsl_prefix:
            return 'FSL configuration must either use fsl_config or fsl_prefix but not both'
        if not osp.exists(study_config.fsl_config):
            return 'File "%s" does not exists' % study_config.fsl_config
        if not study_config.fsl_config.endswith('fsl.sh'):
            return 'File "%s" is not a path to fsl.sh script' % study_config.fsl_config
    return None

def auto_configuration(study_config):
    '''
    Try to automatically set the study_config configuration for FSL.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    fsl_prefix = getattr(study_config, 'fsl_prefix', '')
    if fsl_prefix is Undefined:
        fsl_prefix = ''
    if fsl_dir and not fsl_prefix:
        # Try to set fsl_config from FSLDIR environment variable
        fsl_config = '%s/etc/fslconf/fsl.sh' % fsl_dir
        if osp.exists(fsl_config):
            study_config.fsl_config = fsl_config
    elif not fsl_prefix:
        # Try to set fsl_prefix by searching fsl-*bet in PATH
        bet = find_in_path('fsl*-bet')
        if bet:
            study_config.fsl_prefix = osp.basename(bet)[:-3]

class Popen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for FSL commands
    '''
    def __init__(self, study_config, command, **kwargs):
        check_fsl_configuration(study_config)
        cmd = fsl_command_with_environment(study_config, command)
        super(Popen, self).__init__(cmd, **kwargs)
        
def call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.call for FSL commands
    '''
    check_fsl_configuration(study_config)
    cmd = fsl_command_with_environment(study_config, command)
    return soma.subprocess.call(cmd, **kwargs)

def check_call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for FSL commands
    '''
    check_fsl_configuration(study_config)
    cmd = fsl_command_with_environment(study_config, command)
    return soma.subprocess.check_call(cmd, **kwargs)


def check_output(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for FSL commands
    '''
    check_fsl_configuration(study_config)
    cmd = fsl_command_with_environment(study_config, command)
    return soma.subprocess.check_output(cmd, **kwargs)
