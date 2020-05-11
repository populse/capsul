# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os
import os.path as osp

def configure_all():
    '''
    Configure nipye for all known software interfaces their configuration
    is present in os.environ. This environment must have been set by the
    CapsulEngine mecanism.
    '''
    #print('!!!')
    configure_matlab()
    configure_spm()


def configure_spm():
    '''
    Configure Nipype SPM interface if CapsulEngine had been used to set
    the appropriate configuration variables in os.environ.
    '''
    spm_directory = os.environ.get('SPM_DIRECTORY')
    if spm_directory:
        from nipype.interfaces import spm
        
        standalone = (os.environ.get('SPM_STANDALONE') == 'yes')
        if standalone:
            import glob
            spm_exec_glob = osp.join(spm_directory, 'mcr', 'v*')
            spm_exec = glob.glob(spm_exec_glob)
            if spm_exec:
                spm_exec = spm_exec[0]
                spm.SPMCommand.set_mlab_paths(
                    matlab_cmd=osp.join(spm_directory, 'run_spm%s.sh' % os.environ.get('SPM_VERSION','')) + ' ' + spm_exec + ' script',
                    use_mcr=True)

        else:
            # Matlab spm version

            from nipype.interfaces import matlab

            matlab.MatlabCommand.set_default_paths(
                [spm_directory])  # + add_to_default_matlab_path)
            spm.SPMCommand.set_mlab_paths(matlab_cmd="", use_mcr=False)


def configure_matlab():
    '''
    Configure matlab for nipype
    '''

    from capsul import engine

    conf = engine.configurations.get('matlab')
    if conf and conf.get('executable'):
        matlab_exe = conf['executable']

        from nipype.interfaces import matlab

        matlab.MatlabCommand.set_default_matlab_cmd(
            matlab_exe + " -nodesktop -nosplash")

