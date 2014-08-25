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
import sys

# Traits import
try:
    from traits.api import String
except ImportError:
    from enthought.traits.api import String

# Capsul import
from capsul.process import Process

# Genibabel import
from bioresource import BioresourceDB


def title_for(title):
    """ Create a title from an underscore-separated string.

    Parameters
    ----------
    title: str (mandatory)
        the string to format.

    Returns
    -------
    out: str
        the formated string.
    """
    return title.replace("_", " ").title().replace(" ", "")


class CWProcess(Process):
    """ Dummy class to dynamically generate processes to access a cw database.
    """
    def __init__(self):
        """ Initialize the CWProcess class
        """
        # Inheritance
        super(CWProcess, self).__init__()

        # Define input traits
        self.add_trait("url", String(
            "http://mart.intra.cea.fr/genetic_imagen/",
            optional=False,
            output=False,
            desc=("the cw instance url.")))
        self.add_trait("login", String(
            optional=False,
            output=False,
            desc=("the cw instance login.")))
        self.add_trait("password", String(
            optional=False,
            output=False,
            desc=("the cw instance password.")))

        # Define output traits
        self.add_trait("array", String(
            optional=False,
            output=True,
            desc=("the cw instance result set.")))

        # Redifine process identifier
        if hasattr(self, "_id"):
            self.id = self._id

    def _run_process(self):
        """ Get the information from the cw database.
        """
        # Connection to the cw instance
        opener = BioresourceDB(self.url, self.login, self.password)

        # Execucute the request to the database
        self.array = opener.__dict__[self.question_name]


def class_factory(func):
    """ Dynamically create a process instance from a function

    In order to make the class publicly accessible, we assign the result of
    the function to a variable dynamically using globals().

    Parameters
    ----------
    func: @function (mandatory)
        the function we want encapsulate in a process.
    """
    # Create the process class name
    class_name = title_for(func.__name__)

    # Define the process class parameters
    class_parameters = {
        "_id":  __name__ + "." + class_name,
        "__doc__": func.__doc__
    }

    # Get the process instance associated to the function
    globals()[class_name] = type(class_name, (CWProcess, ), class_parameters)


def register_processes(functions):
    """ Register a number of new processes from function.

    Parameters
    ----------
    functions: list of @function (mandatory)
        a list of functions we want to encapsulate in processes.
    """
    # Go through all function and create/register the corresponding process
    for func in functions:
        class_factory(func)
