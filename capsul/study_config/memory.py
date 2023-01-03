# -*- coding: utf-8 -*-
'''
Memory caching. Probably mostly obsolete, this code is not much used now.

Classes
=======
:class:`UnMemorizedProcess`
---------------------------
:class:`MemorizedProcess`
-------------------------
:class:`CapsulResultEncoder`
----------------------------
:class:`Memory`
---------------

Functions
=========
:func:`get_process_signature`
-----------------------------
:func:`has_attribute`
---------------------
:func:`file_fingerprint`
------------------------
'''

# System import
from __future__ import with_statement
from __future__ import absolute_import
from __future__ import print_function
import os
import hashlib
import time
import shutil
import json
import logging
import six
import sys

# CAPSUL import
from capsul.process.process import Process, ProcessResult

# TRAITS import
from traits.api import Undefined


# Define the logger
logger = logging.getLogger(__name__)


###########################################################################
# Proxy process objects
###########################################################################

class UnMemorizedProcess(object):
    """ This class replaces MemorizedProcess when there is no cache.
    It provides an identical API but does not write anything on disk.
    """
    def __init__(self, process, verbose=1):
        """ Initialize the UnMemorizedProcess class.

        Parameters
        ----------
        process: capsul process
            the process instance to wrap.
        verbose: int
            if different from zero, print console messages.
        """
        self.process = process
        self.verbose = verbose

    def __call__(self, **kwargs):
        """ Call the process.

        .. note::
            matlab process input image headers are saved since matlab
            tools may modify image headers.

        Parameters
        ----------
        kwargs: dict (optional)
            should correspond to the declared process parameters.
        """
        # Set the process inputs early to get some argument checking
        for name, value in six.iteritems(kwargs):
            self.process.set_parameter(name, value)
        input_parameters = self._get_process_arguments()

        # Information message
        if self.verbose != 0:
            print("{0}\n[Process] Calling {1}...\n{2}".format(
                80 * "_", self.process.id,
                get_process_signature(self.process, input_parameters)))

        # Start a timer
        start_time = time.time()

        # Execute the process
        result = self.process()
        duration = time.time() - start_time

        # Information message
        if self.verbose != 0:
            msg = "{0:.1f}s, {1:.1f}min".format(duration, duration / 60.)
            print(max(0, (80 - len(msg))) * '_' + msg)

        return result

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
        for name, trait in six.iteritems(self.process.user_traits()):

            # Get the trait value
            value = self.process.get_parameter(name)

            # Split input and output traits
            is_input = True
            if "output" in trait.__dict__ and trait.output:
                is_input = False

            # Skip undefined trait attributes and outputs
            if is_input and value is not Undefined:

                # Store the input parameter
                input_parameters[name] = value

        return input_parameters

    def __getattr__(self, name):
        """ Define behavior for when a user attempts to access an attribute
        of a MemorizedProcess instance.

        First check the MemorizedProcess object and then the Process object.

        Parameters
        ----------
        name: string
            the name of the parameter we want to access.
        """
        if name in self.__dict__:
            super(UnMemorizedProcess, self).__getattr__(name)
        elif name in self.process.user_traits():
            return self.process.get_parameter(name)
        elif name in dir(self.process):
            return getattr(self.process, name)
        else:
            raise AttributeError(
                "'UnMemorizedProcess' and 'Process' objects have no attribute "
                "'{0}'".format(name))

    def __setattr__(self, name, value):
        """ Define behavior for when a user attempts to set an attribute
        of a MemorizedProcess instance.

        First check the MemorizedProcess object and then the Process object.

        Parameters
        ----------
        name: string
            the name of the parameter we want to set.
        value: object
            the parameter value.
        """
        if ("process" in self.__dict__ and
                name in self.__dict__["process"].__dict__):
            super(self.__dict__["process_class"],
                  self.__dict__["process"]).__setattr__(name, value)
        else:
            super(UnMemorizedProcess, self).__setattr__(name, value)

    def __repr__(self):
        """ ProcessFunc class representation.
        """
        return "{0}({1})".format(self.__class__.__name__, self.process.id)


