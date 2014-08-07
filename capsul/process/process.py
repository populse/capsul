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
import types
from socket import getfqdn
from datetime import datetime as datetime
from copy import deepcopy
import json
import subprocess

# Trait import
try:
    import traits.api as traits
    from traits.trait_base import _Undefined
    from traits.api import (ListStr, HasTraits, File, Float, Instance,
                            Enum, Str, Directory, Dict, Undefined)
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.trait_base import _Undefined
    from enthought.traits.api import (ListStr, HasTraits, File, Float,
                                      Instance, Enum, Str, Directory, Dict,
                                      Undefined)

# Capsul import
from soma.controller import Controller
from soma.controller import trait_ids
from capsul.utils import get_tool_version
from soma.utils import LateBindingProperty

# If nipype is not found create a dummy InterfaceResult class
try:
    from nipype.interfaces.base import InterfaceResult
except:
    class InterfaceResult(object):
        pass


class Process(Controller):
    """ A prosess is an atomic component that contains the processing.

    Attributes
    ----------
    `name` : str
        the class name
    `id` : str
        the string description of the class location
    `runtime` : dict (default None)
        after the process execution, a dictionary containing all
        exection information
    `log_file` : str (default None)
        if None, the log will be generated in the current directory
        otherwise is will be written in log_file

    Methods
    -------
    __call__
    _run_process
    get_commandline
    save_log
    get_input_spec
    get_outputs
    set_parameter
    get_parameter
    """
    def __init__(self):
        """ Initialize the Process class.
        """
        # Inheritance
        super(Process, self).__init__()

        # Intern identifiers
        self.name = self.__class__.__name__
        self.id = self.__class__.__module__ + "." + self.name

        # tools around the current process
        # TODO: remove it
        self.viewers = {}

        # Runtime information
        self.runtime = None

        # Log file name
        self.log_file = None

    def __call__(self, **kwargs):
        """ Execute the Process

        Keyword arguments may be passed to set parameters,
        to allow calling the process like a standard python function.
        In such case keyword arguments are set in the process in
        addition to those already set before the call.

        Parameters
        ----------
        kwargs
            should correspond to the declared parameter traits.

        Returns
        -------
        results:  ProcessResult object
            contains all execution information
        """
        # Get class
        process = self.__class__

        # Execution report
        runtime = {
            "start_time": datetime.isoformat(datetime.utcnow()),
            "cwd": os.getcwd(),
            "returncode": None,
            "environ": deepcopy(os.environ.data),
            "end_time": None,
            "hostname": getfqdn(),
        }

        # Set parameters
        if kwargs:
            user_traits = self.user_traits()
            for arg_name, arg_val in kwargs.iteritems():
                if arg_name not in user_traits:
                    raise TypeError("__call__ got an unexpected keyword "
                                    "argument '{0}'".foramt(arg_name))
                setattr(self, arg_name, arg_val)
            del user_traits

        # Call
        returncode = self._run_process()

        # End timer
        runtime["end_time"] = datetime.isoformat(datetime.utcnow())

        # Get dependencies' versions
        versions = {
            "capsul": get_tool_version("capsul"),
        }
        if "_nipype_interface" in dir(self):
            versions["nipype"] = get_tool_version("nipype")
            interface_name = self._nipype_interface.__module__.split(".")[2]
            versions[interface_name] = self._nipype_interface.version
        runtime["versions"] = versions

        # If run a Nipype process, get more informations
        if isinstance(returncode, InterfaceResult):
            process = returncode.interface
            if "cmd_line" in dir(returncode.runtime):
                runtime["cmd_line"] = returncode.runtime.cmdline
            runtime["stderr"] = returncode.runtime.stderr
            runtime["stdout"] = returncode.runtime.stdout
            runtime["cwd"] = returncode.runtime.cwd
            runtime["returncode"] = returncode.runtime.returncode
            outputs = dict(("_" + x[0],
                           self._nipype_interface._list_outputs()[x[0]])
                           for x in returncode.outputs.get().iteritems())
        else:
            outputs = self.get_outputs()

        # Result
        results = ProcessResult(process, runtime, self.get_inputs(),
                                outputs)

        return results

    ##############
    # Methods    #
    ##############

    def _run_process(self):
        """ Method that do the processings when the instance is called.

        Either this _run_process() or get_commandline() must be
        defined in derived classes.
        """
        # check if get_commandline() is specialized.
        # If yes, we can make use of it to execute the process
        if self.__class__.get_commandline != Process.get_commandline:
            commandline = self.get_commandline()
            subprocess.check_call(commandline)
        else:
            raise NotImplementedError(
                "Either get_commandline() or "
                "_run_process() should be redefined in "
                "a process ({0})".format(self.__class__.__name__))

    def get_commandline(self):
        """ Commandline representation of the process.

        Either this _run_process() or get_commandline() must be
        defined in derived classes.
        """
        def _is_defined(self, name):
            value = getattr(self, name)
            if (value is None or value is Undefined or
               (type(value) in types.StringTypes and value == "")):
                return False
            return True

        def _is_pathname(trait):
            return isinstance(trait.trait_type, File) \
                or isinstance(trait.trait_type, Directory)

        # Get command line defined arguments
        reserved_params = ('nodes_activation', 'selection_changed')
        args = [(name, _is_pathname(trait))
                for name, trait in self.user_traits().iteritems()
                if name not in reserved_params and _is_defined(self, name)]

        # Build the python call expression, keeping apart file names
        # file names are given separately since they might be modified
        # externally afterwards, typically to handle temporary files, or
        # file transfers with Soma-Workflow.
        argslist = [(name, getattr(self, name))
                    for name, is_pathname in args if not is_pathname]
        argsdict = dict(argslist)
        pathslist = [(name, getattr(self, name))
                     for name, is_pathname in args if is_pathname]
        pathsdict = dict(pathslist)

        module_name = sys.modules[self.__module__].__name__
        class_name = self.__class__.__name__
        commandline = [
            "python",
            "-c",
            ("import sys; from %s import %s; kwargs=%s; "
            "kwargs.update({sys.argv[i*2+1]: sys.argv[i*2+2] "
            "for i in xrange((len(sys.argv)-1)/2)}); %s()(**kwargs)")
            % (module_name, class_name, repr(argsdict), class_name)
        ] + sum([list(x) for x in pathsdict.items()], [])

        return commandline

    def save_log(self, returncode):
        """ Method to save process execution informations in json format

        If the class attribute `log_file` is not set, a log.json output
        file is generated in the process call current working directory.

        Parameters
        ----------
        returncode: ProcessResult
            the process reesult return code
        """
        # Access execution informations
        exec_info = self._get_log(returncode)

        # Generate output log file name if necessary
        if not self.log_file:
            self.log_file = os.path.join(exec_info["cwd"], "log.json")

        # Dump
        json_struct = unicode(json.dumps(exec_info, sort_keys=True,
                                         check_circular=True, indent=4))

        # Save Dump
        if self.log_file:
            f = open(self.log_file, 'w')
            print >> f, json_struct
            f.close()

    def get_log(self):
        """ Log the log file

        Returns
        -------
        log: dict
            the content of the log file
        """
        if os.path.isfile(self.log_file):
            with open(self.log_file) as json_file:
                return json.load(json_file)
        else:
            return None

    def add_trait(self, name, *trait):
        """ Add a new trait

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

    ##############
    # Properties #
    ##############

    def get_viewer(self, name):
        """ Get the viewer identified by name
        TODO: move
        """
        return self.viewers[name]

    def set_viewer(self, name, viewer_id, **kwargs):
        """ Create and set a viewer.
        TODO: move
        """
        self.viewers[name] = (viewer_id, kwargs)

    def get_input_spec(self):
        """ Method to access the process input specifications

        Returns
        -------
        outputs: str
            a string representation of all the input trait specifications
        """
        output = "\nINPUT SPECIFICATIONS\n\n"
        for trait_name, trait in self.user_traits().iteritems():
            if not trait.output:
                output += "{0}: {1}\n".format(
                    trait_name, trait_ids(self.trait(trait_name)))
        return output

    def get_output_spec(self):
        """ Method to access the process output specifications

        Returns
        -------
        outputs: str
            a string representation of all the output trait specifications
        """
        output = "\nOUTPUT SPECIFICATIONS\n\n"
        for trait_name, trait in self.user_traits().iteritems():
            if trait.output:
                output += "{0}: {1}\n".format(
                    trait_name, trait_ids(self.trait(trait_name)))
        return output

    def get_inputs(self):
        """ Method to access the process inputs

        Returns
        -------
        outputs: dict
            a dictionary with all the input trait names and values
        """
        output = {}
        for trait_name, trait in self.user_traits().iteritems():
            if not trait.output:
                output[trait_name] = getattr(self, trait_name)
        return output

    def get_outputs(self):
        """ Method to access the process outputs

        Returns
        -------
        outputs: dict
            a dictionary with all the output trait names and values
        """
        output = {}
        for trait_name, trait in self.user_traits().iteritems():
            if trait.output:
                output[trait_name] = getattr(self, trait_name)
        return output

    def set_parameter(self, name, value):
        """ Method to set the trait value of a process instance.

        Parameters
        ----------
        name: str (mandatory)
            the trait name we want to modify
        value: object (mandatory)
            the trait value we want to set
        """
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

    def _get_log(self, exec_info):
        """ Intern method to format process instance execution
        informations.

        Parameters
        ----------
        exec_info: dict (mandatory)
            the execution informations we want to format
            the dictionnary is supposed to contain a runtime attribute

        Returns
        -------
        log: dict
            formated execution informations
        """
        log = exec_info.runtime
        log["process"] = self.id
        log["inputs"] = exec_info.inputs.copy()
        log["outputs"] = exec_info.outputs.copy()

        # Need to take the representation of undefined input or outputs
        # traits
        for parameter_type in ["inputs", "outputs"]:
            for key, value in log[parameter_type].iteritems():
                if value is Undefined:
                    log[parameter_type][key] = repr(value)

        return log

    run = LateBindingProperty(
        _run_process, None, None,
        "Processing method that has to be defined in derived classes")


class NipypeProcess(Process):
    """ Dummy class to wrap nipype interfaces.
    """
    def __init__(self, nipype_instance, *args, **kwargs):
        """ Initialize the NipypeProcess class.

        NipypeProcess instances get automatically an additional user trait:
        "output_directory".

        Parameters
        ----------
        nipype_instance: nipype interface (mandatory)
            the nipype interface we want to wrap

        Attributes
        ----------
        _nipype_interface : interface
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

        # Some interface identification parameters
        self._nipype_interface = nipype_instance
        self._nipype_module = nipype_instance.__class__.__module__
        self._nipype_class = nipype_instance.__class__.__name__
        self._nipype_interface_name = self._nipype_module.split(".")[2]

        # Reset the process name and id
        self.id = ".".join([self._nipype_module, self._nipype_class])
        self.name = self._nipype_interface.__class__.__name__

        # Add trait to store processing output directory
        super(Process, self).add_trait("output_directory",
                                       Directory(Undefined,
                                       exists=True, optional=True))

        # For the nipype dcm2nii interface to work properly,
        # need to create attributes that will be modified by
        # the nipype run call
        if self._nipype_interface_name == "dcm2nii":
            self.output_files = _Undefined()
            self.reoriented_files = _Undefined()
            self.reoriented_and_cropped_files = _Undefined()
            self.bvecs = _Undefined()
            self.bvals = _Undefined()
        elif (self._nipype_interface_name == "fsl" and
                  self._nipype_class == "Split"):
            self._nipype_interface.inputs.dimension = "t"
        elif (self._nipype_interface_name == "fsl" and
                  self._nipype_class == "Merge"):
            self._nipype_interface.inputs.dimension = "t"

    def set_output_directory(self, out_dir):
        """ Set the process output directory

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
    """Object that contains the results of running a particular Process.

    Parameters
    ----------
    process : class type (mandatory)
        A copy of the `Process` class that was call to generate the result.
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

