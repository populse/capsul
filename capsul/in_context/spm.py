# -*- coding: utf-8 -*-
'''
Specific subprocess-like functions to call SPM taking into account 
configuration stored in ExecutionContext. To functions and class in
this module it is mandatory to activate an ExecutionContext (using a
with statement). For instance::

   from capsul.engine import capsul_engine
   from capsul.in_context.spm import spm_check_call
   
   ce = capsul_engine()
   with ce:
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
    if os.environ.get('SPM_STANDALONE') == 'yes':
        # Check that batch file exists and raise appropriate error if not
        open(spm_batch_filename)
        spm_directory = os.environ.get('SPM_DIRECTORY', '')
        mcr_dir = os.environ.get('MCR_HOME')
        if mcr_dir is None:
            mcr_glob = osp.join(spm_directory, 'mcr', 'v*')
            mcr_dir = glob.glob(mcr_glob)
            if not mcr_dir:
                raise ValueError('Cannot find Matlab MCR dir: %s' % mcr_glob)
            mcr_dir = mcr_dir[0]
        print('---- BATCH SMP ----')
        print(open(spm_batch_filename).read())
        print('-------------------')
        cmd = [osp.join(spm_directory, 
                        'run_spm%s.sh' % os.environ.get('SPM_VERSION', '')),
               mcr_dir,
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
        super(SPMPopen, self).__init__(cmd, **kwargs)
        
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
    import tempfile
    
    ce = capsul_engine()
    ce.global_config.spm.directory = '/casa/spm12_standalone'
    with ce:
        batch = tempfile.NamedTemporaryFile(suffix='.m')
        batch.write("fprintf(1, '%s', spm('dir'));")
        batch.flush()
        spm_call(batch.name)
