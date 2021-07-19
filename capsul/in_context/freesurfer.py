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
import six

'''
If this variable is set, it contains FS runtime env variables, allowing to run directly freesurfer commands from this process.
'''
freesurfer_runtime_env = None


def freesurfer_command_with_environment(command):
    '''
    Given a Freesurfer command where first element is a command name without
    any path or prefix (e.g. "recon-all"). Returns the appropriate command to
    call taking into account the Freesurfer configuration stored in the
    activated configuration.

    Usinfg :func`freesurfer_env` is an alternative to this.
    '''
    config = engine.configurations.get('capsul.engine.module.freesurfer', {})
    fs_setup = config.get('setup')
    if not fs_setup:
        return command

    fs_dir = os.path.dirname(fs_setup)

    cmd = ['bash', '-c']
    args = ['export FREESURFER_HOME=%s' % fs_dir]
    subjects_dir = config.get('subjects_dir')
    if subjects_dir:
        args.append('export SUBJECTS_DIR=%s' % subjects_dir)
    args.append('. %s' % fs_setup)

    return cmd + ['; '.join(args) + '; '
                  + ' '.join([pipes.quote(x) for x in command])]


def freesurfer_env():
    '''
    get Freesurfer env variables by running the setup script in a separate bash
    process
    '''
    global freesurfer_runtime_env

    if freesurfer_runtime_env is not None:
        return freesurfer_runtime_env

    cmd = freesurfer_command_with_environment(['env'])
    new_env = soma.subprocess.check_output(cmd).decode(
        'utf-8').strip().split('\n')
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
        #cmd = freesurfer_command_with_environment(command)
        env = freesurfer_env()
        if 'env' in kwargs:
            env = dict(env)
            env.update(kwargs['env'])
            kwargs = dict(kwargs)
            del kwargs['env']
        super(FreesurferPopen, self).__init__(command, env=env, **kwargs)

def freesurfer_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for Freesurfer commands
    '''
    #cmd = freesurfer_command_with_environment(command)
    env = freesurfer_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.call(command, env=env, **kwargs)

def freesurfer_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for Freesurfer commands
    '''
    #cmd = freesurfer_command_with_environment(command)
    env = freesurfer_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.check_call(command, env=env, **kwargs)


def freesurfer_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for Freesurfer commands
    '''
    cmd = freesurfer_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)
