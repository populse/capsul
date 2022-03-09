# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call AFNI taking into account a
potential configuration done in StudyConfig. If a StudyConfig is not
configured to use AFNI, it may be automatically configured.

For calling AFNI command with this module, the first argument of
command line must be the AFNI executable.
The appropriate path is added from the configuration
of the StudyConfig instance.

Classes
=======
:class:`Popen`
--------------

Functions
=========
:func:`afni_command_with_environment`
------------------------------------
:func:`check_afni_configuration`
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


def afni_command_with_environment(study_config, command):
    '''
    Given an AFNI command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the study_config AFNI configuration.
    '''
    afni_dir = os.environ.get('AFNIPATH')
    if afni_dir:
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c',
                   'setenv AFNIPATH "{0}"; setenv PATH "{0}:$PATH";exec {1} '.format(
                       afni_dir, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c',
                   'export AFNIPATH="{0}"; export PATH="{0}:$PATH"; exec {1} '.format(
                       afni_dir, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]

    return cmd


def check_afni_configuration(study_config):
    '''
    Check thas study_config configuration is valid to call AFNI commands.
    If not, try to automatically configure AFNI. Finally raises an
    EnvironmentError if configuration is still wrong.
    '''

    if getattr(study_config, '_afni_config_checked', False):
        # Check FLS configuration only once
        return
    if 'AFNIConfig' not in study_config.modules:
        raise EnvironmentError('AFNIConfig module is missing in StudyConfig.')
    if study_config.use_afni is False:
        raise EnvironmentError('Configuration is set not to use AFNI. Set use_afni to True in order to use AFNI.')
    # Configuration must be valid otherwise
    # try to update configuration and recheck is validity
    if check_configuration_values(study_config) is not None:
        error_message = check_configuration_values(study_config)
        if error_message:
            raise EnvironmentError(error_message)
    study_config.use_afni = True
    study_config._afni_config_checked = True


def check_configuration_values(study_config):
    '''
    Check if the configuration is valid to run AFNI and returns an error
    message if there is an error or None if everything is good.
    '''

    if not find_in_path('afni'):
        return 'AFNI command "afni" cannot be found in PATH'
    else:
        return None



class Popen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for AFNI commands
    '''

    def __init__(self, study_config, command, **kwargs):
        check_afni_configuration(study_config)
        cmd = afni_command_with_environment(study_config, command)
        super(Popen, self).__init__(cmd, **kwargs)


def call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.call for AFNI commands
    '''
    check_afni_configuration(study_config)
    cmd = afni_command_with_environment(study_config, command)
    return soma.subprocess.call(cmd, **kwargs)


def check_call(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for AFNI commands
    '''
    check_afni_configuration(study_config)
    cmd = afni_command_with_environment(study_config, command)
    return soma.subprocess.check_call(cmd, **kwargs)


def check_output(study_config, command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for AFNI commands
    '''
    check_afni_configuration(study_config)
    cmd = afni_command_with_environment(study_config, command)
    return soma.subprocess.check_output(cmd, **kwargs)
