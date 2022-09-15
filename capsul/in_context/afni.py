# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call AFNI taking into account
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance::

   from capsul.engine import capsul_engine
   from capsul.in_context.afni import afni_check_call

   ce = capsul_engine()
   with ce:
       afni_check_call(['bet', '/somewhere/myimage.nii'])

For calling AFNI command with this module, the first argument of
command line must be the AFNI executable without any path.
The appropriate path is added from the configuration
of the ExecutionContext.
'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess
from soma.utils.env import parse_env_lines
import six

afni_runtime_env = None

def afni_command_with_environment(command, use_runtime_env=True):
    '''
    Given an AFNI command where first element is a command name without
    any path. Returns the appropriate command to call taking into account
    the AFNI configuration stored in the
    activated ExecutionContext.
    '''

    if use_runtime_env and afni_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

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

def afni_env():
    '''
    get AFNI env variables
    process
    '''
    global afni_runtime_env

    if afni_runtime_env is not None:
        return afni_runtime_env

    afni_dir = os.environ.get('AFNIPATH')
    kwargs = {}

    cmd = afni_command_with_environment(['env'], use_runtime_env=False)
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

    # add PATH
    if afni_dir:
        env['PATH'] = os.pathsep.join([afni_dir, os.environ.get('PATH', '')])
    # cache dict
    afni_runtime_env = env
    return env


class AFNIPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for AFNI commands
    '''
    def __init__(self, command, **kwargs):
        cmd = afni_command_with_environment(command)
        super(AFNIPopen, self).__init__(cmd, **kwargs)


def afni_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for AFNI commands
    '''
    cmd = afni_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)


def afni_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for AFNI commands
    '''
    cmd = afni_command_with_environment(command)
    return soma.subprocess.check_call(cmd, **kwargs)


def afni_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for AFNI commands
    '''
    cmd = afni_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)
