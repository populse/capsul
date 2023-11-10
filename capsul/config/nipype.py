from .configuration import ModuleConfiguration
import os
import os.path as osp
import tempfile


class NipypeConfiguration(ModuleConfiguration):
    ''' Nipype configuration module
    '''
    name = 'nipype'

    def is_valid_config(self, requirements):
        return True

    @staticmethod
    def init_execution_context(execution_context):
        '''
        Configure an execution context given a capsul_engine and some
        requirements.
        '''
        NipypeConfiguration.configure_matlab(execution_context)
        NipypeConfiguration.configure_spm(execution_context)
        NipypeConfiguration.configure_fsl(execution_context)
        NipypeConfiguration.configure_freesurfer(execution_context)
        NipypeConfiguration.configure_afni(execution_context)
        NipypeConfiguration.configure_ants(execution_context)

    @staticmethod
    def configure_spm(context):
        '''
        Configure Nipype SPM interface if CapsulEngine had been used to set
        the appropriate configuration variables in os.environ.
        '''
        conf = getattr(context, 'spm', None)
        if conf is None:
            return

        spm_directory = None
        standalone = None
        if conf:
            spm_directory = getattr(conf, 'directory', None)
            standalone = getattr(conf, 'standalone', None)

        if not spm_directory:
            spm_directory = os.environ.get('SPM_HOME')
        if standalone is None:
            standalone = (os.environ.get('SPM_STANDALONE') == 'yes')
        if spm_directory:
            from nipype.interfaces import spm

            spm_version = getattr(conf, 'version', None)
            if standalone:
                mlab_conf = getattr(context, 'matlab', None)
                mcr_directory = None
                if mlab_conf and getattr(mlab_conf, 'mcr_directory', None):
                    mcr_directory = mlab_conf.mcr_directory

                if not mcr_directory:
                    import glob
                    spm_exec_glob = osp.join(spm_directory, 'mcr', 'v*')
                    spm_exec = glob.glob(spm_exec_glob)
                    if spm_exec:
                        mcr_directory = spm_exec[0]
                if mcr_directory:
                    # set_mlab_paths() writes a file "pyscript.m" in the
                    # current directory.
                    # This is bad but we cannot do anything about it. So let's
                    # run it from a temp directory.
                    cwd = os.getcwd()
                    with tempfile.TemporaryDirectory() as tmpdir:
                        os.chdir(tmpdir)
                        spm.SPMCommand.set_mlab_paths(
                            matlab_cmd=osp.join(
                                spm_directory,
                                'run_spm%s.sh' % spm_version) + ' '
                                    + mcr_directory + ' script',
                            use_mcr=True)
                        os.chdir(cwd)

            else:
                # Matlab spm version

                from nipype.interfaces import matlab

                # set_mlab_paths() writes a file "pyscript.m" in the current
                # directory.
                # This is bad but we cannot do anything about it. So let's run
                # it from a temp directory.
                cwd = os.getcwd()
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    matlab.MatlabCommand.set_default_paths(
                        [spm_directory])  # + add_to_default_matlab_path)
                    mlab_conf = getattr(context, 'matlab', None)
                    matlab_cmd = ''
                    if mlab_conf and getattr(mlab_conf, 'executable', None):
                        matlab_cmd = mlab_conf.executable
                    spm.SPMCommand.set_mlab_paths(matlab_cmd=matlab_cmd,
                                                  use_mcr=False)
                    os.chdir(cwd)

    @staticmethod
    def configure_matlab(context):
        '''
        Configure matlab for nipype
        '''
        conf = getattr(context, 'matlab', None)
        if not conf:
            return
        if getattr(conf, 'executable', None):
            matlab_exe = conf.executable

            from nipype.interfaces import matlab

            matlab.MatlabCommand.set_default_matlab_cmd(
                matlab_exe + " -nodesktop -nosplash")
        #elif conf.get('mcr_directory'):
            #mcr_directory = cong['mcr_directory']

            #from nipype.interfaces import matlab

            #matlab.MatlabCommand.set_default_matlab_cmd(
                #mcr_directory)

    @staticmethod
    def configure_fsl(context):
        '''
        Configure FSL for nipype
        '''
        conf = getattr(context, 'fsl', None)
        if conf:
            from capsul.in_context import fsl as fslrun
            env = fslrun.fsl_env()
            for var, value in env.items():
                os.environ[var] = value

    @staticmethod
    def configure_freesurfer(context):
        '''
        Configure Freesurfer for nipype
        '''
        conf = getattr(context, 'freesurfer', None)
        if conf:
            subjects_dir = getattr(conf, 'subjects_dir', None)
            if subjects_dir:
                from nipype.interfaces import freesurfer
                freesurfer.FSCommand.set_default_subjects_dir(subjects_dir)
            from capsul.in_context import freesurfer as fsrun
            env = fsrun.freesurfer_env()
            for var, value in env.items():
                os.environ[var] = value

    @staticmethod
    def configure_afni(context):
        '''
        Configure AFNI for nipype
        '''
        conf = getattr(context, 'afni', None)
        if conf:
            from capsul.in_context import afni as afnirun
            env = afnirun.afni_env()
            for var, value in env.items():
                os.environ[var] = value

    @staticmethod
    def configure_ants(context):
        '''
        Configure ANTS for nipype
        '''
        conf = getattr(context, 'ants', None)
        if conf:
            from capsul.in_context import ants as antsrun
            env = antsrun.ants_env()
            for var, value in env.items():
                os.environ[var] = value
