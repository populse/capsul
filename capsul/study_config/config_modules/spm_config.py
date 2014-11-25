##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
from traits.api import Directory, File, Bool, Enum, Undefined
from capsul.study_config.study_config import StudyConfigModule

try:
    import nipype.interfaces.matlab as matlab
    from nipype.interfaces import spm
except ImportError:
    matlab = None
    spm = None

# Define the logger
logger = logging.getLogger(__name__)

def find_spm(matlab=None, matlab_path=None):
    """ Function to return the root directory of SPM.

    Parameters
    ----------
    matlab: str (default=None)
        if given, is the path to the MATLAB executable.
    matlab_path: str (default None)
        if given, is a MATLAB expression fed to addpath.

    Returns
    -------
    last_line: str
        the SPM root directory
    """
    # Script to execute with matlab in order to find SPM root dir
    script = ("spm8;"
              "fprintf(1, '%s', spm('dir'));"
              "exit();")

    # Add matlab path if necessary
    if matlab_path:
        script = "addpath({0});".format(matlab_path) + script

    # Generate the matlab command
    command = [matlab or "matlab",
               "-nodisplay", "-nosplash", "-nojvm",
               "-r", script]

    # Try to execute the command
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
    except OSError:
        # Matlab is not present
        raise Exception("Could not find SPM.")
    stdout = process.communicate()[0]
    last_line = stdout.split("\n")[-1]

    # Do not consider weird data at the end of the line
    if '\x1b' in last_line:
        last_line = last_line[:last_line.index('\x1b')]

    # If the last line is empty, SPM not found
    if last_line == "":
        raise Exception("Could not find SPM.")

    # Debug message
    logger.debug("SPM found at location '{0}'.".format(last_line))

    return last_line


class SPMConfig(StudyConfigModule):
    
    dependencies = ['MatlabConfig']
    
    def __init__(self, study_config, configuration):
        study_config.add_trait("use_spm", Bool(
            Undefined,
            desc="If True, SPM configuration is set up on startup"))
        study_config.add_trait("spm_standalone", Bool(
            Undefined,
            desc="If True, use the standalone version of SPM"))
        study_config.add_trait('spm_directory', Directory(
            Undefined,
            output=False,
            desc='Directory containing SPM'))
        study_config.add_trait('spm_exec', File(
            Undefined,
            output=False,
            desc='SPM standalone (MCR) command path'))

        self.study_config = study_config
        study_config.on_trait_change(self.use_spm_changed,'use_spm')
    
    def use_spm_changed(self, old_value, new_value):
        """Event to setup SPM environment"""
        if new_value == 'standalone':
            if self.study_config.spm_exec is undefined:
                raise EnvironmentError('smp_exec must be defined in order to use SPM standalone')
            if not os.path.exists(self.study_config.spm_exec_cmd):
                raise EnvironmentError('"%s" is not a valid executable for SPM standalone' % self.study_config.spm_exec_cmd)
        if new_value in ('standalone', 'matlab'):
            if 'matlab_exec' not in self.study_config.user_traits():
                raise SystemError('Matlab configuration module is not included. Cannot use SPM via Matlab.')
            if self.study_config.spm_directory is undefined:
                raise EnvironmentError('smp_directory must be defined in order to use SPM')
            if not os.path.isdir(self.study_config.spm_exec_cmd):
                raise EnvironmentError('"%s" is not a valid directory for SPM' % self.study_config.spm_directory)
        

    def initialize_module(self, study_config):
        """ Set up SPM environment according to current
        configuration.
        """
        if study_config.use_spm is False:
            # Configuration is explicitely asking not to use SPM
            return
        
        if study_config.use_spm is Undefined:
            # If use_spm is not defined, SPM configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False            
        else:
            # If use_spm is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True
        
        if study_config.spm_exec is Undefined:
            # spm_exec is not set, it will not be possible to activate SPM
            if force_configuration:
                raise EnvironmentError('smp_exec must be defined in order to '
                                       'use SPM')
            study_config.use_spm = False
            return
        
        if study_config.spm_standalone is Undefined:
            # Try to guess if the configuration is for a standalone version
            if 'spm' in study_config.spm_exec:
                standalone = True
            else:
                standalone = False
        else:
             standalone = study_config.spm_standalone
        

        # If not standalone, check that Matlab is activated
        if not standalone and not study_config.use_matlab:
            if force_configuration:
                raise EnvironmentError('Matlab is disabled. Cannot use SPM '
                                       'via Matlab')
            else:
                study_config.use_spm = False
        
        if not standalone and \
           study_config.spm_directory is Undefined and \
           study_config.automatic_configuration:
                study_config.spm_directory = find_spm(study_config.matlab_exec)
        
        if study_config.spm_directory is Undefined:
            if force_configuration:
                raise EnvironmentError('smp_directory must be defined in order to use SPM')
            else:
                study_config.use_spm = False
        elif not os.path.isdir(study_config.spm_directory):
            if force_configuration:
                raise EnvironmentError('"%s" is not a valid SPM directory' % \
                                       study_config.spm_directory)
            else:
                study_config.use_spm = False
    