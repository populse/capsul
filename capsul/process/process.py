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
import operator
from socket import getfqdn
from datetime import datetime as datetime
from copy import deepcopy
import json
import subprocess
import logging
import shutil

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.trait_base import _Undefined
from traits.api import Directory, Undefined
from traits.trait_handlers import BaseTraitHandler

# Soma import
from soma.controller import Controller
from soma.controller import trait_ids
from soma.utils import LateBindingProperty
from soma.controller.trait_utils import is_trait_value_defined
from soma.controller.trait_utils import is_trait_pathname
from soma.controller.trait_utils import get_trait_desc

# Capsul import
from capsul.utils.version_utils import get_tool_version
from capsul.utils.trait_utils import is_trait_either


class ProcessMeta(Controller.__metaclass__):
    """ Class used to complete a process docstring

    Use a class and not a function for inheritance.
    """
    def __new__(mcls, name, bases, attrs):
        """ Method to print the full help.

        Parameters
        ----------
        mcls: meta class (mandatory)
            a meta class.
        name: str (mandatory)
            the process class name.
        bases: tuple (mandatory)
            the direct base classes.
        attrs: dict (mandatory)
            a dictionnary with the class attributes.
        """
        # Get the process docstring
        docstring = attrs.get("__doc__", "").split("\n")

        # we have to indent the note properly so that the docstring is
        # properly displayed, and correctly processed by sphinx
        indent = -1
        for line in docstring[1:]:
            lstrip = line.strip()
            if not lstrip:  # empty lines do not influence indent
                continue
            lindent = line.index(line.strip())
            if indent == -1 or lindent < indent:
                indent = lindent
        if indent < 0:
            indent = 0

        # Complete the docstring
        docstring += [' ' * indent + line for line in [
            "",
            ".. note::",
            "",
            "    * Type '{0}.help()' for a full description of "
            "this process parameters.".format(name),
            "    * Type '<{0}>.get_input_spec()' for a full description of "
            "this process input trait types.".format(name),
            "    * Type '<{0}>.get_output_spec()' for a full description of "
            "this process output trait types.".format(name),
            ""
        ]]

        # Update the class docstring with the full process help
        attrs["__doc__"] = "\n".join(docstring)

        # Find all traits definitions in the process class and ensure that
        # it has a boolean value for attributes "output" and "optional".
        # If no value is given at construction, False will be used.
        for n, possible_trait_definition in attrs.iteritems():
            if isinstance(possible_trait_definition, BaseTraitHandler):
                possible_trait_definition._metadata['output'] = bool(possible_trait_definition.output)
                possible_trait_definition._metadata['optional'] = bool(possible_trait_definition.optional)
        
        return super(ProcessMeta, mcls).__new__(
            mcls, name, bases, attrs)


