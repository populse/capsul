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
The appropriate path and eventually prefix are added from the configuration
of the ExecutionContext.
'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess
import six

from traits.api import Undefined
from soma.path import find_in_path


'''
If this variable is set, it contains FS runtime env variables, allowing to run directly freesurfer commands from this process.
'''
fsl_runtime_env = None


def fsl_command_with_environment(command, use_prefix=True,
                                 use_runtime_env=True):
    '''
    Given an FSL command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the FSL configuration stored in the
    activated ExecutionContext.

    Usinfg :func`fsl_env` is an alternative to this.
    '''
    if use_prefix:
        fsl_prefix = os.environ.get('FSL_PREFIX', '')
    else:
        fsl_prefix = ''
    if use_runtime_env and fsl_runtime_env:
        c0 = list(osp.split(command[0]))
        c0[-1] = '%s%s' % (fsl_prefix, c0[-1])
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir:
        dir_prefix = '%s/bin/' % fsl_dir
    else:
        dir_prefix = ''
    fsl_config = os.environ.get('FSL_CONFIG')
    if fsl_prefix and not os.path.isdir(dir_prefix):
        dir_prefix = ''

    if fsl_config:
        fsldir = osp.dirname(osp.dirname(osp.dirname(fsl_config)))
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c', 
                'setenv FSLDIR "{0}"; setenv PATH "{0}/bin:$PATH"; source {0}/etc/fslconf/fsl.csh;exec {1}{2} '.format(
                    fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c', 
                'export FSLDIR="{0}"; export PATH="{0}/bin:$PATH"; . {0}/etc/fslconf/fsl.sh;exec {1}{2} '.format(
                    fsldir, fsl_prefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
    else:
        cmd = ['%s%s%s' % (dir_prefix,
                           fsl_prefix, 
                           command[0])] + command[1:]
    return cmd


def parse_env_lines(text):
    ''' Separate text into multi-line elements, avoiding separations inside ()
    or {} blocks
    '''
    def push(obj, l, depth, tags, start_tag=None):
        while depth:
            l = l[-1]
            tags = tags[-1]
            depth -= 1

        if start_tag:
            tags.append([start_tag, []])
        if isinstance(obj, str):
            if len(l) == 0 or isinstance(l[-1], list):
                l.append(obj)
            else:
                l[-1] += obj
        else:
            l.append(obj)

    def current_tag(tags, depth):
        while depth:
            tags = tags[-1]
            depth -= 1
        return tags[0]

    def parse_parentheses(s):
        rev_char = {'(': ')', '{': '}',
                    #'[': ']',
                    '"': '"', "'": "'"}
        groups = []
        tags = [None, []]
        depth = 0
        escape = None

        try:
            for char in s:
                if s == '\\':
                    escape = not escape
                    if escape:
                       push(char, groups, depth, tags)
                #if char in rev_char:

                if char in rev_char and char != current_tag(tags, depth):
                    start_char = char
                    push([char], groups, depth, tags, char)
                    depth += 1
                elif char == rev_char.get(current_tag(tags, depth)):
                    push(char, groups, depth, tags)
                    depth -= 1
                else:
                    push(char, groups, depth, tags)
        except IndexError:
            raise ValueError('Parentheses mismatch', depth, groups)

        if depth > 0:
            raise ValueError('Parentheses mismatch 2', depth, groups)
        else:
            return groups

    def rebuild_lines(parsed, breaks=True):
        lines = []
        for item in parsed:
            if isinstance(item, str):
                if breaks:
                    newlines = item.split('\n')
                else:
                    newlines = [item]
            else:
                newlines = rebuild_lines(item, breaks=False)
            if lines:
                lines[-1] += newlines[0]
                lines += newlines[1:]
            else:
                lines = newlines
        return lines

    return rebuild_lines(parse_parentheses(text))


def fsl_env():
    '''
    get FSL env variables by running the setup script in a separate bash
    process
    '''
    global fsl_runtime_env

    if fsl_runtime_env is not None:
        return fsl_runtime_env

    fsl_config = os.environ.get('FSL_CONFIG')
    fsl_dir = os.environ.get('FSLDIR')
    kwargs = {}
    if not fsl_config:
        cmd = ['env']
        if fsl_dir:
            kwargs = {'env': {'PATH': os.pathsep.join(
                ['%s/bin' % fsl_dir, os.environ.get('PATH', '')])}}
    else:
        cmd = fsl_command_with_environment(['env'], use_prefix=False,
                                           use_runtime_env=False)
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
        cmd = fsl_command_with_environment(command)
        env = fsl_env()
        if 'env' in kwargs:
            env = dict(env)
            env.update(kwargs['env'])
            kwargs = dict(kwargs)
            del kwargs['env']
        super(FslPopen, self).__init__(cmd, env=env, **kwargs)

def fsl_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.call(cmd, env=env, **kwargs)

def fsl_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.check_call(cmd, env=env, **kwargs)


def fsl_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    env = fsl_env()
    if 'env' in kwargs:
        env = dict(env)
        env.update(kwargs['env'])
        kwargs = dict(kwargs)
        del kwargs['env']
    return soma.subprocess.check_output(cmd, env=env, **kwargs)