class MemorizedProcess(object):
    """ Callable object decorating a capsul process for caching its return
    values each time it is called.

    All values are cached on the filesystem, in a deep directory
    structure. Methods are provided to inspect the cache or clean it.
    """

    def __init__(self, process, cachedir, timestamp=None, verbose=1):
        """ Initialize the MemorizedProcess class.

        Parameters
        ----------
        process: capsul process
            the process instance to wrap.
        cachedir: string
            the directory in which the computation will be stored
        timestamp: float (optional)
            The reference time from which times in tracing messages
            are reported.
        callback: callable (optional)
            an optional callable called each time after the function
            is called.
        verbose: int
            if different from zero, print console messages.
        """
        # Check the a process is passed
        self.process_class = process.__class__
        self.process = process
        if not (isinstance(self.process_class, object) and
                issubclass(self.process_class, Process)):
            raise ValueError(
                "The 'process' argument should be a capsul process class, "
                "but '{0}' (type '{1}') was passed.".format(
                    self.process_class, type(self.process_class)))

        # Check the memory directory
        cachedir = os.path.abspath(cachedir)
        if not os.path.exists(cachedir) and os.path.isdir(cachedir):
            raise ValueError("'base_dir' should be an existing directory.")
        self.cachedir = cachedir

        # Define the cache time
        if timestamp is None:
            timestamp = time.time()
        self.timestamp = timestamp

        # Set the documentation of the class
        self.__doc__ = self.process.get_help(returnhelp=True)

        # Store if some messages have to be displayed
        self.verbose = verbose

    def __call__(self, **kwargs):
        """ Call wrapped process and cache result, or read cache if
        available.

        This function returns the wrapped function output and some metadata.

        .. note::
            matlab process input image headers are saved since matlab
            tools may modify image headers.

        Parameters
        ----------
        kwargs: dict (optional)
            should correspond to the declared process parameters.
        """
        # Set the process inputs early to get some argument checking
        for name, value in six.iteritems(kwargs):
            self.process.set_parameter(name, value)

        # Create the destination folder and a unique id for the current
        # process
        process_dir, process_hash, input_parameters = self._get_process_id()

        # Execute the process
        if not os.path.isdir(process_dir):

            # Create the destination memory folder
            os.makedirs(process_dir)

            # Try to execute the process and if an error occurred remove the
            # cache folder
            try:
                # Run
                result = self._call_process(process_dir, input_parameters)

                # Save the result files in the memory with the corresponding
                # mapping
                output_parameters = {}
                for name, trait in self.process.traits(output=True).items():
                    # Get the trait value
                    value = self.process.get_parameter(name)
                    output_parameters[name] = value
                file_mapping = []
                self._copy_files_to_memory(output_parameters, process_dir,
                                           file_mapping)
                map_fname = os.path.join(process_dir, "file_mapping.json")
                with open(map_fname, "w") as open_file:
                    open_file.write(json.dumps(file_mapping))

            except Exception as e:  # noqa: E722
                print('error in MemorizedProcess.__call__:', e)
                shutil.rmtree(process_dir)
                raise

        # Restore the process results from the cache folder
        else:
            # Restore the memorized files
            map_fname = os.path.join(process_dir, "file_mapping.json")
            with open(map_fname, "r") as json_data:
                file_mapping = json.load(json_data)

            # Go through all mapping files
            for workspace_file, memory_file in file_mapping:

                # Determine if the workspace directory is writeable
                if os.access(os.path.dirname(workspace_file), os.W_OK):
                    shutil.copy2(memory_file, workspace_file)
                else:
                    logger.debug("Can't restore file '{0}', access rights are "
                                 "not sufficients.".format(workspace_file))

            # Update the process output traits
            result = self._load_process_result(process_dir, input_parameters)

        return result

    def _copy_files_to_memory(self, python_object, process_dir, file_mapping):
        """ Copy file items inside the memory.

        Parameters
        ----------
        python_object: object
            a generic python object.
        process_dir: str
            the process memory path.
        file_mapping: list of 2-uplet
            store in this structure the mapping between the workspace and the
            memory (workspace_file, memory_file).
        """
        # Deal with dictionary
        if isinstance(python_object, dict):
            for val in python_object.values():
                if val is not Undefined:
                    self._copy_files_to_memory(val, process_dir, file_mapping)

        # Deal with tuple and list
        elif isinstance(python_object, (list, tuple)):
            for val in python_object:
                if val is not Undefined:
                    self._copy_files_to_memory(val, process_dir, file_mapping)

        # Otherwise start the copy if the object is a file
        else:
            if (python_object is not Undefined and
                    isinstance(python_object, six.string_types) and
                    os.path.isfile(python_object)):
                fname = os.path.basename(python_object)
                out = os.path.join(process_dir, fname)
                shutil.copy2(python_object, out)
                file_mapping.append((python_object, out))

    def _call_process(self, process_dir, input_parameters):
        """ Call a process.

        Parameters
        ----------
        process_dir: string
            the directory where the cache has been written.
        input_parameters: dict
            the process input_parameters.

        Returns
        -------
        result: dict
            the process results.
        """
        # Information message
        if self.verbose != 0:
            print("{0}\n[Memory] Calling {1}...\n{2}".format(
                80 * "_", self.process.id,
                get_process_signature(self.process, input_parameters)))

        # Start a timer
        start_time = time.time()

        # Execute the process
        study_config = self.process.get_study_config()
        caching = getattr(study_config, 'use_smart_caching', None)
        # avoid recusrion
        study_config.use_smart_caching = False

        result = self.process()
        study_config.use_smart_caching = caching
        duration = time.time() - start_time

        # Save the result in json format
        cache = {'parameters': dict((i, getattr(self.process, i)) 
                                    for i in self.process.user_traits()),
                 'result': result}
        json_data = json.dumps(cache, sort_keys=True,
                               check_circular=True, indent=4,
                               cls=CapsulResultEncoder)
        result_fname = os.path.join(process_dir, "result.json")
        with open(result_fname, "w") as open_file:
            open_file.write(json_data)

        # Information message
        if self.verbose != 0:
            msg = "{0:.1f}s, {1:.1f}min".format(duration, duration / 60.)
            print(max(0, (80 - len(msg))) * '_' + msg)

        return result

    def _load_process_result(self, process_dir, input_parameters):
        """ Load the result of a process.

        Parameters
        ----------
        process_dir: string
            the directory where the cache has been written.
        input_parameters: dict
            the process input_parameters.

        Returns
        -------
        result: ProcessResult
            the process cached results.
        """
        # Display an information message
        if self.verbose != 0:
            print("[Memory]: Loading {0}...".format(
                get_process_signature(self.process, input_parameters)))

        # Load the process result
        result_fname = os.path.join(process_dir, "result.json")
        if not os.path.isfile(result_fname):
            raise KeyError(
                "Non-existing cache value (may have been cleared).\n"
                "File {0} does not exist.".format(result_fname))
        with open(result_fname, "r") as json_data:
            result_dict = json.load(json_data, cls=CapsulResultDecoder)


        ## Update the process output traits
        for name, value in six.iteritems(result_dict['parameters']):
            self.process.set_parameter(name, value)

        return result_dict['result']

    def _get_process_id(self, **kwargs):
        """ Return the directory in which are persisted the result of the
        process called with the given arguments.

        Returns
        -------
        process_dir: string
            the directory where the cache should be write.
        process_hash: string
            the process md5 hash.
        input_parameters: dict
            the process input_parameters.
        """
        # Get the process id
        process_hash, input_parameters = self._get_argument_hash()
        process_dir = os.path.join(self._get_process_dir(), process_hash)

        return process_dir, process_hash, input_parameters

    def _get_argument_hash(self):
        """ Get a hash of the process arguments.

        The user process traits are accessed through the user_traits()
        method that returns a sorted dictionary.

        Some parameters are not considered during the hash computation:
            * if the parameter value is not defined
            * if the corresponding trait has an attribute 'nohash'

        Add the tool versions to check roughly if the running codes have
        changed.

        Returns
        -------
        process_hash: string
            the process md5 hash.
        input_parameters: dict
            the process input_parameters.
        """
        # Store for input parameters
        input_parameters = {}

        # Go through all the user traits
        for name, trait in six.iteritems(self.process.user_traits()):

            # Get the trait value
            value = self.process.get_parameter(name)

            # Split input and output traits
            is_input = True
            if "output" in trait.__dict__ and trait.output:
                is_input = False

            # Skip undefined trait attributes and outputs
            if is_input and value is not Undefined:

                # Check specific flags before hash
                if has_attribute(trait, "nohash", attribute_value=True,
                                 recursive=True):
                    continue

                # Store the input parameter
                input_parameters[name] = value

        # Add the tool versions to check roughly if the running codes have
        # changed and add file path fingerprints
        process_parameters = input_parameters.copy()
        process_parameters = self._add_fingerprints(process_parameters)
        process_parameters["versions"] = self.process.versions

        # Generate the process hash
        hasher = hashlib.new("md5")
        hasher.update(json.dumps(process_parameters, sort_keys=True).encode())
        process_hash = hasher.hexdigest()

        return process_hash, input_parameters

    def _add_fingerprints(self, python_object):
        """ Add file path fingerprints.

        Parameters
        ----------
        python_object: object
            a generic python object.

        Returns
        -------
        out: object
            the input object with fingerprint-file representation.
        """
        # Deal with dictionary
        out = {}
        if isinstance(python_object, dict):
            for key, val in six.iteritems(python_object):
                if val is not Undefined:
                    out[key] = self._add_fingerprints(val)

        # Deal with tuple and list
        elif isinstance(python_object, (list, tuple)):
            out = []
            for val in python_object:
                if val is not Undefined:
                    out.append(self._add_fingerprints(val))
            if isinstance(python_object, tuple):
                out = tuple(out)

        # Otherwise start the deletion if the object is a file
        else:
            out = python_object
            if (python_object is not Undefined and
                    isinstance(python_object, six.string_types) and
                    os.path.isfile(python_object)):
                out = file_fingerprint(python_object)

        return out

    def _get_process_dir(self):
        """ Get the directory corresponding to the cache for the current
        process.

        Returns
        -------
        process_dir: string
            the directory where the cache should be write.
        """
        # Build the memory path from the process id
        path = [self.cachedir]
        path.extend(self.process.id.split("."))
        process_dir = os.path.join(*path)

        # Guarantee the path exists on the disk
        if not os.path.exists(process_dir):
            os.makedirs(process_dir)

        return process_dir

    def __repr__(self):
        """ ProcessFunc class representation.
        """
        return "{0}({1}, base_dir={2})".format(
            self.__class__.__name__, self.process.id, self.cachedir)

    def __getattr__(self, name):
        """ Define behavior for when a user attempts to access an attribute
        of a MemorizedProcess instance.

        First check the MemorizedProcess object and then the Process object.

        Parameters
        ----------
        name: string
            the name of the parameter we want to access.
        """
        if name in self.__dict__:
            super(MemorizedProcess, self).__getattr__(name)
        elif name in self.process.user_traits():
            return self.process.get_parameter(name)
        elif name in dir(self.process):
            return getattr(self.process, name)
        else:
            raise AttributeError(
                "'MemorizedProcess' and 'Process' objects have no attribute "
                "'{0}'".format(name))

    def __setattr__(self, name, value):
        """ Define behavior for when a user attempts to set an attribute
        of a MemorizedProcess instance.

        First check the MemorizedProcess object and then the Process object.

        Parameters
        ----------
        name: string
            the name of the parameter we want to set.
        value: object
            the parameter value.
        """
        if ("process" in self.__dict__ and
                name in self.__dict__["process"].__dict__):
            super(self.__dict__["process_class"],
                  self.__dict__["process"]).__setattr__(name, value)
        else:
            super(MemorizedProcess, self).__setattr__(name, value)


