# -*- coding: utf-8 -*-
'''
Utility functions for configuration

Functions
=========
:func:`environment`
-------------------
'''

# System import
from __future__ import absolute_import
import os
import re
import soma.subprocess
import logging

# Define the logger
logger = logging.getLogger(__name__)


def environment(sh_file=None, env={}):
    """ Function that return a dictionary containing the environment
    needed by a program (for instance FSL or FreeSurfer).

    In the configuration file, the variable are expected to be defined
    as 'VARIABLE_NAME=value'.

    Parameters
    ----------
    sh_file: str (mandatory)
        the path to the sh script used to set up the environment.
    env: dict (optional, default empty)
        the default environment used to parse the configuration sh file.

    Returns
    -------
    environment: dict
        a dict containing the program configuration.
    """
    # Use sh commands and a string instead of a list since
    # we're using shell=True
    # Pass empty environment to get only the program variables
    command = ["bash", "-c", ". '{0}' ; /usr/bin/printenv".format(sh_file)]
    process = soma.subprocess.Popen(command, env=env,
                               stdout=soma.subprocess.PIPE, stderr=soma.subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception(
            "Could not parse sh_file: {0}. Maybe you should check if all "
            "the dependencies are installed".format(stderr))

    # Parse the output : each line should be of the form
    # 'VARIABLE_NAME=value'
    environment = {}
    for line in stdout.decode().split(os.linesep):
        if line.startswith("export"):
            line = line.replace("export ", "")
            line = line.replace("'", "")
        match = re.match(r"^(\w+)=(\S*)$", line)
        if match:
            name, value = match.groups()
            if name != "PWD":
                environment[name] = str(value)

    # Debug message
    logger.debug("Parsed FSL environment: {0}.".format(environment))

    return environment
