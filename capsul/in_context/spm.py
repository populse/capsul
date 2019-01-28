'''
Specific subprocess-like functions to call SPM taking into account 
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance:

   from capsul.engine import engine
   from capsul.in_context.fsl import fsl_call
   
   capsul_engine = engine()
   with capsul_engine.execution_context:
     spm_check_call(spm_batch_filename)

For calling SPM command with this module, the first arguent of
command line must be the SPM batch file to execute with Matlab.
'''

from __future__ import absolute_import, print_function

import glob
import os
import os.path as osp

import soma.subprocess


def spm_command(spm_batch_filename):
    if os.environ.get('SPM_STANDALONE') == 'True':
        # Check that batch file exists and raise appropriate error if not
        open(spm_batch_filename)
        spm_directory = os.environ.get('SPM_DIRECTORY', '')
        spm_exec_glob = osp.join(spm_directory, 'mcr', 'v*')
        spm_exec = glob.glob(spm_exec_glob)
        if not spm_exec:
            raise ValueError('Cannot find SPM executable: %s' % spm_exec_glob)
        spm_exec = spm_exec[0]
        print('---- BATCH SMP ----')
        print(open(spm_batch_filename).read())
        print('-------------------')
        cmd = [osp.join(spm_directory, 
                        'run_spm%s.sh' % os.environ.get('SPM_VERSION', '')),
               spm_exec,
               'batch',
               spm_batch_filename]
    else:
        raise NotImplementedError('Running SPM with matlab is not '
                                  'implemented yet')
    return cmd

class SPMPopen(soma.subprocess.Popen):
    '''
    Equivalent to Python subprocess.Popen for SPM batch
    '''
    def __init__(self, spm_batch_filename, **kwargs):
        cmd = spm_command(spm_batch_filename)
        super(Popen, self).__init__(cmd, **kwargs)
        
def spm_call(spm_batch_filename, **kwargs):
    '''
    Equivalent to Python subprocess.call for SPM batch
    '''
    cmd = spm_command(spm_batch_filename)
    return soma.subprocess.call(cmd, **kwargs)

def spm_check_call(spm_batch_filename, **kwargs):
    '''
    Equivalent to Python subprocess.check_call for SPM batch
    '''
    cmd = spm_command(spm_batch_filename)
    return soma.subprocess.check_call(cmd, **kwargs)


def spm_check_output(spm_batch_filename, **kwargs):
    '''
    Equivalent to Python subprocess.check_output for SPM batch
    '''
    cmd = spm_command(spm_batch_filename)
    return soma.subprocess.check_output(cmd, **kwargs)


if __name__ == '__main__':
    from capsul.api import capsul_engine
    from capsul.in_context.spm import spm_call
    import tempfile
    
    ce = capsul_engine(config={
        'spm': dict(directory='/casa/spm_directory',
                    use=True)})
    with ce.execution_context:
        batch = tempfile.NamedTemporaryFile(suffix='.m')
        batch.write("fprintf(1, '%s', spm('dir'));")
        batch.flush()
        spm_call(batch.name)