def get_process_signature(process, input_parameters):
    """ Generate the process signature.

    Parameters
    ----------
    process: Process
        a capsul process object
    input_parameters: dict
        the process input_parameters.

    Returns
    -------
    signature: string
        the process signature.
    """
    kwargs = ["{0}={1}".format(name, value)
              for name, value in six.iteritems(input_parameters)]
    return "{0}({1})".format(process.id, ", ".join(kwargs))


def has_attribute(trait, attribute_name, attribute_value=None,
                  recursive=True):
    """ Checks if a given trait has an attribute and optionally if it
    is set to particular value.

    Parameters
    ----------
    trait: Trait
        the input trait object.
    attribute_name: string
        the trait attribute name that will be checked.
    attribute_value: object (optional)
        the trait attribute axpected value.
    recursive: bool (optional, default True)
        check for the attribute in the inner traits.

    Returns
    -------
    res: bool
        True if input given trait has an attribute and optionally if it
        is set to a particular value.
    """
    # Count the number of trait having the target attribute
    count = 0

    # Check the current trait
    if (attribute_name in trait.__dict__ and
        (trait.__dict__[attribute_name] == attribute_value or
         attribute_value is None)):
            count += 1

    # Check the inner traits
    if recursive:
        if len(trait.inner_traits) > 0:
            for inner_trait in trait.inner_traits:
                count += has_attribute(inner_trait, attribute_name,
                                       attribute_value, recursive)

    return count > 0


