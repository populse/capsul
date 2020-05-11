# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call Freesurfer taking into account
configuration stored in the activated configuration.
'''

from __future__ import absolute_import

import os
import soma.subprocess

from capsul import engine
import pipes


def freesurfer_command_with_environment(command):
    '''
    Given a Freesurfer command where first element is a command name without
    any path or prefix (e.g. "recon-all"). Returns the appropriate command to
    call taking into account the Freesurfer configuration stored in the
    activated configuration.
    '''
    config = engine.configurations.get('capsul.engine.module.freesurfer', {})
    fs_setup = config.get('setup')
    if not fs_setup:
        return command

    fs_dir = os.path.dirname(fs_setup)

    cmd = ['bash', '-c']
    args = ['export FREESURFER_HOME=%s' % fs_dir, '. %s' % fs_setup]

    return cmd + ['; '.join(args) + '; '
                  + ' '.join([pipes.quote(x) for x in command])]

class FreesurferPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for FSL commands
    '''
    def __init__(self, command, **kwargs):
        cmd = freesurfer_command_with_environment(command)
        super(FreesurferPopen, self).__init__(cmd, **kwargs)

def freesurfer_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for FSL commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)

def freesurfer_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for FSL commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.check_call(cmd, **kwargs)


def freesurfer_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for FSL commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)

