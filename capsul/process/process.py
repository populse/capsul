# -*- coding: utf-8 -*-
''' Process main class and infrastructure

Classes
-------

.. currentmodule:: capsul.process.process

:class:`Process`
++++++++++++++++
:class:`FileCopyProcess`
++++++++++++++++++++++++
:class:`InteractiveProcess`
+++++++++++++++++++++++++++
:class:`NipypeProcess`
++++++++++++++++++++++
:class:`ProcessMeta`
++++++++++++++++++++
:class:`ProcessResult`
++++++++++++++++++++++

'''

# System import
from __future__ import print_function
from __future__ import absolute_import
import os
import operator
from socket import getfqdn
from datetime import datetime as datetime
from copy import deepcopy
import json
import soma.subprocess
import logging
import shutil
import six
import sys
import functools
import glob
import tempfile
import traceback

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import Directory, Undefined, Int, List, Bool, File
from traits.api import BaseTraitHandler

# Soma import
from soma.controller import Controller
from soma.controller import trait_ids
from soma.controller.trait_utils import is_trait_value_defined
from soma.controller.trait_utils import is_trait_pathname
from soma.controller.trait_utils import get_trait_desc
from soma.utils import json_utils

# Capsul import
from capsul.utils.version_utils import get_tool_version


class ProcessMeta(Controller.__class__):
    """ Class used to complete a process docstring

    Use a class and not a function for inheritance.
    """
    @staticmethod
    def complement_doc(name, docstr):
        """ complement the process docstring
        """
        docstring = docstr.split("\n")

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

        return "\n".join(docstring)

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
            a dictionary with the class attributes.
        """
        # Update the class docstring with the full process help
        docstring = ProcessMeta.complement_doc(
            name, attrs.get("__doc__", ""))
        attrs["__doc__"] = docstring

        # Find all traits definitions in the process class and ensure that
        # it has a boolean value for attributes "output" and "optional".
        # If no value is given at construction, False will be used.
        for n, possible_trait_definition in six.iteritems(attrs):
            if isinstance(possible_trait_definition, BaseTraitHandler):
                possible_trait_definition._metadata['output'] \
                    = bool(possible_trait_definition.output)
                possible_trait_definition._metadata['optional'] \
                    = bool(possible_trait_definition.optional)

        return super(ProcessMeta, mcls).__new__(
            mcls, name, bases, attrs)


class Process(six.with_metaclass(ProcessMeta, Controller)):
    """ A process is an atomic component that contains a processing.

    A process is typically an object with typed parameters, and an execution
    function. Parameters are described using Enthought
    `traits <http://docs.enthought.com/traits/>`_ through Soma-Base
    :somabase:`Controller <api.html#soma.controller.controller.Controller>`
    base class.

    In addition to describing its parameters, a Process must implement its
    execution function, either through a python method, by overloading
    :meth:`_run_process`, or through a commandline execution, by overloading
    :meth:`get_commandline`. The second way allows to run on a remote
    processing machine which has not necessary capsul, nor python, installed.

    Parameters are declared or queried using the traits API, and their values
    are in the process instance variables:

    ::

        from __future__ import print_function
        from capsul.api import Process
        import traits.api as traits

        class MyProcess(Process):

            # a class trait
            param1 = traits.Str('def_param1')

            def __init__(self):
                super(MyProcess, self).__init__()
                # declare an input param
                self.add_trait('param2', traits.Int())
                # declare an output param
                self.add_trait('out_param', traits.File(output=True))

            def _run_process(self):
                with open(self.out_param, 'w') as f:
                    print('param1:', self.param1, file=f)
                    print('param2:', self.param2, file=f)

        # run it with parameters
        MyProcess()(param2=12, out_param='/tmp/log.txt')

    **Note about the File and Directory traits**

    The :class:`~traits.trait_types.File` trait type represents a file
    parameter. A file is actually two things: a filename (string), and the file itself (on the filesystem). For an input it is OK not to distinguish them, but for an output, there are two different cases:

    * the file (on the filesystem) is an output, but the filename (string) is
      given as an input: this is the classical "commandline" behavior, when we
      tell the program where it should write its output file.
    * the file is an output, and the filename is also an output: this is rather a
      "function return value" behavior: the process determines internally where
      it should write the file, and tells as an output where it did.

    To distinguish these two cases, in Capsul we normally add in the
    :class:`~traits.trait_types.File` or :class:`~traits.trait_types.Directory`
    trait a property ``input_filename`` which is True when the filename is an
    input, and False when the filename is an output::

        self.add_trait('out_file',
                       traits.File(output=True, input_filename=False))

    However as most of our processes are based on the "commandline behavior"
    (the filename is an input) and we often forget to specify the
    ``input_filename`` parameter, the default is the "filename is an input"
    behavior, when not specified.

    **Attributes**

    Attributes
    ----------
    name: str
        the class name.
    id: str
        the string description of the class location (ie., module.class).
    log_file: str (default None)
        if None, the log will be generated in the current directory
        otherwise it will be written in log_file path.
    """

    def __init__(self, **kwargs):
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
        self.study_config = None

        default_values = getattr(self, 'default_values', None)
        if default_values:
            self.default_values = default_values.copy()
        else:
            self.default_values = {}
        for k, v in six.iteritems(kwargs):
            self.default_values[k] = v

    def __getstate__(self):
        """ Remove the _weakref attribute eventually set by 
        soma.utils.weak_proxy because it prevent Process instance
        from being used with pickle.
        """
        state = super(Process, self).__getstate__()
        state.pop('_weakref', None)
        state.pop('_user_traits', None)
        state.pop('__doc__', None)
        state.pop('study_config', None)
        return state
    
    def add_trait(self, name, trait):
        """Ensure that trait.output and trait.optional are set to a
        boolean value before calling parent class add_trait.
        """
        if not "_metadata" in trait.__dict__:
            trait._metadata = {}
        if trait._metadata is not None:
            trait._metadata['output'] = bool(trait.output)
            trait._metadata['optional'] = bool(trait.optional)
        else:
            trait.output = bool(trait.output)
            trait.optional = bool(trait.optional)
        super(Process, self).add_trait(name, trait)
        
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

        .. note:

            This method should **not** be overloaded by Process subclasses to
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
        # Execute the process
        returncode = self.get_study_config().run(self, **kwargs)
        return returncode


    def run(self, **kwargs):
        '''
        Obsolete: use self.__call__ instead
        '''
        return self.__call__(**kwargs)

    
    ####################################################################
    # Private methods
    ####################################################################

    def _run_process(self):
        """Runs the processings when the instance is called.

        Either this _run_process() or :meth:`get_commandline` must be
        defined in derived classes.

        Note that _run_process() is called as a python function, on a Process
        instance. When using remote processing (cluster for instance), this
        means that the commandline which will run needs to be able to re-
        instantiate the same process: the process thus has to be stored in a
        file or python module which can be accessed from the remote machine,
        and python / capsul correctly installed and available on it.

        :meth:`get_commandline` at the contrary, can implement commandlines
        which are completely inependent from Capsul, and from python.

        .. note::

            If both methods are not defined in the derived class a
            NotImplementedError error is raised.

            On the other side, if both methods are overloaded, the process
            behavior in local sequential computing mode and in Soma-Workflow
            modes may be different.
        """
        # Check if get_commandline() method is specialized
        # If yes, we can make use of it to execute the process
        if self.__class__.get_commandline != Process.get_commandline:
            commandline = self.get_commandline()
            soma.subprocess.check_call(commandline)

        # Otherwise raise an error
        else:
            raise NotImplementedError(
                "Either get_commandline() or _run_process() should be "
                "redefined in process ({0})".format(
                    self.__class__.__name__))
    
    def _before_run_process(self):
        """This method is called by StudyConfig.run() before calling
        _run_process(). By default it does nothing but can be overridden
        in derived classes.
        """
        pass

    def _after_run_process(self, run_process_result):
        """This method is called by StudyConfig.run() after calling
        _run_process(). It is expected to return the final result of the
        process. By default it does nothing but can be overridden
        in derived classes.
        """
        return run_process_result
        

    def _get_log(self, exec_info):
        """ Method that generate the logging structure from the execution
        information and class attributes.

        Parameters
        ----------
        exec_info: dict (mandatory)
            the execution information,
            the dictionary is supposed to contain a runtime attribute.

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
            for key, value in six.iteritems(log[parameter_type]):
                if value is Undefined:
                    log[parameter_type][key] = repr(value)

        return log

    def _rst_table(self, data):
        """ Create a rst formatted table.

        Parameters
        ----------
        data: list of list of str (mandatory)
            the table line-cell centent.

        Returns
        -------
        rsttable: list of str
            the rst formatted table containing the input data.
        """
        # Output rst table
        rsttable = []

        for table_row in data:
            for index, cell_row in enumerate(table_row):
                # > set the parameter name in bold
                if index == 0 and ":" in cell_row:
                    delimiter_index = cell_row.index(":")
                    cell_row = ("**" + cell_row[:delimiter_index] + "**" +
                                cell_row[delimiter_index:])
                rsttable.append(cell_row)

        ## Get the size of the largest row in order to
        ## format properly the rst table (do not forget the '+' and '*')
        #row_widths = [len(item)
                      #for item in functools.reduce(operator.add, data)]
        #width = max(row_widths) + 11

        ## Generate the rst table

        ## > table synthax
        #rsttable.append("+" + "-" * width + "+")
        ## > go through the table lines
        #for table_row in data:
            ## > go through the cell lines
            #for index, cell_row in enumerate(table_row):
                ## > set the parameter name in bold
                #if index == 0 and ":" in cell_row:
                    #delimiter_index = cell_row.index(":")
                    #cell_row = ("**" + cell_row[:delimiter_index] + "**" +
                                #cell_row[delimiter_index:])
                ## >  add table rst content
                #rsttable.append(
                    #"| | {0}".format(cell_row) +
                    #" " * (width - len(cell_row) - 3) +
                    #"|")
            ## > close cell
            #rsttable.append("+" + "-" * width + "+")

        return rsttable

    ####################################################################
    # Public methods
    ####################################################################

    def save_log(self, returncode):
        """ Method to save process execution information in json format.

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
            f.write(six.text_type(json_struct))

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
        """ Method to generate a commandline representation of the process.

        If not implemented, it will generate a commandline running python,
        instaitiating the current process, and calling its
        :meth:`_run_process` method.

        Returns
        -------
        commandline: list of strings
            Arguments are in separate elements of the list.
        """
        # Get command line arguments (ie., the process user traits)
        # Build the python call expression, keeping apart file names.
        # File names are given separately since they might be modified
        # externally afterwards, typically to handle temporary files, or
        # file transfers with Soma-Workflow.

        class ArgPicker(object):
            """ This small object is only here to have a __repr__() representation which will print sys.argv[n] in a list when writing the commandline code.
            """
            def __init__(self, num):
                self.num = num
            def __repr__(self):
                return 'sys.argv[%d]' % self.num

        reserved_params = ("nodes_activation", "selection_changed")
        # pathslist is for files referenced from lists: a list of files will
        # look like [sys.argv[5], sys.argv[6]...], then the corresponding
        # path args will be in additional arguments, here stored in pathslist
        pathslist = []
        # argsdict is the dict of non-path arguments, and will be printed
        # using repr()
        argsdict = {}
        # pathsdict is the dict of path arguments, and will be printed as a
        # series of arg_name, path_value, all in separate commandline arguments
        pathsdict = {}

        for trait_name, trait in six.iteritems(self.user_traits()):
            value = getattr(self, trait_name)
            if trait_name in reserved_params \
                    or not is_trait_value_defined(value):
                continue
            if is_trait_pathname(trait):
                pathsdict[trait_name] = value
            elif isinstance(trait.trait_type, List) \
                    and is_trait_pathname(trait.inner_traits[0]):
                plist = []
                for pathname in value:
                    if is_trait_value_defined(pathname):
                        plist.append(ArgPicker(len(pathslist) + 1))
                        pathslist.append(pathname)
                    else:
                        plist.append(pathname)
                argsdict[trait_name] = plist
            else:
                argsdict[trait_name] = value

        # Get the module and class names
        if hasattr(self, '_function'):
            # function with xml decorator
            module_name = self._function.__module__
            class_name = self._function.__name__
            call_name = class_name
        else:
            module_name = self.__class__.__module__
            class_name = self.name
            call_name = '%s()' % class_name

        # Construct the command line
        python_command = os.path.basename(sys.executable)
        commandline = [
            python_command,
            "-c",
            ("import sys; from {0} import {1}; kwargs={2}; "
             "kwargs.update(dict((sys.argv[i * 2 + {3}], "
             "sys.argv[i * 2 + {4}]) "
             "for i in range(int((len(sys.argv) - {3}) / 2)))); "
             "{5}(**kwargs)").format(module_name, class_name,
                                       repr(argsdict), len(pathslist) + 1,
                                       len(pathslist) + 2,
                                       call_name).replace("'", '"')
        ] + pathslist + sum([list(x) for x in pathsdict.items()], [])

        return commandline

    def params_to_command(self):
        '''
        Generates a commandline representation of the process.

        If not implemented, it will generate a commandline running python,
        instaitiating the current process, and calling its
        :meth:`_run_process` method.

        This methood is new in Capsul v3 and is a replacement for
        :meth:`get_commandline`.

        It can be overwritten by custom Process subclasses. Actually each
        process should overwrite either :meth:`params_to_command` or
        :meth:`_run_process`.

        The returned commandline is a list, which first element is a "method",
        and others are the actual commandline with arguments. There are several
        methods, the process is free to use either of the supported ones,
        depending on how the execution is implemented.

        **Methods:**

        `capsul_job`: Capsul process run in python
            The command will run the :meth:`_run_process` execution method of
            the process, after loading input parameters from a JSON dictionary
            file. The only second element in the commandline list is the
            process identifier (module/class as in
            :meth:`~capsul.engine.CapsulEngine.get_process_instance`). The
            location of the JSON file will be passed to the job execution
            through an environment variable `SOMAWF_INPUT_PARAMS`::

                return ['capsul_job', 'morphologist.capsul.morphologist']

        `format_string`: free commandline with replacements for parameters
            Command arguments can be, or contain, format strings in the shape
            `'%(param)s'`, where `param` is a parameter of the process. This
            way we can map values correctly, and call a foreign command::

                return ['format_string', 'ls', '%(input_dir)s']

        `json_job`: free commandline with JSON file for input parameters
            A bit like `capsul_job` but without the automatic wrapper::

                return ['json_job', 'python', '-m', 'my_module']

        Returns
        -------
        commandline: list of strings
            Arguments are in separate elements of the list.
        '''
        if self.__class__.get_commandline != Process.get_commandline:
            # get_commandline is overridden the old way: use it.
            return ['format_string'] + self.get_commandline()
        return ['capsul_job', self.id]

    def make_commandline_argument(self, *args):
        """This helper function may be used to build non-trivial commandline
        arguments in get_commandline implementations.
        Basically it concatenates arguments, but it also takes care of keeping
        track of temporary file objects (if any), and converts non-string
        arguments to strings (using repr()).

        Ex:

        >>> process.make_commandline_argument('param=', self.param)

        will return the same as:

        >>> 'param=' + self.param

        if self.param is a string (file name) or a temporary path.
        """
        built_arg = ""
        temp = None
        for arg in args:
            if hasattr(arg, 'pattern'): # tempfile
                built_arg = built_arg + arg
            elif isinstance(arg, six.string_types):
                built_arg += arg
            else:
                built_arg = built_arg + repr(arg)
        return built_arg

    @staticmethod
    def run_from_commandline(process_definition):
        '''
        Run a process from a commandline call. The process name (with module)
        are given in argument, input parameters should be passed through a JSON
        file which location is in the ``SOMAWF_INPUT_PARAMS`` environment
        variable.

        If the process has outputs, the ``SOMAWF_OUTUT_PARAMS`` environment
        variable should contain the location of an output file which will be
        written with a dict containing output parameters values.
        '''
        from capsul.engine import capsul_engine

        ce = capsul_engine()

        param_file = os.environ.get('SOMAWF_INPUT_PARAMS')

        # fix expandvars problem when the env var SOMAWF_OUTPUT_PARAMS is
        # defined from a script and passed into a container (like bv set
        # through soma-workflow config using "$SOMAWF_OUTPUT_PARAMS"): when the
        # "source" variable is not set, os.expandvars() leaves the value
        # "$SOMAWF_OUTPUT_PARAMS" untouched, but here we would expect an empty
        # variable
        if param_file in ('$SOMAWF_INPUT_PARAMS', '${SOMAWF_INPUT_PARAMS}'):
            param_file = None

        if not param_file:
            print('Warning: no input parameters, the env variable '
                  'SOMAWF_INPUT_PARAMS is not set.', file=sys.stderr)
            params_conf = {}
        else:
            with open(param_file) as f:
                params_conf = json_utils.from_json(json.load(f))

        configuration = params_conf.get('configuration_dict')
        if configuration:
            # activation will be re-done during run() but some global configs
            # (nipype SPM/Matlab settings) need to be done before any process
            # is instantiated, so we must do it earlier, right now.

            # clear activations for now.
            from capsul import engine
            engine.activated_modules = set()
            engine.activate_configuration(configuration)

        params = params_conf.get('parameters', {})
        ## filter out undefined values -- maybe this is not OK in all cases:
        ## we may want to manually reset a parameter, but in normal cases,
        ## Undefined values are just not set, which means that the values are
        ## left to defaults depending on the global config: nipype works like
        ## this for matlab parameters.
        #params = dict([(k, v) for k, v in params.items()
                       #if v is not Undefined])

        process = ce.get_process_instance(process_definition)
        try:
            process.import_from_dict(params)
        except Exception as e:
            print('error in setting parameters of process %s, with dict:'
                  % process.name, params, file=sys.stderr)
            raise
        # actually run the process
        ce.study_config.use_soma_workflow = False
        result = ce.study_config.run(process, configuration_dict=configuration)
        # collect output parameers
        out_param_file = os.environ.get('SOMAWF_OUTPUT_PARAMS')

        # fix expandvars problem when the env var SOMAWF_OUTPUT_PARAMS is
        # defined from a script and passed into a container (like bv set
        # through soma-workflow config using "$SOMAWF_OUTPUT_PARAMS"): when the
        # "source" variable is not set, os.expandvars() leaves the value
        # "$SOMAWF_OUTPUT_PARAMS" untouched, but here we would expect an empty
        # variable
        if out_param_file in ('$SOMAWF_OUTPUT_PARAMS',
                              '${SOMAWF_OUTPUT_PARAMS}'):
            out_param_file = None

        output_params = {}
        if out_param_file:
            if result is None:
                result = {}
            reserved_params = ("nodes_activation", "selection_changed")
            for param, trait in six.iteritems(process.user_traits()):
                if param in reserved_params or not trait.output:
                    continue
                if isinstance(trait.trait_type, (File, Directory)) \
                        and trait.input_filename is not False:
                    continue
                elif isinstance(trait.trait_type, List) \
                        and isinstance(trait.inner_traits[0].trait_type,
                                       (File, Directory)) \
                        and trait.inner_traits[0].trait_type.input_filename \
                            is not False \
                        and trait.input_filename is not False:
                    continue
                output_params[param] = getattr(process, param)
            output_params.update(result)
            with open(out_param_file, 'w') as f:
                json.dump(json_utils.to_json(output_params), f)

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
        for trait_name, trait in six.iteritems(self.user_traits()):
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
        for trait_name, trait in six.iteritems(self.traits(output=True)):
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
        for trait_name, trait in six.iteritems(self.user_traits()):
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
        for trait_name, trait in six.iteritems(self.traits(output=True)):
            output[trait_name] = getattr(self, trait_name)
        return output

    def get_help(self, returnhelp=False, use_labels=False):
        """ Generate description of a process parameters.

        Parameters
        ----------
        returnhelp: bool (optional, default False)
            if True return the help string message formatted in rst,
            otherwise display the raw help string message on the console.
        use_labels: bool
            if True, input and output sections will get a RestructuredText
            label to avoid ambiguities.
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
        if use_labels:
            in_label = ['.. _%s.%s_inputs:\n\n' % (self.__module__, self.name)]
            out_label = ['.. _%s.%s_outputs:\n\n'
                         % (self.__module__, self.name)]
        else:
            in_label = []
            out_label = []
        full_help = (doctring + in_label + self.get_input_help(returnhelp)
                     + [""] + out_label
                     + self.get_output_help(returnhelp) + [""])
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
            if True generate a rst table with the input descriptions.

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
        mandatory_items = [x for x in six.iteritems(self.user_traits())
                           if not x[1].output and not x[1].optional]
        #mandatory_items.update(self.traits(output=None, optional=False))

        # If we have mandatory inputs, get the corresponding string
        # descriptions
        data = []
        if mandatory_items:
            for trait_name, trait in mandatory_items:
                trait_desc = get_trait_desc(trait_name, trait,
                                            use_wrap=not rst_formating)
                data.append(trait_desc)

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                manhelpstr += self._rst_table(data)
            # Otherwise
            else:
                manhelpstr += functools.reduce(operator.add, data)

        # Markup to separate optional inputs
        opthelpstr = ["", "[Optional]", ""]

        # Get all optional input traits
        optional_items = [x for x in six.iteritems(self.user_traits())
                          if not x[1].output and x[1].optional]
        #optional_items = self.traits(output=False, optional=True)
        #optional_items.update(self.traits(output=None, optional=True))

        # If we have optional inputs, get the corresponding string
        # descriptions
        data = []
        if optional_items:
            for trait_name, trait in optional_items:
                data.append(
                    get_trait_desc(trait_name, trait,
                                   use_wrap=not rst_formating))

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                opthelpstr += self._rst_table(data)
            # Otherwise
            else:
                opthelpstr += functools.reduce(operator.add, data)

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
            if True generate a rst table with the input descriptions.

        Returns
        -------
        helpstr: str
            the trait output help descriptions
        """
        # Generate an output section
        helpstr = ["Outputs", "~" * 7, ""]

        # Get all the process output traits, keep their order
        items = [(name, trait)
                 for name, trait in six.iteritems(self.user_traits())
                 if trait.output]

        # If we have no output trait, return no string description
        if not items:
            return [""]

        # If we have some outputs, get the corresponding string
        # descriptions
        data = []
        for trait_name, trait in items:
            data.append(
                get_trait_desc(trait_name, trait, use_wrap=not rst_formating))

        # If we want to format the output nicely (rst)
        if data != []:
            if rst_formating:
                helpstr += self._rst_table(data)
            # Otherwise
            else:
                helpstr += functools.reduce(operator.add, data)

        return helpstr

    def set_parameter(self, name, value, protected=None):
        """ Method to set a process instance trait value.

        For File and Directory traits the None value is replaced by the
        special Undefined trait value.

        Parameters
        ----------
        name: str (mandatory)
            the trait name we want to modify
        value: object (mandatory)
            the trait value we want to set
        protected: None or bool (tristate)
            if True or False, force the "protected" status of the plug. If None,
            keep it as is.
        """
        # The None trait value is Undefined, do the replacement
        if value is None:
            value = Undefined

        if protected is not None:
            self.protect_parameter(name, protected)
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

    def get_study_config(self):
        ''' Get (or create) the StudyConfig this process belongs to
        '''
        if self.study_config is None:
            # Import cannot be done on module due to circular dependencies
            from capsul.study_config.study_config import default_study_config
            self.set_study_config(default_study_config())
        return self.study_config

    def set_study_config(self, study_config):
        ''' Set a StudyConfig for the process.
        Note that it can only be done once: once a non-null StudyConfig has
        been assigned to the process, it should not change.
        '''
        if self.study_config is not None \
                and self.study_config is not study_config:
            raise ValueError("A StudyConfig had already been set in the "
                             "process %s. It cannot be changed afterwards."
                             % self.name)
        self.study_config = study_config

    def get_missing_mandatory_parameters(self):
        ''' Returns a list of parameters which are not optional, and which
        value is Undefined or None, or an empty string for a File or
        Directory parameter.
        '''
        def check_trait(trait, value):
            if trait.optional:
                return True
            if hasattr(trait, 'inner_traits') and len(trait.inner_traits) != 0:
                if value is Undefined:
                    return bool(trait.output)
                for i, item in enumerate(value):
                    j = min(i, len(trait.inner_traits) - 1)
                    if not check_trait(trait.inner_traits[j], item):
                        return False
                return True
            if isinstance(trait.trait_type, (File, Directory)):
                if trait.output and trait.input_filename is False:
                    # filename is an output
                    return True
                return value not in (Undefined, None, '')
            return trait.output or value not in (Undefined, None)

        missing = []
        for name, trait in six.iteritems(self.user_traits()):
            if not trait.optional:
                value = self.get_parameter(name)
                if not check_trait(trait, value):
                    missing.append(name)
        return missing

    def requirements(self):
        '''
        Requirements needed to run the process. It is a dictionary which keys are config/settings modules and values are requests for them.

        The default implementation returns an empty dict (no requirements), and
        should be overloaded by processes which actually have requirements.

        Ex::

            {'spm': 'version >= "12" and standalone == "True"')
        '''
        return {}

    def check_requirements(self, environment='global', message_list=None):
        '''
        Checks the process requirements against configuration settings values
        in the attached CapsulEngine. This makes use of the
        :meth:`requirements` method and checks that there is one matching
        config value for each required module.

        Parameters
        ----------
        environment: str
            config environment id. Normally corresponds to the computing
            resource name, and defaults to "global".
        message_list: list
            if not None, this list will be updated with messages for
            unsatisfied requirements, in order to present the user with an
            understandable error.

        Returns
        -------
        config: dict, list, or None
            if None is returned, requirements are not met: the process cannot
            run. If a dict is returned, it corresponds to the matching config
            values. When no requirements are needed, an empty dict is returned.
            A pipeline, if its requirements are met will return a list of
            configuration values, because different nodes may require different
            config values.
        '''
        settings = self.get_study_config().engine.settings
        req = self.requirements()
        config = settings.select_configurations(environment, uses=req)
        success = True
        for module in req:
            module_name = settings.module_name(module)
            if module_name not in config and message_list is not None:
                message_list.append('requirement: %s is not met in %s'
                                    % (req, self.name))
                success = False
            elif module_name not in config:
                # if no message is expected, then we can return immediately
                # without checking further requirements. Otherwise we
                # continue to get a full list of unsatisfied requirements.
                print('requirement:', req, 'not met in', self.name)
                print('config:', settings.select_configurations(environment))
                return None
        if success:
            return config
        else:
            return None


class FileCopyProcess(Process):
    """ A specific process that copies all the input files.

    Attributes
    ----------
    copied_inputs : dict
        the list of copied file parameters {param: dst_value}
    copied_files: dict
        copied files {param: [dst_value1, ...]}

    Methods
    -------
    __call__
    _update_input_traits
    _get_process_arguments
    _copy_input_files
    """
    def __init__(self, activate_copy=True, inputs_to_copy=None,
                 inputs_to_clean=None, destination=None,
                 inputs_to_symlink=None, use_temp_output_dir=False):
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
            processing. If None, all copied files will be cleaned.
        destination: str (optional default None)
            where the files are copied.
            If None, the output directory will be used, unless
            use_temp_output_dir is set.
        inputs_to_symlink: list of str (optional, default None)
            as inputs_to_copy, but for files which should be symlinked
        use_temp_output_dir: bool
            if True, the output_directory parameter is set to a temp one during
            execution, then outputs are copied / moved / hardlinked to the
            final location. This is useful when several parallel jobs are
            working in the same directory and may write the same intermediate
            files (SPM does this a lot).
        """
        # Inheritance
        super(FileCopyProcess, self).__init__()

        # Class parameters
        self.activate_copy = activate_copy
        self.destination = destination
        if self.activate_copy:
            self.inputs_to_clean = inputs_to_clean
            if inputs_to_symlink is None:
                self.inputs_to_symlink = list(self.user_traits().keys())
            else:
                self.inputs_to_symlink = inputs_to_symlink
            if inputs_to_copy is None:
                self.inputs_to_copy = [k for k in self.user_traits().keys()
                                       if k not in self.inputs_to_symlink]
            else:
                self.inputs_to_copy = inputs_to_copy
                self.inputs_to_symlink = [k for k in self.inputs_to_symlink
                                          if k not in self.inputs_to_copy]
            self.copied_inputs = None
            self.copied_files = None
        self.use_temp_output_dir = use_temp_output_dir

    def _before_run_process(self):
        """ Method to copy files before executing the process.
        """
        super(FileCopyProcess, self)._before_run_process()

        if self.destination is None:
            output_directory = getattr(self, 'output_directory', None)
            if output_directory in (None, Undefined, ''):
                output_directory = None
            if self.use_temp_output_dir:
                workspace = tempfile.mkdtemp(dir=output_directory,
                                             prefix=self.name)
                destdir = workspace
            else:
                destdir = output_directory
        else:
            destdir = self.destination
        if not destdir:
            raise ValueError('FileCopyProcess cannot be used without a '
                             'destination directory')
        self._destination = destdir
        output_directory = self.destination
        if output_directory is None:
            output_directory = getattr(self, 'output_directory', None)
        if output_directory not in (None, Undefined, ''):
            self._former_output_directory = output_directory
            self.output_directory = destdir

        # The copy option is activated
        if self.activate_copy:

            # Copy the desired items
            self._update_input_traits()

            self._recorded_params = {}
            # Set the process inputs
            for name, value in six.iteritems(self.copied_inputs):
                self._recorded_params[name] = getattr(self, name)
                self.set_parameter(name, value)

    def _after_run_process(self, run_process_result):
        """ Method to clean-up temporary workspace after process
        execution.
        """
        run_process_result = super(FileCopyProcess, self)._after_run_process(
            run_process_result)
        if self.use_temp_output_dir:
            self._move_outputs()
        # The copy option is activated
        if self.activate_copy:
            # Clean the workspace
            self._clean_workspace()

        # restore initial values, keeping outputs
        # The situation here is that:
        # * output_directory should drive "final" output values
        # * we may have been using a temporary output directory, thus output
        #   values are already set to this temp dir, not the final one.
        #   (at least when use_temp_output_dir is set).
        #   -> _move_outputs() already changes these output values
        # * when we reset inputs, outputs are reset to values pointing to
        #   the input directory (via nipype callbacks).
        # So we must:
        # 1. record output values
        # 2. set again inputs to their initial values (pointing to the input
        #    directories). Outputs will be reset accordingly to input dirs.
        # 3. force output values using the recorded ones.

        # 1. record output values
        outputs = {}
        for name, trait in six.iteritems(self.user_traits()):
            if trait.output:
                outputs[name] = getattr(self, name)
        # 2. set again inputs to their initial values
        if hasattr(self, '_recorded_params'):
            for name, value in six.iteritems(self._recorded_params):
                self.set_parameter(name, value)
        # 3. force output values using the recorded ones
        for name, value in six.iteritems(outputs):
            self.set_parameter(name, value)
        if hasattr(self, '_recorded_params'):
            del self._recorded_params

        return run_process_result

    def _clean_workspace(self):
        """ Removed some copied inputs that can be deleted at the end of the
        processing.
        """
        inputs_to_clean = self.inputs_to_clean
        if inputs_to_clean is None:
            # clean all copied inputs
            inputs_to_clean = list(self.copied_files.keys())
        for to_rm_name in inputs_to_clean:
            rm_files = self.copied_files.get(to_rm_name, [])
            if rm_files:
                self._rm_files(rm_files)
                del self.copied_files[to_rm_name]
                del self.copied_inputs[to_rm_name]

    def _move_outputs(self):
        tmp_output = self._destination
        dst_output = self._former_output_directory
        output_values = {}
        moved_dict = {}
        for param, trait in six.iteritems(self.user_traits()):
            if trait.output:
                new_value = self._move_files(tmp_output, dst_output,
                                             getattr(self, param),
                                             moved_dict=moved_dict)
                output_values[param] = new_value
                self.set_parameter(param, new_value)

        shutil.rmtree(tmp_output)
        del self._destination
        self.destination = self._former_output_directory
        if hasattr(self, 'output_directory'):
            self.output_directory = self._former_output_directory
        del self._former_output_directory
        return output_values

    def _move_files(self, src_directory, dst_directory, value, moved_dict={}):
        if isinstance(value, (list, tuple)):
            new_value = [self._move_files(src_directory, dst_directory, item,
                                          moved_dict)
                         for item in value]
            if isinstance(value, tuple):
                return tuple(new_value)
            return new_value
        elif isinstance(value, dict):
            new_value = {}
            for name, item in six.iteritems(value):
                new_value[name] = self._move_files(
                    src_directory, dst_directory, item, moved_dict)
            return new_value
        elif isinstance(value, six.string_types):
            if value in moved_dict:
                return moved_dict[value]
            if os.path.dirname(value) == src_directory \
                    and os.path.exists(value):
                name = os.path.basename(value).split('.')[0]
                matfnames = glob.glob(os.path.join(
                    os.path.dirname(value), name + ".*"))
                todo = [x for x in matfnames if x != value]
                dst = os.path.join(dst_directory, os.path.basename(value))
                if os.path.exists(dst) or os.path.islink(dst):
                    print('warning: file or directory %s exists' % dst)
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.unlink(dst)
                try:
                    # print('moving:', value, 'to:', dst)
                    shutil.move(value, dst)
                except Exception as e:
                    print(e, file=sys.stderr)
                moved_dict[value] = dst
                for item in todo:
                    self._move_files(src_directory, dst_directory, item,
                                     moved_dict)
                return dst
        return value

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
            if (isinstance(python_object, six.string_types) and
                    os.path.isfile(python_object)):
                os.remove(python_object)

    def _update_input_traits(self, copy=True):
        """ Update the process input traits: input files are copied.
        """
        # Get the new trait values
        input_parameters, input_symlinks = self._get_process_arguments()
        self.copied_files = {}
        self.copied_inputs \
            = self._copy_input_files(input_parameters, False,
                                     self.copied_files, copy=copy)
        self.copied_inputs.update(
            self._copy_input_files(input_symlinks, True, self.copied_files,
                                   copy=copy))

    def _copy_input_files(self, python_object, use_symlink=True,
                          files_list=None, copy=True):
        """ Recursive method that copy the input process files.

        Parameters
        ----------
        python_object: object
            a generic python object.
        use_symlink: bool
            if True, symbolic links will be make instead of full copies, on
            systems which support symlinks. Much faster and less disk consuming
            than full copies, but might have side effects in programs which
            detect and handle symlinks in a different way.
        files_list: list or dict
            if provided, this *output* parameter will be updated with the list
            of files actually created.
        copy: bool
            if False, files are not actually copied/symlinked but filenames are
            generated

        Returns
        -------
        out: object
            the copied-file input object.
        """
        if sys.platform.startswith('win') and sys.version_info[0] < 3:
            # on windows, no symlinks (in python2 at least).
            use_symlink = False

        # Deal with dictionary
        # Create an output dict that will contain the copied file locations
        # and the other values
        if isinstance(python_object, dict):
            out = {}
            for key, val in python_object.items():
                if val is not Undefined:
                    if isinstance(files_list, dict):
                        sub_files_list = files_list.setdefault(key, [])
                    else:
                        sub_files_list = files_list
                    out[key] = self._copy_input_files(val, use_symlink,
                                                      sub_files_list,
                                                      copy=copy)

        # Deal with tuple and list
        # Create an output list or tuple that will contain the copied file
        # locations and the other values
        elif isinstance(python_object, (list, tuple)):
            out = []
            for val in python_object:
                if val is not Undefined:
                    out.append(self._copy_input_files(val, use_symlink,
                                                      files_list, copy=copy))
            if isinstance(python_object, tuple):
                out = tuple(out)

        # Otherwise start the copy (with metadata cp -p) if the object is
        # a file
        else:
            out = python_object
            if (python_object is not Undefined and
                    isinstance(python_object, six.string_types) and
                    os.path.isfile(python_object)):
                destdir = self._destination
                if not os.path.exists(destdir):
                    os.makedirs(destdir)
                fname = os.path.basename(python_object)
                out = os.path.join(destdir, fname)
                if out == python_object:
                    return out  # input=output, nothing to do
                if copy:
                    if os.path.exists(out) or os.path.islink(out):
                        if os.path.isdir(out):
                            shutil.rmtree(out)
                        else:
                            os.unlink(out)
                    if use_symlink:
                        os.symlink(python_object, out)
                    else:
                        shutil.copy2(python_object, out)
                    if files_list is not None:
                        files_list.append(out)

                    # Copy associated .mat/.json/.minf files
                    name = fname.rsplit(".", 1)[0]
                    matfnames = glob.glob(os.path.join(
                        os.path.dirname(python_object), name + ".*"))
                    for matfname in matfnames:
                        extrafname = os.path.basename(matfname)
                        extraout = os.path.join(destdir, extrafname)
                        if extraout != out:
                            if os.path.exists(extraout) \
                                    or os.path.islink(extraout):
                                if os.path.isdir(extraout):
                                    shutil.rmtree(extraout)
                                else:
                                    os.unlink(extraout)
                            if use_symlink:
                                os.symlink(matfname, extraout)
                            else:
                                shutil.copy2(matfname, extraout)
                            if files_list is not None:
                                files_list.append(extraout)

        return out

    def _get_process_arguments(self):
        """ Get the process arguments.

        The user process traits are accessed through the user_traits()
        method that returns a sorted dictionary.

        Returns
        -------
        input_parameters: dict
            the process input parameters that should be copied.
        input_symlinks: dict
            the process input parameters that should be symlinked.
        """
        # Store for input parameters
        input_parameters = {}
        input_symlinks = {}

        # Go through all the user traits
        for name, trait in six.iteritems(self.user_traits()):
            if trait.output:
                continue
            # Check if the target parameter is in the check list
            c = name in self.inputs_to_copy
            s = name in self.inputs_to_symlink
            if c or s:
                # Get the trait value
                value = self.get_parameter(name)
                # Skip undefined trait attributes and outputs
                if value is not Undefined:
                    # Store the input parameter
                    if c:
                        input_parameters[name] = value
                    else:
                        input_symlinks[name] = value

        return input_parameters, input_symlinks