def file_fingerprint(afile):
    """ Computes the file fingerprint.

    Do not consider the file content, just the fingerprint (ie. the mtime,
    the size and the file location).

    Parameters
    ----------
    afile: string
        the file to process.

    Returns
    -------
    fingerprint: tuple
        the file location, mtime and size.
    """
    fingerprint = {
        "name": afile,
        "mtime": None,
        "size": None
    }
    if os.path.isfile(afile):
        stat = os.stat(afile)
        fingerprint["size"] = str(stat.st_size)
        fingerprint["mtime"] = str(stat.st_mtime)
    return fingerprint


class CapsulResultEncoder(json.JSONEncoder):
    """ Deal with ProcessResult in json.
    """
    def default(self, obj):
        try:
            import numpy
        except ImportError:
            # numpy is not here
            numpy = None

        # File special case
        if isinstance(obj, ProcessResult):
            result_dict = {}
            for name in ["runtime", "returncode", "inputs",
                         "outputs"]:
                result_dict[name] = tuple_json_encoder(getattr(obj, name))
            return result_dict

        # Undefined parameter special case
        if isinstance(obj, Undefined.__class__):
            return "<undefined_trait_value>"

        # InterfaceResult special case
        # avoid explicitly loading nipype: it takes much time...
        nipype = sys.modules.get('nipype.interfaces.base')
        if nipype:
            InterfaceResult = getattr(nipype, 'InterfaceResult')
        else:
            class InterfaceResult(object):
                pass

        if isinstance(obj, InterfaceResult):
            return "<skip_nipype_interface_result>"

        # Array special case
        if numpy is not None and isinstance(obj, numpy.ndarray):
            return obj.tolist()

        # Call the base class default method
        return json.JSONEncoder.default(self, obj)


