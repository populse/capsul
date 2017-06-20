#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import sys
import os
import types
import logging
import traceback

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import Directory, CTrait, Undefined

# CAPSUL import
from soma.controller.trait_utils import trait_ids
from soma.controller.trait_utils import build_expression
from soma.controller.trait_utils import eval_trait

# Capsul import
from process import NipypeProcess


def nipype_factory(nipype_instance):
    """ From a nipype class instance generate dynamically a process
    instance that encapsulate the nipype instance.

    This function clone the nipye traits (also convert special traits) and
    conect the process and nipype instances traits.

    A new 'output_directory' nipype input trait is created.

    Since nipype inputs and outputs are separated and thus can have
    the same names, the nipype process outputs are prefixed with '_'.

    It also monkey patch some nipype functions in order to execute the
    process in a specific directory:
    the monkey patching has been written for Nipype version '0.9.2'.

    Parameters
    ----------
    nipype_instance : instance (mandatory)
        a nipype interface instance.

    Returns
    -------
    process_instance : instance
        a process instance.

    See Also
    --------
    _run_interface
    _list_outputs
    _gen_filename
    _parse_inputs
    relax_exists_constrain
    sync_nypipe_traits
    sync_process_output_traits
    clone_nipype_trait
    """

    ####################################################################
    # Monkey patching for Nipype version '0.9.2'.
    ####################################################################

    # Modify the nipype interface to dynamically update the working dir
    def _run_interface(self, runtime):
        """ Method to execute nipype interface.

        Parameters
        ----------
        runtime: Bunch (mandatory)
            the configuration structure
        """
        runtime.cwd = self.inputs.output_directory
        return self._run_interface_core(runtime)

    def _list_outputs(self):
        """ Method to list all the interface outputs.

        Returns
        -------
        outputs: dict
            all the interface outputs
        """
        # Get the outputs from the nipype method
        outputs = self._list_outputs_core()

        # Modify the output paths
        corrected_outputs = {}
        for trait_name, trait_value in outputs.iteritems():
            trait_desc = trait_ids(self.output_spec().trait(trait_name))
            if len(trait_desc) != 1:
                raise ValueError("Do not deal for the moment with Either "
                                 "nipype output traits.")
            corrected_outputs[trait_name] = self._modify_path(
                trait_value, trait_desc[0].split("_"))
        return corrected_outputs

    def _modify_path(self, item, trait_ids):
        """ Recursive method that will change file and directory path.

        Parameters
        ----------
        item: object
            a python object.
        trait_ids: list of str
            the trait string description to detect files and directories.

        Returns
        -------
        out: object
            the input object with modified files and directories.
        """
        if isinstance(item, list):
            out = [self._modify_path(subitem, trait_ids[1:]) for subitem in item]
        elif isinstance(item, dict):
            out = dict((key, self._modify_path(value, trait_ids[1:]))
                        for key, value in item.items())
        elif trait_ids[0] in ["File", "Directory"] and item is not Undefined:
            out = os.path.join(self.inputs.output_directory,
                               os.path.basename(item))
        else:
            out = item
        return out

    def _list_fsl_split_outputs(self):
        """ Method to list the fsl split interface outputs

        Returns
        -------
        outputs: dict
            all the interface outputs
        """
        from glob import glob
        from nipype.interfaces.fsl.base import Info
        from nipype.interfaces.base import isdefined

        # Get the nipype outputs
        outputs = self._outputs().get()

        # Modify the path outputs
        ext = Info.output_type_to_ext(self.inputs.output_type)
        outbase = 'vol*'
        if isdefined(self.inputs.out_base_name):
            outbase = '%s*' % self.inputs.out_base_name
        outputs['out_files'] = sorted(glob(
            os.path.join(self.inputs.output_directory, outbase + ext)))

        return outputs

    def _gen_filename(self, name):
        """ Method to generate automatically the output file name.

        Used by: nipype.interfaces.base.CommandLine._parse_inputs

        Returns
        -------
        outputs: str
            the generated output file name
        """
        # Get the nipype generated filename
        output = self._gen_filename_core(name)

        # Modify the path of this file
        if output:
            if os.path.isdir(output):
                corrected_output = self.inputs.output_directory
            else:
                corrected_output = os.path.join(self.inputs.output_directory,
                                                os.path.basename(output))

        return corrected_output

    def _parse_inputs(self, skip=None):
        """Parse all inputs using the ``argstr`` format string in the Trait.

        Any inputs that are assigned (not the default_value) are formatted
        to be added to the command line.

        Returns
        -------
        all_args : list
            A list of all inputs formatted for the command line.
        """
        # Reset input traits that has to be autogenerated
        #metadata = dict(argstr=lambda t: t is not None)
        #for name, spec in sorted(self.inputs.traits(**metadata).items()):
        #    if spec.genfile or spec.name_source:
        #        setattr(self.inputs, name, _Undefined())
        return self._parse_inputs_core()

    # Apply the monkey patching for Nipype version '0.9.2'.
    # The original nipype 'method' is stored in 'method_core' new method
    # Add an 'output_directory' nipype input trait.
    nipype_instance.inputs.add_trait(
        "output_directory", Directory(os.getcwd()))

    # Monkey patching: '_list_outputs'
    nipype_instance._list_outputs_core = nipype_instance._list_outputs
    # Special case for the fsl Split interface: use the redefined
    # '_list_fsl_split_outputs'
    if (nipype_instance.__class__.__module__.split(".")[2] == "fsl" and
       nipype_instance.__class__.__name__ == "Split"):
        nipype_instance._list_outputs = types.MethodType(
            _list_fsl_split_outputs, nipype_instance)
    # Standard case: use the redefined '_list_outputs'
    else:
        nipype_instance._list_outputs = types.MethodType(_list_outputs,
                                                         nipype_instance)
    nipype_instance._modify_path = types.MethodType(_modify_path,
                                                    nipype_instance)

    # Monkey patching: '_run_interface'
    nipype_instance._run_interface_core = nipype_instance._run_interface
    nipype_instance._run_interface = types.MethodType(_run_interface,
                                                      nipype_instance)

    # Monkey patching: '_parse_inputs'
    nipype_instance._parse_inputs_core = nipype_instance._parse_inputs
    nipype_instance._parse_inputs = types.MethodType(_parse_inputs,
                                                     nipype_instance)

    # Monkey patching: '_gen_filename'  for fsl and dcm2nii interface only
    if ("fsl" in nipype_instance.__class__.__module__ or
            "dcm2nii" in nipype_instance.__class__.__module__):
        nipype_instance._gen_filename_core = nipype_instance._gen_filename
        nipype_instance._gen_filename = types.MethodType(_gen_filename,
                                                         nipype_instance)

    # Create new instance derived from Process
    process_instance = NipypeProcess(nipype_instance)

    ####################################################################
    # Define functions to synchronized the process and interface traits
    ####################################################################

    def relax_exists_constrain(trait):
        """ Relax the exist constrain of a trait

        Parameters
        ----------
        trait: trait
            a trait that will be relaxed from the exist constrain
        """
        # If we have a single trait, just modify the 'exists' contrain
        # if specified
        if hasattr(trait.handler, "exists"):
            trait.handler.exists = False

        # If we have a selector, call the 'relax_exists_constrain' on each
        # selector inner components.
        main_id = trait.handler.__class__.__name__
        if main_id == "TraitCompound":
            for sub_trait in trait.handler.handlers:
                sub_c_trait = CTrait(0)
                sub_c_trait.handler = sub_trait
                relax_exists_constrain(sub_c_trait)
        elif len(trait.inner_traits) > 0:
            for sub_c_trait in trait.inner_traits:
                relax_exists_constrain(sub_c_trait)

    def sync_nypipe_traits(process_instance, name, old, value):
        """ Event handler function to update the nipype interface traits

        Parameters
        ----------
        process_instance: process instance (mandatory)
            the process instance that contain the nipype interface we want
            to update.
        name: str (mandatory)
            the name of the trait we want to update.
        old: type (manndatory)
            the old trait value
        new: type (manndatory)
            the new trait value
        """
        # Set the new nypipe interface value
        setattr(process_instance._nipype_interface.inputs, name,
                value)

    def sync_process_output_traits(process_instance, name, value):
        """ Event handler function to update the process instance outputs

        This callback is only called when an input process instance trait is
        modified.

        Parameters
        ----------
        process_instance: process instance (mandatory)
            the process instance that contain the nipype interface we want
            to update.
        name: str (mandatory)
            the name of the trait we want to update.
        value: type (manndatory)
            the old trait value
        """
        # Get all the input traits
        input_traits = process_instance.traits(output=False)

        # Try to update all the output process instance traits values when
        # a process instance input trait is modified.
        if name in input_traits:

            # Try to set all the process instance output traits values from
            # the nipype autocompleted traits values
            try:
                nipype_outputs = (process_instance.
                                  _nipype_interface._list_outputs())

                # Synchronize traits: check file existance
                for out_name, out_value in nipype_outputs.iteritems():

                    # Get trait type
                    trait_type = trait_ids(
                        process_instance._nipype_interface.output_spec().
                        trait(out_name))

                    # Set the output process trait value
                    # If we have a file check that the file exists before
                    # setting the new value
                    if (trait_type[0] is not "File" or
                       os.path.isfile(repr(out_value))):

                        process_instance.set_parameter(
                            "_" + out_name, out_value)

            # If we can't update the output process instance traits values,
            # print a logging debug message.
            except Exception:
                ex_type, ex, tb = sys.exc_info()
                logger.debug(
                    "Something wrong in the nipype output trait "
                    "synchronization:\n\n\tError: {0} - {1}\n"
                    "\tTraceback:\n{2}".format(
                        ex_type, ex, "".join(traceback.format_tb(tb))))

    ####################################################################
    # Clone nipype traits
    ####################################################################

    # The following function is not shared since it is too specific
    def clone_nipype_trait(nipype_trait):
        """ Create a new trait (cloned and converrted if necessary)
        from a nipype trait.

        Parameters
        ----------
        nipype_trait: trait
            the nipype trait we want to clone and convert if necessary.

        Returns
        -------
        process_trait: trait
            the cloned/converted trait that will be used in the process
            instance.
        """
        # Clone the nipype trait
        modules = set()
        expression = build_expression(nipype_trait, modules)
        process_trait = eval_trait(expression, modules)

        # Copy some information from the nipype trait
        process_trait.desc = nipype_trait.desc
        process_trait.optional = not nipype_trait.mandatory

        return process_trait

    # Add nipype traits to the process instance
    # > input traits
    for trait_name, trait in nipype_instance.input_spec().items():

        # Check if trait name already used in calss attributes:
        # For instance nipype.interfaces.fsl.FLIRT has a save_log bool input
        # trait.
        if hasattr(process_instance, trait_name):
            trait_name = "nipype_" + trait_name

        # Relax nipye exists trait contrain
        relax_exists_constrain(trait)

        # Clone the nipype trait
        process_trait = clone_nipype_trait(trait)

        # Add the cloned trait to the process instance
        process_instance.add_trait(trait_name, process_trait)

        # Need to copy all the nipype trait information
        process_instance.trait(trait_name).optional = not trait.mandatory
        process_instance.trait(trait_name).desc = trait.desc
        process_instance.trait(trait_name).output = False

        # Add the callback to update nipype traits when a process input
        # trait is modified
        process_instance.on_trait_change(sync_nypipe_traits, name=trait_name)

    # Syncronized also the output_directory input
    process_instance.on_trait_change(sync_nypipe_traits, name="output_directory")

    # Add callback to synchronize output process instance traits with nipype
    # autocompleted output traits
    process_instance.on_trait_change(sync_process_output_traits)

    # > output traits
    for trait_name, trait in nipype_instance.output_spec().items():

        # Clone the nipype trait
        process_trait = clone_nipype_trait(trait)

        # Create the output process trait name: nipype trait name prefixed
        # by '_'
        private_name = "_" + trait_name

        # Add the cloned trait to the process instance
        process_instance.add_trait(private_name, process_trait)

        # Need to copy all the nipype trait information
        process_instance.trait(private_name).optional = not trait.mandatory
        process_instance.trait(private_name).desc = trait.desc
        process_instance.trait(private_name).output = True
        process_instance.trait(private_name).enabled = False

    return process_instance
