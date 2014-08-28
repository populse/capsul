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
from socket import getfqdn
from datetime import datetime as datetime
from copy import deepcopy
import json
import subprocess

# Trait import
from traits.trait_base import _Undefined
from traits.api import Directory, Undefined

# Soma import
from soma.controller import Controller
from soma.controller import trait_ids
from soma.utils import LateBindingProperty

# Capsul import
from capsul.utils import get_tool_version
from capsul.utils.trait_utils import (
    is_trait_value_defined, is_trait_pathname, get_trait_desc)

# Nipype import
try:
    from nipype.interfaces.base import InterfaceResult
# If nipype is not found create a dummy InterfaceResult class
except:
    InterfaceResult = type("InterfaceResult", (object, ), {})


class Process(Controller):
    """ A prosess is an atomic component that contains a processing.

    Attributes
    ----------
    `name` : str
        the class name.
    `id` : str
        the string description of the class location (ie., module.class).
    `log_file` : str (default None)
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
    def __init__(self):
        """ Initialize the Process class.
        """
        # Inheritance
        super(Process, self).__init__()

        # Initialize the process identifiers
        self.name = self.__class__.__name__
        self.id = self.__class__.__module__ + "." + self.name

        # Initialize the log file name
        self.log_file = None

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
        versions = {
            "capsul": get_tool_version("capsul"),
        }
        if hasattr(self, "_nipype_interface"):
            versions["nipype"] = get_tool_version("nipype")
            interface_name = self._nipype_interface.__module__.split(".")[2]
            versions[interface_name] = self._nipype_interface.version
        runtime["versions"] = versions

        # If a Nipype process has ran, set additional information in
        # the execution report and the the outputs
        if isinstance(returncode, InterfaceResult):
            process = returncode.interface
            if hasattr(returncode.runtime, "cmd_line"):
                runtime["cmd_line"] = returncode.runtime.cmdline
            runtime["stderr"] = returncode.runtime.stderr
            runtime["stdout"] = returncode.runtime.stdout
            runtime["cwd"] = returncode.runtime.cwd
            runtime["returncode"] = returncode.runtime.returncode
            outputs = dict(
                ("_" + x[0], self._nipype_interface._list_outputs()[x[0]])
                for x in returncode.outputs.get().iteritems())

        # Otherwise just get the outputs
        else:
            outputs = self.get_outputs()

        # Generate a process result that is returned
        results = ProcessResult(
            process, runtime, self.get_inputs(), outputs)

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

    ####################################################################
    # Public methods
    ####################################################################

    def add_trait(self, name, *trait):
        """ Add a new trait.

        Parameters
        ----------
        name: str (mandatory)
            the trait name.
        trait: traits.api (mandatory)
            a valid trait.
        """
        # Call the controller add_trait method
        super(Process, self).add_trait(name, *trait)

        # Get the trait instance and if it is a user trait load the traits
        # to get it in the traits accessor method that can select traits from
        # trait attributes
        trait_instance = self.trait(name)
        if self.is_user_trait(trait_instance):
            self.get(name)

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
        json_struct = unicode(json.dumps(exec_info, sort_keys=True,
                                         check_circular=True, indent=4))

        # Save the json structure
        f = open(self.log_file, "w")
        print >> f, json_struct
        f.close()

    @classmethod
    def help(cls):
        """ Method to print the full help.

        Parameters
        ----------
        cls: process class (mandatory)
            a process class
        """
        # Get the process class docstring
        if cls.__doc__:
            doctring = cls.__doc__.split("\n") + [""]
        else:
            doctring = [""]

        # Append the input and output traits help
        full_help = (doctring + cls.get_input_help() + [""] +
                     cls.get_output_help() + [""])

        # Print the full process help
        print("\n".join(full_help))

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
             "kwargs.update(dict(sys.argv[i * 2 + 1]: sys.argv[i * 2 + 2] "
             "for i in range((len(sys.argv) - 1) / 2))); "
             "{1}()(**kwargs)").format(module_name, class_name, repr(argsdict))
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
        for trait_name, trait in self.user_traits().iteritems():
            if trait.output:
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
            if not trait.output:
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
        for trait_name, trait in self.user_traits().iteritems():
            if trait.output:
                output[trait_name] = getattr(self, trait_name)
        return output

    @classmethod
    def get_input_help(cls):
        """ Generate description for process input parameters

        Parameters
        ----------
        cls: process class (mandatory)
            a process class

        Returns
        -------
        helpstr: str
            the class input traits help
        """
        print cls

        # Generate an input section
        helpstr = ["Inputs", "~" * 6, ""]

        # Markup to separate mandatory inputs
        manhelpstr = ["", "[Mandatory]", ""]

        # Get all the mandatory input traits
        mandatory_items = cls().traits(output=False, optional=False)

        # If we have mandatory inputs, get the corresponding string
        # descriptions
        if mandatory_items:
            for trait_name, trait_spec in mandatory_items.iteritems():
                manhelpstr.extend(
                    get_trait_desc(trait_name, trait_spec))

        # Markup to separate optional inputs
        opthelpstr = ["", "[Optional]", ""]

        # Get all optional input traits
        optional_items = cls().traits(output=False, optional=True)

        # If we have optional inputs, get the corresponding string
        # descriptions
        if optional_items:
            for trait_name, trait_spec in optional_items.iteritems():
                opthelpstr.extend(
                    get_trait_desc(trait_name, trait_spec))

        # Add the mandatry and optional input string description if necessary
        if mandatory_items:
            helpstr += manhelpstr
        if optional_items:
            helpstr += opthelpstr

        return helpstr

    @classmethod
    def get_output_help(cls):
        """ Generate description for process output parameters

        Parameters
        ----------
        cls: process class (mandatory)
            a process class

        Returns
        -------
        helpstr: str
            the trait output help descriptions
        """
        # Generate an output section
        helpstr = ["Outputs", "~" * 7, ""]

        # Get all the process output traits
        items = cls().traits(output=True)

        # If we have no output trait, return no string description
        if not items:
            return [""]

        # If we have some outputs, get the corresponding string
        # descriptions
        for trait_name, trait_spec in items.iteritems():
            helpstr.extend(
                get_trait_desc(trait_name, trait_spec))

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
        # Detect File and Directory trait types with None value
        if value is None and is_trait_pathname(self.trait(name)):

            # The None trait value is _Undefined, do the replacement
            value = _Undefined()

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


class NipypeProcess(Process):
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
        # Inheritance
        super(NipypeProcess, self).__init__(*args, **kwargs)

        # Set some class attributes that characterize the nipype interface
        self._nipype_interface = nipype_instance
        self._nipype_module = nipype_instance.__class__.__module__
        self._nipype_class = nipype_instance.__class__.__name__
        self._nipype_interface_name = self._nipype_module.split(".")[2]

        # Replace the process name and identification attributes
        self.id = ".".join([self._nipype_module, self._nipype_class])
        self.name = self._nipype_interface.__class__.__name__

        # Add a new trait to store the processing output directory
        super(Process, self).add_trait(
            "output_directory", Directory(Undefined, exists=True,
                                          optional=True))

        # Nipype '0.9.2' tricks
        # In order to run the nipype dcm2nii interface, we
        # need to create attributes that will be modified by
        # the nipype run call
        if self._nipype_interface_name == "dcm2nii":
            self.output_files = _Undefined()
            self.reoriented_files = _Undefined()
            self.reoriented_and_cropped_files = _Undefined()
            self.bvecs = _Undefined()
            self.bvals = _Undefined()

        # For the split fsl interface, initialize the dimension trait
        # value properly
        elif (self._nipype_interface_name == "fsl" and
              self._nipype_class == "Split"):

            self._nipype_interface.inputs.dimension = "t"

        # For the merge fsl interface, initialize the dimension trait
        # value properly
        elif (self._nipype_interface_name == "fsl" and
              self._nipype_class == "Merge"):

            self._nipype_interface.inputs.dimension = "t"

    def set_output_directory(self, out_dir):
        """ Set the process output directory.

        Parameters
        ----------
        out_dir: str (mandatory)
            the output directory
        """
        self.output_directory = out_dir
        self._nipype_interface.inputs.output_directory = out_dir

    def _run_process(self):
        """ Method that do the processings when the instance is called.

        Returns
        -------
        runtime: InterfaceResult
            object containing the running results
        """
        return self._nipype_interface.run()

    run = property(_run_process)


class ProcessResult(object):
    """ Object that contains running information a particular Process.

    Parameters
    ----------
    process : Process class (mandatory)
        A copy of the `Process` class that was called.
    runtime : dict (mandatory)
        Execution attributes.
    inputs :  dict (optional)
        Representation of the process inputs.
    outputs : dict (optional)
        Representation of the process outputs.
    """

    def __init__(self, process, runtime, inputs=None, outputs=None):
        """ Initialize the ProcessResult class.
        """
        self.process = process
        self.runtime = runtime
        self.inputs = inputs
        self.outputs = outputs