def tuple_json_encoder(obj):
    """ Encode a tuple in order to save it in json format.

    Parameters
    ----------
    obj: object
        a python object to encode.

    Returns
    -------
    encobj: object
        the encoded object.
    """
    if isinstance(obj, tuple):
        return {
            "__tuple__": True,
            "items": [tuple_json_encoder(item) for item in obj]
        }
    elif isinstance(obj, list):
        return [tuple_json_encoder(item) for item in obj]
    elif isinstance(obj, dict):
        return dict((tuple_json_encoder(key), tuple_json_encoder(value))
                    for key, value in six.iteritems(obj))
    else:
        return obj


class CapsulResultDecoder(json.JSONDecoder):
    """ Deal with ProcessResult in json.
    """
    def __init__(self, *args, **kargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_object, *args,
                                  **kargs)

    def object_object(self, obj):
        # Tuple special case
        if "__tuple__" in obj:
            return tuple(obj["items"])
        # Undefined parameter special case
        elif obj == "<undefined_trait_value>":
            return Undefined
        elif isinstance(obj, dict):
            for key, value in six.iteritems(obj):
                if value == "<undefined_trait_value>":
                    obj[key] = Undefined
            return obj
        # Default
        else:
            return obj


############################################################################
# Memory manager: provide some tracking about what is computed when, to
# be able to flush the disk
############################################################################

