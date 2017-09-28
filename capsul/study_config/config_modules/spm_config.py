##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import logging
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

# TRAITS import
from traits.api import Directory, File, Bool, Enum, Undefined, Str

# CAPSUL import
from capsul.study_config.study_config import StudyConfigModule

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
    """ SPM configuration.

    There is two ways to configure SPM:
        * the first one requires to configure matlab and then to set the spm
          directory.
        * the second one is based on a standalone version of spm and requires
          to set the spm executable directory.
    """

    dependencies = ["MatlabConfig"]

    def __init__(self, study_config, configuration):
        """ Initialize the SPMConfig class.
        """
        super(SPMConfig, self).__init__(study_config, configuration)
        self.study_config.add_trait("spm_standalone", Bool(
            False,
            desc="If True, use the standalone version of SPM."))
        self.study_config.add_trait("spm_directory", Directory(
            Undefined,
            output=False,
            desc="Directory containing SPM."))
        self.study_config.add_trait("spm_exec", File(
            Undefined,
            output=False,
            desc="SPM standalone (MCR) command path."))
        self.study_config.add_trait("use_spm", Bool(
            Undefined,
            desc="If True, SPM configuration is set up on startup."))
        self.study_config.add_trait('spm_version', Str(
            Undefined, output=False,
            desc='Version string for SPM: "12", "8", etc.'))

    def initialize_module(self):
        """ Set up SPM environment according to current configuration.
        """
        if self.study_config.use_spm is False:
            # Configuration is explicitely asking not to use SPM
            return
        elif self.study_config.use_spm is True:
            # If use_spm is True configuration must be valid otherwise
            # an EnvironmentError is raised
            force_configuration = True
        else:
            # If use_spm is not defined, SPM configuration will
            # be done if possible but there will be no error if it cannot be
            # done.
            force_configuration = False
        self.study_config.use_spm = True

        # If we need to check spm configuration
        if self.study_config.use_spm is True:

            # If standalone
            if self.study_config.spm_standalone is True:

                # Check that a valid file has been set for the stanalone
                # version of spm
                if (self.study_config.spm_exec is Undefined or 
                        not os.path.isfile(self.study_config.spm_exec)):
                    self.study_config.use_spm = False
                    if force_configuration:
                        raise EnvironmentError("'spm_exec' must be defined in "
                                               "order to use SPM-standalone.")
                    else:
                        return

                # determine SPM version (currently 8 or 12)
                if os.path.isdir(os.path.join(
                    self.study_config.spm_directory, 'spm12_mcr')):
                    self.study_config.spm_version = '12'
                elif os.path.isdir(os.path.join(
                    self.study_config.spm_directory, 'spm8_mcr')):
                    self.study_config.spm_version = '8'
                else:
                    self.study_config.spm_version = Undefined

            # If not standalone
            else:

                # Check that Matlab is activated
                if not self.study_config.use_matlab:
                    self.study_config.use_spm = False
                    if force_configuration:
                        raise EnvironmentError(
                            "Matlab is disabled. Cannot use SPM via Matlab.")
                    else:
                        return

                # If the spm sources are not set, try to find them automaticaly
                if self.study_config.spm_directory is Undefined:
                    self.study_config.spm_directory = find_spm(
                        self.study_config.matlab_exec)

                # Check that a valid directory has been set for spm sources
                if not os.path.isdir(self.study_config.spm_directory):
                    self.study_config.use_spm = False
                    if force_configuration:
                        raise EnvironmentError(
                            "'{0}' is not a valid SPM directory.".format(
                                self.study_config.spm_directory))
                    else:
                        return

                # determine SPM version (currently 8 or 12)
                if os.path.isdir(os.path.join(
                    self.study_config.spm_directory, 'toolbox', 'OldNorm')):
                    self.study_config.spm_version = '12'
                elif os.path.isdir(os.path.join(
                    self.study_config.spm_directory, 'templates')):
                    self.study_config.spm_version = '8'
                else:
                    self.study_config.spm_version = Undefined

    def initialize_callbacks(self):
        """ When the 'use_spm' trait changes, configure spm with the new
        setting.
        """
        self.study_config.on_trait_change(self.initialize_module, "use_spm")
   
