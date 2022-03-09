# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call ANTS taking into account a
potential configuration done in StudyConfig. If a StudyConfig is not
configured to use ANTS, it may be automatically configured.

For calling ANTS command with this module, the first argument of
command line must be the ANTS executable.
The appropriate path is added from the configuration
of the StudyConfig instance.

Classes
=======
:class:`Popen`
--------------

Functions
=========
:func:`ants_command_with_environment`
------------------------------------
:func:`check_ants_configuration`
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
import soma.subprocess
from soma.path import find_in_path


def ants_command_with_environment(study_config, command):
    '''
    Given an ANTS command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the study_config ANTS configuration.
    '''
    ants_dir = os.environ.get('ANTSPATH')
    if ants_dir:
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c',
                   'setenv ANTSPATH "{0}"; setenv PATH "{0}:$PATH";exec {1} '.format(
                       ants_dir, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c',
                   'export ANTSPATH="{0}"; export PATH="{0}:$PATH"; exec {1} '.format(
                       ants_dir, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]

    return cmd


def check_ants_configuration(study_config):
    '''
    Check thas study_config configuration is valid to call ANTS commands.
    If not, try to automatically configure ANTS. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''

    if getattr(study_config, '_ants_config_checked', False):
        # Check FLS configuration only once
        return
    if 'ANTSConfig' not in study_config.modules:
        raise EnvironmentError('ANTSConfig module is missing in StudyConfig.')
    if study_config.use_ants is False:
        raise EnvironmentError('Configuration is set not to use ANTS. Set use_ants to True in order to use ANTS.')
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(study_config) is not None:
        error_message = check_configuration_values(study_config)
        if error_message:
            raise EnvironmentError(error_message)
    study_config.use_ants = True
    study_config._ants_config_checked = True


def check_configuration_values(study_config):
    '''
    Check if the configuration is valid to run ANTS and returns an error
    message if there is an error or None if everything is good.
    '''

    if not find_in_path('ANTS'):
        return 'ANTS command "ANTS" cannot be found in PATH'
    else:
        return None



class Popen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for ANTS commands
    '''

    def __init__(self, study_config, command, **kwargs):
        check_ants_configuration(study_config)
        cmd = ants_command_with_environment(study_config, command)
        super(Popen, self).__init__(cmd, **kwargs)


def call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.call for ANTS commands
    '''
    check_ants_configuration(study_config)
    cmd = ants_command_with_environment(study_config, command)
    return soma.subprocess.call(cmd, **kwargs)


def check_call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for ANTS commands
    '''
    check_ants_configuration(study_config)
    cmd = ants_command_with_environment(study_config, command)
    return soma.subprocess.check_call(cmd, **kwargs)


def check_output(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for ANTS commands
    '''
    check_ants_configuration(study_config)
    cmd = ants_command_with_environment(study_config, command)
    return soma.subprocess.check_output(cmd, **kwargs)