class Process(Controller):
    """ A process is an atomic component that contains a processing.

    Attributes
    ----------
    `name`: str
        the class name.
    `id`: str
        the string description of the class location (ie., module.class).
    `log_file`: str (default None)
        if None, the log will be generated in the current directory
        otherwise it will be written in log_file path.

    Methods
    -------
    __call__
    _run_process
    _get_log
    add_trait
    save_log
    help
    get_input_help
    get_output_help
    get_commandline
    get_log
    get_input_spec
    get_output_spec
    get_inputs
    get_outputs
    set_parameter
    get_parameter

    """
    # Meta class used to complete the class docstring
    __metaclass__ = ProcessMeta

    def __init__(self):
        """ Initialize the Process class.
        """
        # Inheritance
        super(Process, self).__init__()

        # Initialize the process identifiers
        self.name = self.__class__.__name__
        self.id = self.__class__.__module__ + "." + self.name

        # Parameter to store which tools will be used dusring the processing
        self.versions = {
            "capsul": get_tool_version("capsul")
        }

        # Initialize the log file name
        self.log_file = None

        # Define reserved control names
        self.reserved_controls = ("nodes_activation", "selection_changed")

    def add_trait(self, name, trait):
        """Ensure that trait.output and trait.optional are set to a
        boolean value before calling parent class add_trait.
        """
        if trait._metadata is not None:
            trait._metadata['output'] = bool(trait.output)
            trait._metadata['optional'] = bool(trait.optional)
        else:
            trait.output = bool(trait.output)
            trait.optional = bool(trait.optional)
        super(Process, self).add_trait(name, trait)

    def traits(self, **kwargs):
        """ Returns a dictionary containing the definitions of all of the trait
        attributes of this object that match the set of *metadata* criteria.
        """
        traits = super(Process, self).traits(**kwargs)
        for name in self.reserved_controls:
            if name in traits:
                traits.pop(name)
        return traits
        
    def __call__(self, **kwargs):
        """ Method to execute the Process.

        Keyword arguments may be passed to set process parameters.
        This in turn will allow calling the process like a standard
        python function.
        In such case keyword arguments are set in the process in
        addition to those already set before the call.

        Raise a TypeError if a keyword argument do not match with a
        process trait name.

        .. note:

            This method must not modify the class attributes in order
            to be able to perform smart caching.

        .. node:

            This method should not be overloaded by Process subclasses to
            perform actual processing. Instead, either the
            :meth:`_run_process` method or the :meth:`get_commandline` method
            should be overloaded.

        Parameters
        ----------
        kwargs: dict (optional)
            should correspond to the declared parameter traits.

        Returns
        -------
        results:  ProcessResult object
            contains all execution information.
        """
        # Get the process class
        process = self.__class__

        # Initialize the execution report
        runtime = {
            "start_time": datetime.isoformat(datetime.utcnow()),
            "cwd": os.getcwd(),
            "returncode": None,
            "environ": deepcopy(os.environ.data),
            "end_time": None,
            "hostname": getfqdn(),
        }

        # Set process parameters if extra arguments are passed
        if kwargs:

            # Go through all the extra parameters
            for arg_name, arg_val in kwargs.iteritems():

                # If the extra parameter name do not match with a user
                # trait paameter name, raise a TypeError
                if arg_name not in self.user_traits():
                    raise TypeError(
                        "Process __call__ got an unexpected keyword "
                        "argument '{0}'".foramt(arg_name))

                # Set the extra parameter value
                setattr(self, arg_name, arg_val)

        # Execute the process
        returncode = self._run_process()

        # Set the execution stop time in the execution report
        runtime["end_time"] = datetime.isoformat(datetime.utcnow())

        # Set the dependencies versions in the execution report
        runtime["versions"] = self.versions

        # Generate a process result that is returned
        results = ProcessResult(
            process, runtime, returncode, self.get_inputs(),
            self.get_outputs())

        return results

    ####################################################################
    # Private methods
    ####################################################################

    def _run_process(self):
        """ Method that contains the processings.

        Either this _run_process() or get_commandline() must be
        defined in derived classes.

        .. note:

            If both methods are not defined in the derived class a
            NotImplementedError error is raised.
        """
        # Check if get_commandline() method is specialized
        # If yes, we can make use of it to execute the process
        if self.__class__.get_commandline != Process.get_commandline:
            commandline = self.get_commandline()
            subprocess.check_call(commandline)

        # Otherwise raise an error
        else:
            raise NotImplementedError(
                "Either get_commandline() or _run_process() should be "
                "redefined in process ({0})".format(
                    self.__class__.__name__))

    def _get_log(self, exec_info):
        """ Method that generate the logging structure from the execution
        information and class attributes.

        Parameters
        ----------
        exec_info: dict (mandatory)
            the execution informations,
            the dictionnary is supposed to contain a runtime attribute.

        Returns
        -------
        log: dict
            the logging information.
        """
        # Set all the execution runtime information in the log
        log = exec_info.runtime

        # Add the process identifiaction class attribute
        log["process"] = self.id

        # Add the process inputs and outputs
        log["inputs"] = exec_info.inputs.copy()
        log["outputs"] = exec_info.outputs.copy()

        # Need to take the representation of undefined input or outputs
        # traits
        for parameter_type in ["inputs", "outputs"]:
            for key, value in log[parameter_type].iteritems():
                if value is Undefined:
                    log[parameter_type][key] = repr(value)

        return log

    def _rst_table(self, data):
        """ Create a rst formated table.

        Parameters
        ----------
        data: list of list of str (mandatory)
            the table line-cell centent.

        Returns
        -------
        rsttable: list of str
            the rst formated table containing the input data.
        """
        # Output rst table
        rsttable = []

        # Get the size of the largest row in order to
        # format properly the rst table (do not forget the '+' and '*')
        row_widths = [len(item) for item in reduce(operator.add, data)]
        width = max(row_widths) + 11

        # Generate the rst table

        # > table synthax
        rsttable.append("+" + "-" * width + "+")
        # > go through the table lines
        for table_row in data:
            # > go through the cell lines
            for index, cell_row in enumerate(table_row):
                # > set the parameter name in bold
                if index == 0 and ":" in cell_row:
                    delimiter_index = cell_row.index(":")
                    cell_row = ("**" + cell_row[:delimiter_index] + "**" +
                                cell_row[delimiter_index:])
                # >  add table rst content
                rsttable.append(
                    "| | {0}".format(cell_row) +
                    " " * (width - len(cell_row) - 3) +
                    "|")
            # > close cell
            rsttable.append("+" + "-" * width + "+")

        return rsttable

    ####################################################################
    # Public methods
    ####################################################################

    def save_log(self, returncode):
        """ Method to save process execution informations in json format.

        If the class attribute `log_file` is not set, a log.json output
        file is generated in the process call current working directory.

        Parameters
        ----------
        returncode: ProcessResult
            the process result return code.
        """
        # Build the logging information
        exec_info = self._get_log(returncode)

        # Generate an output log file name if necessary
        if not self.log_file:
            self.log_file = os.path.join(exec_info["cwd"], "log.json")

        # Dump the log
        json_struct = json.dumps(exec_info, sort_keys=True,
                                 check_circular=True, indent=4)

        # Save the json structure
        with open(self.log_file, "w") as f:
            f.write(unicode(json_struct))

    @classmethod
    def help(cls, returnhelp=False):
        """ Method to print the full help.

        Parameters
        ----------
        cls: process class (mandatory)
            a process class
        returnhelp: bool (optional, default False)
            if True return the help string message,
            otherwise display it on the console.
        """
        cls_instance = cls()
        return cls_instance.get_help(returnhelp)

    ####################################################################
    # Accessors
    ####################################################################

    def get_commandline(self):
        """ Method to generate a comandline representation of the process.
        """
        # Get command line arguments (ie., the process user traits)
        reserved_params = ("nodes_activation", "selection_changed")
        args = [
            (trait_name, is_trait_pathname(trait))
            for trait_name, trait in self.user_traits().iteritems()
            if (trait_name not in reserved_params and
                is_trait_value_defined(getattr(self, trait_name)))]

        # Build the python call expression, keeping apart file names.
        # File names are given separately since they might be modified
        # externally afterwards, typically to handle temporary files, or
        # file transfers with Soma-Workflow.
        argsdict = dict(
            (trait_name, getattr(self, trait_name))
            for trait_name, is_pathname in args if not is_pathname)
        pathsdict = dict(
            (trait_name, getattr(self, trait_name))
            for trait_name, is_pathname in args if is_pathname)

        # Get the module and class names
        module_name = self.__class__.__module__
        class_name = self.name

        # Construct the command line
        commandline = [
            "python",
            "-c",
            ("import sys; from {0} import {1}; kwargs={2}; "
             "kwargs.update(dict((sys.argv[i * 2 + 1], sys.argv[i * 2 + 2]) "
             "for i in range((len(sys.argv) - 1) / 2))); "
             "{1}()(**kwargs)").format(module_name, class_name,
                                       repr(argsdict)).replace("'", '"')
        ] + sum([list(x) for x in pathsdict.items()], [])

        return commandline

    def get_log(self):
        """ Load the logging file.

        .. note:

            If no log file found, return None

        Returns
        -------
        log: dict
            the content of the log file.
        """
        if os.path.isfile(self.log_file):
            with open(self.log_file) as json_file:
                return json.load(json_file)
        else:
            return None

    def get_input_spec(self):
        """ Method to access the process input specifications.

        Returns
        -------
        outputs: str
            a string representation of all the input trait specifications.
        """
        output = "\nINPUT SPECIFICATIONS\n\n"
        # self.traits(output=False) skips params with no output property
        for trait_name, trait in self.user_traits().iteritems():
            if not trait.output:
                output += "{0}: {1}\n".format(
                    trait_name, trait_ids(self.trait(trait_name)))
        return output

    def get_output_spec(self):
        """ Method to access the process output specifications.

        Returns
        -------
        outputs: str
            a string representation of all the output trait specifications.
        """
        output = "\nOUTPUT SPECIFICATIONS\n\n"
        for trait_name, trait in self.traits(output=True).iteritems():
            output += "{0}: {1}\n".format(
                trait_name, trait_ids(self.trait(trait_name)))
        return output

    def get_inputs(self):
        """ Method to access the process inputs.

        Returns
        -------
        outputs: dict
            a dictionary with all the input trait names and values.
        """
        output = {}
        for trait_name, trait in self.user_traits().iteritems():
            if not trait.output and trait_name != "nodes_activation":
                output[trait_name] = getattr(self, trait_name)
        return output

    def get_outputs(self):
        """ Method to access the process outputs.

        Returns
        -------
        outputs: dict
            a dictionary with all the output trait names and values.
        """
        output = {}
        for trait_name, trait in self.traits(output=True).iteritems():
            output[trait_name] = getattr(self, trait_name)
        return output

    def get_help(self, returnhelp=False):
        """ Generate description of a process parameters.

        Parameters
        ----------
        returnhelp: bool (optional, default False)
            if True return the help string message formatted in rst,
            otherwise display the raw help string message on the console.
        """
        # Create the help content variable
        doctring = [""]

        # Update the documentation with a description of the pipeline
        # when the xml to pipeline wrapper has been used
        if returnhelp and hasattr(self, "_pipeline_desc"):
            str_desc = "".join(["    {0}".format(line)
                                for line in self._pipeline_desc])
            doctring += [
                ".. hidden-code-block:: python",
                "    :starthidden: True",
                "",
                str_desc,
                ""
            ]

        # Get the process docstring
        if self.__doc__:
            doctring += self.__doc__.split("\n") + [""]

        # Update the documentation with a reference on the source function
        # when the function to process wrapper has been used
        if hasattr(self, "_func_name") and hasattr(self, "_func_module"):
            doctring += [
                "This process has been wrapped from {0}.{1}.".format(
                    self._func_module, self._func_name),
                ""
            ]
            if returnhelp:
                doctring += [
                    ".. currentmodule:: {0}".format(self._func_module),
                    "",
                    ".. autosummary::",
                    "    :toctree: ./",
                    "",
                    "    {0}".format(self._func_name),
                    ""
                ]

        # Append the input and output traits help
        full_help = (doctring + self.get_input_help(returnhelp) + [""] +
                     self.get_output_help(returnhelp) + [""])
        full_help = "\n".join(full_help)

        # Return the full process help
        if returnhelp:
            return full_help
        # Print the full process help
        else:
            print(full_help)

    def get_input_help(self, rst_formating=False):
        """ Generate description for process input parameters.

        Parameters
        ----------
        rst_formating: bool (optional, default False)
            if True generate a rst table witht the input descriptions.

        Returns
        -------
        helpstr: str
            the class input traits help
        """
        # Generate an input section
        helpstr = ["Inputs", "~" * 6, ""]

        # Markup to separate mandatory inputs
        manhelpstr = ["[Mandatory]", ""]

        # Get all the mandatory input traits
        mandatory_items = dict([x for x in self.user_traits().iteritems()
                                if not x[1].output and not x[1].optional])
        mandatory_items.update(self.traits(output=None, optional=False))

        # If we have mandatory inputs, get the corresponding string
        # descriptions
        data = []
        if mandatory_items:
            for trait_name, trait in mandatory_items.iteritems():
                if trait_name != "nodes_activation":
                    trait_desc = get_trait_desc(trait_name, trait)
                    data.append(trait_desc)

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                manhelpstr += self._rst_table(data)
            # Otherwise
            else:
                manhelpstr += reduce(operator.add, data)

        # Markup to separate optional inputs
        opthelpstr = ["", "[Optional]", ""]

        # Get all optional input traits
        optional_items = self.traits(output=False, optional=True)
        optional_items.update(self.traits(output=None, optional=True))

        # If we have optional inputs, get the corresponding string
        # descriptions
        data = []
        if optional_items:
            for trait_name, trait in optional_items.iteritems():
                data.append(
                    get_trait_desc(trait_name, trait))

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                opthelpstr += self._rst_table(data)
            # Otherwise
            else:
                opthelpstr += reduce(operator.add, data)

        # Add the mandatry and optional input string description if necessary
        if mandatory_items:
            helpstr += manhelpstr
        if optional_items:
            helpstr += opthelpstr

        return helpstr

    def get_output_help(self, rst_formating=False):
        """ Generate description for process output parameters.

        Parameters
        ----------
        rst_formating: bool (optional, default False)
            if True generate a rst table witht the input descriptions.

        Returns
        -------
        helpstr: str
            the trait output help descriptions
        """
        # Generate an output section
        helpstr = ["Outputs", "~" * 7, ""]

        # Get all the process output traits
        items = self.traits(output=True)

        # If we have no output trait, return no string description
        if not items:
            return [""]

        # If we have some outputs, get the corresponding string
        # descriptions
        data = []
        for trait_name, trait in items.iteritems():
            data.append(
                get_trait_desc(trait_name, trait))

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                helpstr += self._rst_table(data)
            # Otherwise
            else:
                helpstr += reduce(operator.add, data)

        return helpstr

    def set_parameter(self, name, value):
        """ Method to set a process instance trait value.

        For File and Directory traits the None value is replaced by the
        special _Undefined trait value.

        Parameters
        ----------
        name: str (mandatory)
            the trait name we want to modify
        value: object (mandatory)
            the trait value we want to set
        """
        # The None trait value is Undefined, do the replacement
        if value is None:
            value = Undefined

        # Set the new trait value
        setattr(self, name, value)

    def get_parameter(self, name):
        """ Method to access the value of a process instance.

        Parameters
        ----------
        name: str (mandatory)
            the trait name we want to modify

        Returns
        -------
        value: object
            the trait value we want to access
        """
        return getattr(self, name)

    run = LateBindingProperty(
        _run_process, None, None,
        "Processing method that has to be defined in derived classes")


