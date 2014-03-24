#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import re
import subprocess


def environment(sh_file=None):
    """ Function that return a dictionary containing the environment
    needed by FSL programs.

    Parameters
    ----------
    fsl_sh: str (mandatory)
        the path to the fsl.sh script.
        If absent default locations are searched.

    Returns
    -------
    environment: dict
        a dict containing the FSL configuration
    """
    # Use sh commands and a string instead of a list since
    # we're using shell=True
    # Pass empty environment to get only the FSL variables
    command = ". {0} ; /usr/bin/printenv".format(sh_file)
    process = subprocess.Popen(command, shell=True, env={},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception("Could not parse sh_file: {0}. Maybe you should "
                        "check if all the dependencies are "
                        "installed".format(stderr))

    # Parse the output : each line should be of the form "VARIABLE_NAME=value"
    environment = {}
    for line in stdout.split(os.linesep):
        if line.startswith("export"):
            line = line.replace("export ", "")
            line = line.replace("'", "")
        match = re.match(r"^(\w+)=(\S*)$", line)
        if match:
            name, value = match.groups()
            if name != "PWD":
                environment[name] = value

    return environment


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
        raise Exception("Could not find SPM")
    stdout = process.communicate()[0]
    last_line = stdout.split("\n")[-1]

    # Weird data at the end of the line
    if '\x1b' in last_line:
        last_line = last_line[:last_line.index('\x1b')]

    # If the last line is empty, SPM not found
    if last_line == "":
        raise Exception("Could not find SPM")

    return last_line
