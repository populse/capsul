# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call ANTS taking into account
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance::

   from capsul.engine import capsul_engine
   from capsul.in_context.ants import ants_check_call

   ce = capsul_engine()
   with ce:
       ants_check_call(['bet', '/somewhere/myimage.nii'])

For calling ANTS command with this module, the first argument of
command line must be the ANTS executable without any path.
The appropriate path is added from the configuration
of the ExecutionContext.
'''

from __future__ import absolute_import

import os
import os.path as osp
import soma.subprocess
import six

ants_runtime_env = None

def ants_command_with_environment(command, use_runtime_env=True):
    '''
    Given an ANTS command where first element is a command name without
    any path. Returns the appropriate command to call taking into account
    the ANTS configuration stored in the
    activated ExecutionContext.
    '''

    if use_runtime_env and ants_runtime_env:
        c0 = list(osp.split(command[0]))
        c0 = osp.join(*c0)
        cmd = [c0] + command[1:]
        return cmd

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
                if char in rev_char:
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



def ants_env():
    '''
    get ANTS env variables
    process
    '''
    global ants_runtime_env

    if ants_runtime_env is not None:
        return ants_runtime_env

    ants_dir = os.environ.get('ANTSPATH')
    kwargs = {}

    cmd = ants_command_with_environment(['env'], use_runtime_env=False)
    #new_env = soma.subprocess.check_output(cmd, **kwargs).decode(
    #    'utf-8').strip().split('\n')
#########
    new_env = soma.subprocess.check_output(cmd, **kwargs).decode(
         'utf-8').strip()
    new_env = parse_env_lines(new_env)
#############
    env = {}
    for l in new_env:
        name, val = l.strip().split('=', 1)
        name = six.ensure_str(name)
        val = six.ensure_str(val)
        if name not in ('_', 'SHLVL') and (name not in os.environ
                                           or os.environ[name] != val):
            env[name] = val

    # add PATH
    if ants_dir:
        env['PATH'] = os.pathsep.join([ants_dir, os.environ.get('PATH', '')])
    # cache dict
    ants_runtime_env = env
    return env


class ANTSPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for ANTS commands
    '''
    def __init__(self, command, **kwargs):
        cmd = ants_command_with_environment(command)
        super(ANTSPopen, self).__init__(cmd, **kwargs)


def ants_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for ANTS commands
    '''
    cmd = ants_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)


def ants_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for ANTS commands
    '''
    cmd = ants_command_with_environment(command)
    return soma.subprocess.check_call(cmd, **kwargs)


def ants_check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for ANTS commands
    '''
    cmd = ants_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)