class FileCopyProcess(Process):
    """ A specific process that copies all the input files.

    Attributes
    ----------
    `copied_inputs` : list of 2-uplet
        the list of copied files (src, dest).

    Methods
    -------
    __call__
    _update_input_traits
    _get_process_arguments
    _copy_input_files
    """
    def __init__(self, activate_copy=True, inputs_to_copy=None,
                 inputs_to_clean=None, destination=None):
        """ Initialize the FileCopyProcess class.

        Parameters
        ----------
        activate_copy: bool (default True)
            if False this class is transparent and behaves as a Process class.
        inputs_to_copy: list of str (optional, default None)
            the list of inputs to copy.
            If None, all the input files are copied.
        inputs_to_clean: list of str (optional, default None)
            some copied inputs that can be deleted at the end of the
            processing.
        destination: str (optional default None)
            where the files are copied.
            If None, files are copied in a '_workspace' folder included in the
            image folder.
        """
        # Inheritance
        super(FileCopyProcess, self).__init__()

        # Class parameters
        self.activate_copy = activate_copy
        self.destination = destination
        if self.activate_copy:
            self.inputs_to_clean = inputs_to_clean or []
            if inputs_to_copy is None:
                self.inputs_to_copy = self.user_traits().keys()
            else:
                self.inputs_to_copy = inputs_to_copy
            self.copied_inputs = None

    def __call__(self, **kwargs):
        """ Method to execute the FileCopyProcess.
        """
        # The copy option is activated
        if self.activate_copy:

            # Set the process inputs
            for name, value in kwargs.iteritems():
                self.process.set_parameter(name, value)

            # Copy the desired items
            self._update_input_traits()

            # Inheritance
            result = super(FileCopyProcess, self).__call__(
                **self.copied_inputs)

            # Clean the workspace
            self._clean_workspace()

            return result

        # Transparent class, call the Process class method
        else:

            # Inheritance
            return super(FileCopyProcess, self).__call__(**kwargs)

    def _clean_workspace(self):
        """ Removed som copied inputs that can be deleted at the end of the
        processing.
        """
        for to_rm_name in self.inputs_to_clean:
            if to_rm_name in self.copied_inputs:
                self._rm_files(self.copied_inputs[to_rm_name])

    def _rm_files(self, python_object):
        """ Remove a set of copied files from the filesystem.

        Parameters
        ----------
        python_object: object
            a generic python object.
        """
        # Deal with dictionary
        if isinstance(python_object, dict):
            for val in python_object.values():
                self._rm_files(val)

        # Deal with tuple and list
        elif isinstance(python_object, (list, tuple)):
            for val in python_object:
                self._rm_files(val)

        # Otherwise start the deletion if the object is a file
        else:
            if (isinstance(python_object, basestring) and
                    os.path.isfile(python_object)):
                os.remove(python_object)

    def _update_input_traits(self):
        """ Update the process input traits: input files are copied.
        """
        # Get the new trait values
        input_parameters = self._get_process_arguments()
        self.copied_inputs = self._copy_input_files(input_parameters)

    def _copy_input_files(self, python_object):
        """ Recursive method that copy the input process files.

        Parameters
        ----------
        python_object: object
            a generic python object.

        Returns
        -------
        out: object
            the copied-file input object.
        """
        # Deal with dictionary
        # Create an output dict that will contain the copied file locations
        # and the other values
        if isinstance(python_object, dict):
            out = {}
            for key, val in python_object.items():
                if val is not Undefined:
                    out[key] = self._copy_input_files(val)

        # Deal with tuple and list
        # Create an output list or tuple that will contain the copied file
        # locations and the other values
        elif isinstance(python_object, (list, tuple)):
            out = []
            for val in python_object:
                if val is not Undefined:
                    out.append(self._copy_input_files(val))
            if isinstance(python_object, tuple):
                out = tuple(out)

        # Otherwise start the copy (with metadata cp -p) if the object is
        # a file
        else:
            out = python_object
            if (python_object is not Undefined and
                    isinstance(python_object, basestring) and
                    os.path.isfile(python_object)):
                srcdir = os.path.dirname(python_object)
                if self.destination is None:
                    destdir = os.path.join(srcdir, "_workspace")
                else:
                    destdir = self.destination
                if not os.path.exists(destdir):
                    os.makedirs(destdir)
                fname = os.path.basename(python_object)
                out = os.path.join(destdir, fname)
                shutil.copy2(python_object, out)

        return out

    def _get_process_arguments(self):
        """ Get the process arguments.

        The user process traits are accessed through the user_traits()
        method that returns a sorted dictionary.

        Returns
        -------
        input_parameters: dict
            the process input parameters.
        """
        # Store for input parameters
        input_parameters = {}

        # Go through all the user traits
        for name, trait in self.user_traits().iteritems():

            # Check if the target parameter is in the check list
            if name in self.inputs_to_copy:

                # Get the trait value
                value = self.get_parameter(name)

                # Split input and output traits
                is_input = True
                if "output" in trait.__dict__ and trait.output:
                    is_input = False

                # Skip undefined trait attributes and outputs
                if is_input and value is not Undefined:

                    # Store the input parameter
                    input_parameters[name] = value

        return input_parameters


