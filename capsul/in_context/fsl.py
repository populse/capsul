# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call FSL taking into account 
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance::

   from capsul.engine import capsul_engine
   from capsul.in_context.fsl import fsl_check_call

   ce = capsul_engine()
   with ce:
       fsl_check_call(['bet', '/somewhere/myimage.nii'])

For calling FSL command with this module, the first arguent of
command line must be the FSL executable without any path nor prefix. 
Prefix are used in Neurodebian install. For instance on Ubuntu 16.04 
Neurodebian FSL commands are prefixed with "fsl5.0-".
The appropriate path and eventualy prefix are added from the configuration
of the ExecutionContext.
'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess

from traits.api import Undefined

from soma.path import find_in_path


'''
If this variable is set, it contains FS runtime env variables, allowing to run directly freesurfer commands from this process.
'''
fsl_runtime_env = None


def fsl_command_with_environment(command):
    '''
    Given an FSL command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the FSL configuration stored in the
    activated ExecutionContext.

    Usinfg :func`fsl_env` is an alternative to this.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir:
        dir_prefix = '%s/bin/' % fsl_dir
    else:
        dir_prefix = ''
    fsl_prefix = os.environ.get('FSL_PREFIX', '')
    fsl_config = os.environ.get('FSL_CONFIG')
    if fsl_prefix and not os.path.isdir(dir_prefix):
        dir_prefix = ''

    if fsl_config:
        fsldir = osp.dirname(osp.dirname(osp.dirname(fsl_config)))
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c', 
                'setenv FSLDIR "{0}";source {0}/etc/fslconf/fsl.csh;exec {0}/bin/{1}{2} '.format(fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c', 
                'export FSLDIR="{0}";. {0}/etc/fslconf/fsl.sh;exec {0}/bin/{1}{2} '.format(fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
    else:
        cmd = ['%s%s%s' % (dir_prefix, 
                           fsl_prefix, 
                           command[0])] + command[1:]
    return cmd


def fsl_env():
    '''
    get FSL env variables by running the setup script in a separate bash
    process
    '''
    global fsl_runtime_env

    if fsl_runtime_env is not None:
        return fsl_runtime_env

    cmd = fsl_command_with_environment(['env'])
    new_env = soma.subprocess.check_output(cmd).decode(
        'utf-8').strip().split('\n')
    env = {}
    for l in new_env:
        name, val = l.strip().split('=', 1)
        if name not in ('_', 'SHLVL') and (name not in os.environ
                                           or os.environ[name] != val):
            env[name] = val
    # add PATH
    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir:
        fsl_bin = osp.join(fsl_dir, 'bin')
        env['PATH'] = os.pathsep.join([fsl_bin, os.environ.get('PATH', '')])
    # cache dict
    fsl_runtime_env = env
    return env


class FslPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for FSL commands
    '''
    def __init__(self, command, **kwargs):
        # cmd = fsl_command_with_environment(command)
        env = fsl_env()
        if 'env' in kwargs:
            env = dict(env)
            env.update(kwargs['env'])
            kwargs = dict(kwargs)
            del kwargs['env']
        super(FslPopen, self).__init__(command, env=env, **kwargs)

def fsl_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for FSL commands
    '''
    #cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.call(command, env=env, **kwargs)

def fsl_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for FSL commands
    '''
    #cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.check_call(command, env=env, **kwargs)


def fsl_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for FSL commands
    '''
    #cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.check_output(command, env=env, **kwargs)