class NipypeProcess(FileCopyProcess):
    """ Base class used to wrap nipype interfaces.
    """

    def __new__(cls, *args, **kwargs):

        def init_with_skip(self, *args, **kwargs):

            cls = self.__init__.cls
            init_att = '__%s_np_init_done__' % cls.__name__
            if hasattr(self, init_att) and getattr(self, init_att):
                # may be called twice, from within __new__ or from python
                # internals
                return

            setattr(self, init_att, True)
            super(cls, self).__init__(*args, **kwargs)

        if cls.__init__ is cls.__base__.__init__ and cls is not NipypeProcess:
            # we must setup a conditional __init__ for each specialized class
            cls.__init__ = init_with_skip
            init_with_skip.cls = cls

        # determine if we were called from within nipype_factory()
        stack = traceback.extract_stack()
        # stack[-1] should be here
        # stack[-2] may be nipype_factory
        if len(stack) >= 2:
            s2 = stack[-2]
            if s2[2] == 'nipype_factory':
                instance = super(NipypeProcess, cls).__new__(cls, *args,
                                                            **kwargs)
                setattr(instance, '__%s_np_init_done__' % cls.__name__, False)
                return instance
        nipype_class = getattr(cls, '_nipype_class_type', None)
        nargs = args
        nkwargs = kwargs
        arg0 = None
        if nipype_class is not None:
            arg0 = nipype_class()
        else:
            if 'nipype_class' in kwargs:
                arg0 = kwargs['nipype_class']()
                nkwargs = {k: v for k, v in kwargs if k != 'nipype_class'}
            elif 'nipype_instance' in kwargs:
                pass
            elif len(args) != 0:
                import nipype.interfaces.base
                if isinstance(args[0], nipype.interfaces.base.BaseInterface):
                    arg0 = args[0]
                    nargs = nargs[1:]
                elif issubclass(args[0], nipype.interfaces.base.BaseInterface):
                    arg0 = args[0]()
                    nargs = args[1:]
        if arg0 is not None:
            from .nipype_process import nipype_factory
            instance = nipype_factory(arg0, base_class=cls, *nargs, **nkwargs)
            if cls != NipypeProcess:
                # override direct nipype reference
                instance.id = instance.__class__.__module__ + "." \
                    + instance.name
            instance.__postinit__(*nargs, **nkwargs)
        else:
            instance = super(NipypeProcess, cls).__new__(cls, *args, **kwargs)
            setattr(instance, '__%s_np_init_done__' % cls.__name__, False)
        return instance


    def __init__(self, nipype_instance=None, use_temp_output_dir=None,
                 *args, **kwargs):
        """ Initialize the NipypeProcess class.

        NipypeProcess instance gets automatically an additional user trait
        'output_directory'.

        This class also fix also some lacks of the nipye version '0.10.0'.

        NipypeProcess is normally not instantiated directly, but through the
        CapsulEngine factory, using a nipype interface name::

            ce = capsul_engine()
            npproc = ce.get_process_instance('nipype.interfaces.spm.Smooth')

        However it is now still possible to instantiate it directly, using a
        nipype interface class or instance::

            npproc = NipypeProcess(nipype.interfaces.spm.Smooth)

        NipypeProcess may be subclassed for specialized interfaces. In such a
        case, the subclass may provide:

        * (optionally) a class attribute `_nipype_class_type` to specify the
        nipype interface class. If present the nipype interface class or
        instance will not be specified in the constructor call.
        * (optionally) a :meth:`__postinit__` method which will be called in
        addition to the constructor, but later once the instance is correctly
        setup. This `__postinit__` method allows to customize the new class
        instance.
        * (optionally) a class attribute `_nipype_trait_mapping`: a dict
        specifying a translation table between nipype traits names and the
        names they will get in the Process instance. By default inputs get the
        same name as in their nipype interface, and outputs are prefixed with
        an underscore ('_') to avoid names collisions when a trait exists both
        in inputs and outputs in nipype. A special trait name
        `_spm_script_file` is also used in SPM interfaces to write the matlab
        script. It can also be translated to a different name in this dict.

        Subclasses should preferably *not* define an __init__ method, because
        it may be called twice if no precaution is taken to avoid it (a
        `__np_init_done__` instance attribute is set once init is done the
        first time).

        Ex::

            class Smooth(NipypeProcess):
                _nipype_class_type = spm.Smooth
                _nipype_trait_mapping = {
                    'smoothed_files': 'smoothed_files',
                    '_spm_script_file': 'spm_script_file'}

            smooth = Smooth()

        Parameters
        ----------
        nipype_instance: nipype interface (mandatory, except from internals)
            the nipype interface we want to wrap in capsul.
        use_temp_output_dir: bool or None
            use a temp working directory during processing

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
        if hasattr(self, '__NipypeProcess_np_init_done__') \
                and self.__NipypeProcess_np_init_done__:
            # may be called twice, from within __new__ or from python internals
            return

        self.__NipypeProcess_np_init_done__ = True
        #super(NipypeProcess, self).__init__(*args, **kwargs)

        # Set some class attributes that characterize the nipype interface
        if nipype_instance is None:
            # probably called from a specialized subclass
            np_class = getattr(self, '_nipype_class_type', None)
            if np_class:
                nipype_instance = np_class()
            else:
                raise TypeError(
                    'NipypeProcess.__init__ must either be called with a '
                    'nipye interface instance as 1st argument, or from a '
                    'specialized subclass providing the _nipype_class_type '
                    'class attribute')
        self._nipype_interface = nipype_instance
        self._nipype_module = nipype_instance.__class__.__module__
        self._nipype_class = nipype_instance.__class__.__name__
        msplit = self._nipype_module.split(".")
        if len(msplit) > 2:
            self._nipype_interface_name = msplit[2]
        else:
            self._nipype_interface_name = 'custom'

        # Inheritance: activate input files copy for spm interfaces.
        if self._nipype_interface_name == "spm":
            # Copy only 'copyfile' nipype traits
            inputs_to_copy = list(self._nipype_interface.inputs.traits(
                copyfile=True).keys())
            inputs_to_symlink = list(self._nipype_interface.inputs.traits(
                copyfile=False).keys())
            out_traits = self._nipype_interface.output_spec().traits()
            inputs_to_clean = [x for x in inputs_to_copy
                               if 'modified_%s' % x not in out_traits]
            if use_temp_output_dir is None:
                use_temp_output_dir = True
            super(NipypeProcess, self).__init__(
                activate_copy=True, inputs_to_copy=inputs_to_copy,
                inputs_to_symlink=inputs_to_symlink,
                inputs_to_clean=inputs_to_clean,
                use_temp_output_dir=use_temp_output_dir,
                *args, **kwargs)
        else:
            if use_temp_output_dir is None:
                use_temp_output_dir = False
            super(NipypeProcess, self).__init__(
                  activate_copy=False, use_temp_output_dir=use_temp_output_dir,
                  *args, **kwargs)

        # Replace the process name and identification attributes
        self.id = ".".join([self._nipype_module, self._nipype_class])
        self.name = self._nipype_interface.__class__.__name__

        # Add a new trait to store the processing output directory
        super(Process, self).add_trait(
            "output_directory", Directory(Undefined, exists=True,
                                          optional=True))

        # Add a 'synchronize' nipype input trait that will be used to trigger
        # manually the output nipype/capsul traits sync.
        super(Process, self).add_trait("synchronize", Int(0, optional=True))

        # use the nipype doc for help
        doc = getattr(nipype_instance, '__doc__')
        if doc:
            self.__doc__ = doc


    def __postinit__(self, *args, **kwargs):
        '''
        `__postinit__` allows to customize subclasses. the base `NipypeProcess`
        implementation does nothing, it is empty.
        '''
        pass


    def requirements(self):
        req = {'nipype': 'any'}
        if self._nipype_interface_name == "spm":
            req['spm'] = 'any'
        elif self._nipype_interface_name == "fsl":
            req['fsl'] = 'any'
        elif self._nipype_interface_name == "freesurfer":
            req['freesurfer'] = 'any'
        return req


    def set_output_directory(self, out_dir):
        """ Set the process output directory.

        Parameters
        ----------
        out_dir: str (mandatory)
            the output directory
        """
        self.output_directory = out_dir

    def set_usedefault(self, parameter, value):
        """ Set the value of the usedefault attribute on a given parameter.

        Parameters
        ----------
        parameter: str (mandatory)
            name of the parameter to modify.
        value: bool (mandatory)
            value set to the usedefault attribute
        """
        setattr(self._nipype_interface.inputs, parameter, value)

    def _before_run_process(self):
        if self._nipype_interface_name == "spm":
            # Set the spm working
            self.destination = None
        super(NipypeProcess, self)._before_run_process()
        # configure nipype from config env variables (which should have been set
        # before now)
        from capsul.in_context import nipype as inp_npp
        inp_npp.configure_all()

    def _run_process(self):
        """ Method that do the processings when the instance is called.

        Returns
        -------
        runtime: InterfaceResult
            object containing the running results
        """
        try:
            cwd = os.getcwd()
        except OSError:
            cwd = None
        if self.output_directory is None or self.output_directory is Undefined:
            raise ValueError('output_directory is not set but is mandatory '
                             'to run a NipypeProcess')
        os.chdir(self.output_directory)
        self.synchronize += 1

        trait_map = getattr(self, '_nipype_trait_mapping', {})
        # Force nipype update
        for trait_name in self._nipype_interface.inputs.traits().keys():
            capsul_name = trait_map.get(trait_name, trait_name)
            if capsul_name in self.user_traits():
                old = getattr(self._nipype_interface.inputs, trait_name)
                new = getattr(self, capsul_name)
                if old is Undefined and old != new:
                    setattr(self._nipype_interface.inputs, trait_name, new)

        results = self._nipype_interface.run()
        self.synchronize += 1

        # update outputs from nipype
        for trait_name \
                in self._nipype_interface.output_spec().traits().keys():
            capsul_name = trait_map.get(trait_name, trait_name)
            if capsul_name in self.user_traits():
                old = getattr(self, capsul_name)
                new = getattr(self._nipype_interface.output_spec(),
                              trait_name)
                if old != new:
                    setattr(self, capsul_name, new)

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

        # Restore cwd
        if cwd is not None:
            os.chdir(cwd)

        #return results.__dict__
        return None

    def _after_run_process(self, run_process_result):
        trait_map = getattr(self, '_nipype_trait_mapping', {})
        script_tname = trait_map.get('_spm_script_file', '_spm_script_file')
        if getattr(self, script_tname, None) not in (None, Undefined, ''):
            script_file = os.path.join(
                self.output_directory,
                self._nipype_interface.mlab.inputs.script_file)
            if os.path.exists(script_file):
                shutil.move(script_file, getattr(self, script_tname))
        return super(NipypeProcess,
                     self)._after_run_process(run_process_result)

    @classmethod
    def help(cls, nipype_interface, returnhelp=False):
        """ Method to print the full wrapped nipype interface help.

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

class InteractiveProcess(Process):
    '''
    Base class for interactive processes. The value of the is_interactive 
    parameter determine if either the process can be run in background
    (eventually remotely) as a standardl process (is_interactive = False)
    or if the process must be executed interactively in the user environment
    (is_interactive = False).
    '''
    is_interactive = Bool(False)

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
