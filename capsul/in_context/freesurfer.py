# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call Freesurfer taking into account
configuration stored in the activated configuration.
'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess
from soma.utils.env import parse_env_lines
from capsul import engine
import pipes
import six

'''
If this variable is set, it contains FS runtime env variables,
allowing to run directly freesurfer commands from this process.
'''
freesurfer_runtime_env = None


def freesurfer_command_with_environment(command, use_runtime_env=True):
    '''
    Given a Freesurfer command where first element is a command name without
    any path or prefix (e.g. "recon-all"). Returns the appropriate command to
    call taking into account the Freesurfer configuration stored in the
    activated configuration.

    Using :func`freesurfer_env` is an alternative to this.
    '''

    if use_runtime_env and freesurfer_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    fconf = engine.configurations.get('capsul.engine.module.freesurfer')

    if fconf:
        freesurfer_script = fconf.get('setup')

        if freesurfer_script is not None and os.path.isfile(freesurfer_script):
            freesurfer_dir = os.path.dirname(freesurfer_script)

        else:
            freesurfer_dir = None

    else:
        freesurfer_dir = os.environ.get('FREESURFER_HOME')

        if freesurfer_dir is not None:
            freesurfer_script = os.path.join(freesurfer_dir,
                                             'SetUpFreeSurfer.sh')

            if not os.path.isfile(freesurfer_script):
                freesurfer_script = None

        else:
            freesurfer_script = None

    if freesurfer_dir is not None and freesurfer_script is not None:
        shell = os.environ.get('SHELL', '/bin/sh')

        if shell.endswith('csh'):
            cmd = [shell, '-c',
                   'setenv FREESURFER_HOME "{0}"; source {1}; exec {2} '.format(
                       freesurfer_dir, freesurfer_script, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]

        else:
            cmd = [shell, '-c',
                   'export FREESURFER_HOME="{0}"; source {1}; exec {2} '.format(
                       freesurfer_dir, freesurfer_script, command[0]) + \
                   ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]

    return cmd


def freesurfer_env():
    '''
    get Freesurfer env variables by running the setup script in a separate bash
    process
    '''
    global freesurfer_runtime_env

    if freesurfer_runtime_env is not None:
        return freesurfer_runtime_env

    kwargs = {}
    cmd = freesurfer_command_with_environment(['env'], use_runtime_env=False)
    new_env = soma.subprocess.check_output(cmd, **kwargs).decode(
        'utf-8').strip()
    new_env = parse_env_lines(new_env)
    env = {}

    for l in new_env:
        name, val = l.strip().split('=', 1)
        name = six.ensure_str(name)
        val = six.ensure_str(val)

        if name not in ('_', 'SHLVL') and (name not in os.environ
                                           or os.environ[name] != val):
            env[name] = val

    # cache dict
    freesurfer_runtime_env = env
    return env


class FreesurferPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for Freesurfer commands
    '''
    def __init__(self, command, **kwargs):
        cmd = freesurfer_command_with_environment(command)
        super(FreesurferPopen, self).__init__(cmd, **kwargs)


def freesurfer_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for Freesurfer commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)


def freesurfer_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for Freesurfer commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)


def freesurfer_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for Freesurfer commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)
