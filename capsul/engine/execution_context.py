import os
import os.path as osp
import sys

from traits.api import DictStrStr, ListStr
from soma.controller import Controller
from soma.serialization import JSONSerializable

# Global execution context used when running processes
active_execution_context = None

class ExecutionContext(Controller):
    '''
    An execution context contains all the information necessary to start a 
    job. For instance, in order to use FSL, it is necessary to setup a few
    environment variables whose content depends on the location where FSL 
    is installed. The execution context contains the information about FSL 
    installation necessary to define these environment variable when a job 
    is started. The execution context is shared with every processing nodes 
    and used to build the execution environment of each job.
    '''
    
    python_path_first = ListStr()
    python_path_last = ListStr()
    environ = DictStrStr()
    
    #def __init__(self, python_path_first=[], python_path_last=[],
                 #environ = {}):
        #self.python_path_first = python_path_first
        #self.python_path_last = python_path_last
        #self.environ = environ
    
    def to_json(self):
        '''
        Returns a dictionary containing JSON compatible representation of
        the execution context.
        '''
        kwargs = {}
        if self.python_path_first:
            kwargs['python_path_first'] = self.python_path_first
        if self.python_path_last:
            kwargs['python_path_last'] = self.python_path_last
        if self.environ:
            kwargs['environ'] = self.environ
        return ['capsul.engine.execution_context.from_json', kwargs]
        
    def __enter__(self):
        self._sys_path_first = [osp.expandvars(osp.expanduser(i)) 
                                for i in self.python_path_first]
        self._sys_path_last = [osp.expandvars(osp.expanduser(i)) 
                                for i in self.python_path_last]
        sys.path = self._sys_path_first + sys.path + self._sys_path_last
        
        self._environ_backup = {}
        for n, v in self.environ.items():
            self._environ_backup[n] = os.environ.get(n)
            os.environ[n] = v

        # This code is specific to Nipype/SPM and should be
        # in a dedicated module. It is put here until 
        # modularity is added to this method.
        if os.environ.get('SPM_STANDALONE'):
            nipype = True
            try:
                from nipype.interfaces import spm
            except ImportError:
                nipype = False
            if nipype:
                import glob
                spm_directory = os.environ.get('SPM_DIRECTORY', '')
                spm_exec_glob = osp.join(spm_directory, 'mcr', 'v*')
                spm_exec = glob.glob(spm_exec_glob)
                if spm_exec:
                    spm_exec = spm_exec[0]
                    spm.SPMCommand.set_mlab_paths(
                        matlab_cmd=osp.join(spm_directory, 'run_spm%s.sh' % os.environ.get('SPM_VERSION','')) + ' ' + spm_exec + ' script',
                        use_mcr=True)

    def __exit__(self, exc_type, exc_value, traceback):
        sys_path_error = False
        if self._sys_path_first:
            if sys.path[0:len(self._sys_path_first)] == self._sys_path_first:
                del sys.path[0:len(self._sys_path_first)]
            else:
                sys_path_error = True
        if self._sys_path_last:
            if sys.path[-len(self._sys_path_last):] == self._sys_path_last:
                del sys.path[0:len(self._sys_path_last)]
            else:
                sys_path_error = True
        del self._sys_path_first
        del self._sys_path_last
        
        for n, v in self._environ_backup.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        del self._environ_backup
        
        if sys_path_error:
            raise ValueError('sys.path was modified and execution context modifications cannot be undone')



def from_json(python_path_first=[], 
                                python_path_last=[]):
    '''
    Creates an ExecutionContext from a set of parameters extracted from a
    JSON format.
    '''
    return ExecutionContext(python_path_first=python_path_first,
                            python_path_last=python_path_last)
