from __future__ import absolute_import

import os
import os.path as osp
import subprocess

from traits.api import Undefined

def fsl_command_with_environment(study_config, command):
    fsl_dir = os.environ.get('FSLDIR')
    if fsl_dir or study_config.fsl_config is Undefined:
        if fsl_dir:
            dir_prefix = '%s/bin/' % fsl_dir
        else:
            di_prefix = ''
        cmd = ['%s%s%s' % (dir_prefix, study_config.fsl_prefix, command[0])] + command[1:]
    else:
        fsldir = osp.dirname(osp.dirname(study_config.fsl_config))
        fslprefix = study_config.fsl_prefix
        shell = os.environ.get('SHELL', '/bin/sh')
        if shell.endswith('csh'):
            cmd = [shell, '-c', 
                'setenv FSLDIR "{0}";source {0}/etc/fslconf/fsl.csh;exec {0}/bin/{1}{2} '.format(fsldir, fslprefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
        else:
            cmd = [shell, '-c', 
                'export FSLDIR="{0}";. {0}/etc/fslconf/fsl.sh;exec {0}/bin/{1}{2} '.format(fsldir, fslprefix, command[0]) + \
                    ' '.join("'%s'" % i.replace("'", "\\'") for i in command[1:])]
    return cmd

class Popen(subprocess.Popen):
    def __init__(self, study_config, command, **kwargs):
        cmd = fsl_command_with_environment(study_config, command)
        super(Popen, self).__init__(cmd, **kwargs)
        
def call(study_config, command, **kwargs):
    cmd = fsl_command_with_environment(study_config, command)
    return subprocess.call(cmd, **kwargs)

def check_call(study_config, command, **kwargs):
    cmd = fsl_command_with_environment(study_config, command)
    return subprocess.check_call(cmd, **kwargs)


def check_output(study_config, command, **kwargs):
    cmd = fsl_command_with_environment(study_config, command)
    return subprocess.check_output(cmd, **kwargs)