class NipypeProcess(FileCopyProcess):
    """ Base class used to wrap nipype interfaces.
    """
    def __init__(self, nipype_instance, *args, **kwargs):
        """ Initialize the NipypeProcess class.

        NipypeProcess instance get automatically an additional user trait
        'output_directory'.

        This class also fix also some lake of the nipye version '0.9.2'.

        Parameters
        ----------
        nipype_instance: nipype interface (mandatory)
            the nipype interface we want to wrap in capsul.

        Attributes
        ----------
        _nipype_interface : Interface
            private attribute to store the nipye interface
        _nipype_module : str
            private attribute to store the nipye module name
        _nipype_class : str
            private attribute to store the nipye class name
        _nipype_interface_name : str
            private attribute to store the nipye interface name
        """
        # Set some class attributes that characterize the nipype interface
        self._nipype_interface = nipype_instance
        self._nipype_module = nipype_instance.__class__.__module__
        self._nipype_class = nipype_instance.__class__.__name__
        self._nipype_interface_name = self._nipype_module.split(".")[2]
        self.desc = self._nipype_module + "." + self._nipype_class

        # Inheritance: activate input files copy for spm interfaces.
        if self._nipype_interface_name == "spm":
            # Copy only 'copyfile' nipype traits
            inputs_to_copy = self._nipype_interface.inputs.traits(
                copyfile=True).keys()
            super(NipypeProcess, self).__init__(
                activate_copy=True, inputs_to_copy=inputs_to_copy, *args,
                **kwargs)
        else:
            super(NipypeProcess, self).__init__(
                activate_copy=False, *args, **kwargs)

        # Replace the process name and identification attributes
        self.id = ".".join([self._nipype_module, self._nipype_class])
        self.name = self._nipype_interface.__class__.__name__

        # Set the nipype and nipype interface versions
        if self._nipype_interface_name != "spm":
            self.versions.update({
                "nipype": get_tool_version("nipype"),
                self._nipype_interface_name: self._nipype_interface.version
            })
        else:
            from nipype.interfaces.spm import SPMCommand
            from nipype.interfaces.matlab import MatlabCommand
            self.versions.update({
                "nipype": get_tool_version("nipype"),
                self._nipype_interface_name: "{0}-{1}|{2}-{3}".format(
                    SPMCommand._matlab_cmd, MatlabCommand._default_paths,
                    SPMCommand._paths, SPMCommand._use_mcr)
            })

        # Add a new trait to store the processing output directory
        super(Process, self).add_trait(
            "output_directory", Directory(Undefined, exists=True,
                                          optional=True))

    def __call__(self, **kwargs):
        """ Method to execute the NipypeProcess.

        Keyword arguments may be passed to set process parameters.
        This in turn will allow calling the process like a standard
        python function.
        In such case keyword arguments are set in the process in
        addition to those already set before the call.

        Raise a TypeError if a keyword argument do not match with a
        process trait name.

        .. note:

            This method must not modified the class attributes in order
            to be able to perform smart caching.

        Parameters
        ----------
        kwargs: dict (optional)
            should correspond to the declared parameter traits.

        Returns
        -------
        results:  ProcessResult object
            contains all execution information
        """
        # Single task worker: change worker current working
        # directory safely (usefull for nipype spm interfaces)
        os.chdir(self.output_directory)

        # Inheritance
        if self._nipype_interface_name == "spm":
            # Set the spm working
            self.destination = self.output_directory
            # Clean the working folder
            if os.path.isdir(self.output_directory):
                items_in_folder = os.listdir(self.output_directory)
                if len(items_in_folder) != 0:
                    logger.info("Found items '{0}', exec auto-clean for spm "
                                "process.".format(items_in_folder))
                    shutil.rmtree(self.output_directory)
            results = super(NipypeProcess, self).__call__(**kwargs)
        # Do nothing specific
        else:
            results = super(NipypeProcess, self).__call__(**kwargs)

        # For spm, need to move the batch
        # (create in cwd: cf nipype.interfaces.matlab.matlab l.181)
        if self._nipype_interface_name == "spm":
            mfile = os.path.join(
                os.getcwd(),
                self._nipype_interface.mlab.inputs.script_file)
            destmfile = os.path.join(
                self.output_directory,
                self._nipype_interface.mlab.inputs.script_file)
            if os.path.isfile(mfile):
                shutil.move(mfile, destmfile)

        # Set additional information in the execution report
        returncode = results.returncode
        if hasattr(returncode.runtime, "cmd_line"):
            results.runtime["cmd_line"] = returncode.runtime.cmdline
        results.runtime["stderr"] = returncode.runtime.stderr
        results.runtime["stdout"] = returncode.runtime.stdout
        results.runtime["cwd"] = returncode.runtime.cwd
        results.runtime["returncode"] = returncode.runtime.returncode

        # Set the nipype outputs to the execution report
        outputs = dict(
            ("_" + x[0], self._nipype_interface._list_outputs()[x[0]])
            for x in returncode.outputs.get().iteritems())
        results.outputs = outputs

        return results

    def set_output_directory(self, out_dir):
        """ Set the process output directory.

        Parameters
        ----------
        out_dir: str (mandatory)
            the output directory
        """
        self.output_directory = out_dir

    def _run_process(self):
        """ Method that do the processings when the instance is called.

        Returns
        -------
        runtime: InterfaceResult
            object containing the running results
        """
        return self._nipype_interface.run()

    @classmethod
    def help(cls, nipype_interface, returnhelp=False):
        """ Method to print the full wraped nipype interface help.

        Parameters
        ----------
        cls: process class (mandatory)
            a nipype process class
        nipype_instance: nipype interface (mandatory)
            a nipype interface object that will be documented.
        returnhelp: bool (optional, default False)
            if True return the help string message,
            otherwise display it on the console.
        """
        from .nipype_process import nipype_factory
        cls_instance = nipype_factory(nipype_interface)
        return cls_instance.get_help(returnhelp)

    run = property(_run_process)


class ProcessResult(object):
    """ Object that contains running information a particular Process.

    Parameters
    ----------
    process : Process class (mandatory)
        A copy of the `Process` class that was called.
    runtime : dict (mandatory)
        Execution attributes.
    returncode: dict (mandatory)
        Execution raw attributes
    inputs :  dict (optional)
        Representation of the process inputs.
    outputs : dict (optional)
        Representation of the process outputs.
    """

    def __init__(self, process, runtime, returncode, inputs=None,
                 outputs=None):
        """ Initialize the ProcessResult class.
        """
        self.process = process
        self.runtime = runtime
        self.returncode = returncode
        self.inputs = inputs
        self.outputs = outputs
