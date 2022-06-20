# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os
import os.path as osp

def configure_all():
    '''
    Configure nipye for all known software interfaces their configuration
    is present in os.environ. This environment must have been set by the
    CapsulEngine mechanism.
    '''
    #print('!!!')
    configure_matlab()
    configure_spm()
    configure_fsl()
    configure_freesurfer()
    configure_afni()
    configure_ants()


def configure_spm():
    '''
    Configure Nipype SPM interface if CapsulEngine had been used to set
    the appropriate configuration variables in os.environ.
    '''
    spm_directory = os.environ.get('SPM_DIRECTORY')
    if not spm_directory:
        spm_directory = os.environ.get('SPM_HOME')
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

    conf = engine.configurations.get('capsul.engine.module.matlab')
    if conf and conf.get('executable'):
        matlab_exe = conf['executable']

        from nipype.interfaces import matlab

        matlab.MatlabCommand.set_default_matlab_cmd(
            matlab_exe + " -nodesktop -nosplash")


def configure_fsl():
    '''
    Configure FSL for nipype
    '''
    from capsul import engine
    conf = engine.configurations.get('capsul.engine.module.fsl')
    if conf:
        from capsul.in_context import fsl as fslrun
        env = fslrun.fsl_env()
        for var, value in env.items():
            os.environ[var] = value


def configure_freesurfer():
    '''
    Configure Freesurfer for nipype
    '''
    from capsul import engine
    conf = engine.configurations.get('capsul.engine.module.freesurfer')
    if conf:
        subjects_dir = conf.get('subjects_dir')
        if subjects_dir:
            from nipype.interfaces import freesurfer
            freesurfer.FSCommand.set_default_subjects_dir(subjects_dir)
        from capsul.in_context import freesurfer as fsrun
        env = fsrun.freesurfer_env()
        for var, value in env.items():
            os.environ[var] = value


def configure_afni():
    '''
    Configure AFNI for nipype
    '''
    from capsul import engine
    conf = engine.configurations.get('capsul.engine.module.afni')
    if conf:
        from capsul.in_context import afni as afnirun
        env = afnirun.afni_env()
        for var, value in env.items():
            os.environ[var] = value

def configure_ants():
    '''
    Configure ANTS for nipype
    '''
    from capsul import engine
    conf = engine.configurations.get('capsul.engine.module.ants')
    if conf:
        from capsul.in_context import ants as antsrun
        env = antsrun.ants_env()
        for var, value in env.items():
            os.environ[var] = value
