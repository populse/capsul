#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
import re
import subprocess


def environment(sh_file=None):
    """ Return a dictionary of the environment needed by FSL programs. fsl_sh
        is the path to the fsl.sh script; if absent default locations are
        searched.
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
    """ Return the root directory of SPM.
        'matlab', if given, is the path to the MATLAB executable.
        'matlab_path', if given, is a MATLAB expression fed to addpath.
    """

    script = ("spm8;"
              "fprintf(1, '%s', spm('dir'));"
              "exit();")

    if matlab_path:
        script = "addpath({0});".format(matlab_path) + script

    command = [matlab or "matlab",
               "-nodisplay", "-nosplash", "-nojvm",
               "-r", script]

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
    if last_line == "":
        raise Exception("Could not find SPM")

    return last_line
