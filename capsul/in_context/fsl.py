'''
Specific subprocess-like functions to call FSL taking into account 
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance:

   from capsul.engine import engine
   from capsul.in_context.fsl import fsl_call
   
   capsul_engine = engine()
   with capsul_engine.execution_context:
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


def fsl_command_with_environment(command):
    '''
    Given an FSL command where first element is a command name without
    any path or prefix (e.g. "bet"). Returns the appropriate command to
    call taking into account the FSL configuration stored in the
    activated ExecutionContext.
    '''
    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir:
        dir_prefix = '%s/bin/' % fsl_dir
    else:
        dir_prefix = ''
    fsl_prefix = os.environ.get('FSL_PREFIX', '')
    fsl_config = os.environ.get('FSL_CONFIG')
    
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

class FslPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for FSL commands
    '''
    def __init__(self, command, **kwargs):
        cmd = fsl_command_with_environment(command)
        super(Popen, self).__init__(cmd, **kwargs)
        
def fsl_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.call for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    return soma.subprocess.call(cmd, **kwargs)

def fsl_check_call(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    return soma.subprocess.check_call(cmd, **kwargs)


def check_output(command, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for FSL commands
    '''
    cmd = fsl_command_with_environment(command)
    return soma.subprocess.check_output(cmd, **kwargs)