class Memory(object):
    """ Memory context to provide caching for processes.

    Attributes
    ----------
    `cachedir`: string
        the location for the caching. If None is given, no caching is done.

    Methods
    -------
    cache
    clear
    """

    def __init__(self, cachedir):
        """ Initialize the Memory class.

        Parameters
        ----------
        base_dir: string
            the directory name of the location for the caching.
        """
        # Build the capsul memory folder
        if cachedir is not None:
            cachedir = os.path.join(
                os.path.abspath(cachedir), "capsul_memory")
            if not os.path.exists(cachedir):
                os.makedirs(cachedir)
            elif not os.path.isdir(cachedir):
                raise ValueError("'base_dir' should be a directory")

        # Define class parameters
        self.cachedir = cachedir
        self.timestamp = time.time()

    def cache(self, process, verbose=1):
        """ Create a proxy of the given process in order to only execute
        the process for input parameters not cached on disk.

        Parameters
        ----------
        process: capsul process
            the capsul Process to be wrapped and cached.
        verbose: int
            if different from zero, print console messages.

        Returns
        -------
        proxy_process: MemorizedProcess object
            the returned object is a MemorizedProcess object, that behaves
            as a process object, but offers extra methods for cache lookup
            and management.

        Examples
        --------
        Create a temporary memory folder

        >>> from tempfile import mkdtemp
        >>> mem = Memory(mkdtemp())

        Here we create a callable that can be used to apply an
        fsl.Merge interface to files

        >>> from capsul.process import get_process_instance
        >>> nipype_fsl_merge = get_process_instance(
        ...    "nipype.interfaces.fsl.Merge")
        >>> fsl_merge = mem.cache(nipype_fsl_merge)

        Now we apply it to a list of files. We need to specify the
        list of input files and the dimension along which the files
        should be merged.

        >>> results = fsl_merge(in_files=['a.nii', 'b.nii'], dimension='t')

        We can retrieve the resulting file from the outputs:

        >>> results.outputs._merged_file
        """
        # If a proxy process is found get the encapsulated process
        if (isinstance(process, MemorizedProcess) or
                isinstance(process, UnMemorizedProcess)):
            process = process.process

        # If the cachedir is None no caching is done
        if self.cachedir is None:
            return UnMemorizedProcess(process, verbose)
        # Otherwise a proxy process is created
        else:
            return MemorizedProcess(process, self.cachedir, self.timestamp,
                                    verbose)

    def clear(self, skips=None):
        """ Remove all the cache apart from those given to the method
        input.

        Parameters
        ----------
        skips: list
            a list of path to keep during the cache deletion.
        """
        # Get all memory directories to remove
        to_remove_folders = []
        skips = skips or []
        for root, dirs, files in os.walk(self.cachedir):
            if "result.json" and files and dirs == [] and root not in skips:
                to_remove_folders.append(root)

        # Delete memory directories
        for folder in to_remove_folders:
            shutil.rmtree(folder)

    def __repr__(self):
        """ Memory class representation.
        """
        return "{0}(cachedir={1})".format(self.__class__.__name__,
                                          self.cachedir)
