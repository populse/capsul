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
import traits.api as traits
from traits.trait_base import _Undefined
from traits.api import Directory, CTrait

# Soma import
from soma.controller import trait_ids

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
    # In order to convert nipype special traits, we define a dict of
    # correspondances
    trait_cvt_table = {
        "InputMultiPath_TraitCompound": "List",
        "InputMultiPath": "List",
        "MultiPath": "List",
        "Dict_Str_Str": "DictStrStr",
        "OutputMultiPath_TraitCompound": "List",
        "OutputMultiPath": "List",
        "OutputList": "List"
    }

    ####################################################################
    # Monkey patching for Nipype version '0.9.2'.
    ####################################################################

    # Modify the nipype interface to dynamically update the working dir
    def _run_interface(self, runtime):
        """ Method to execute nipype interface

        Parameters
        ----------
        runtime: Bunch (mandatory)
            the configuration structure
        """
        runtime.cwd = self.inputs.output_directory
        return self._run_interface_core(runtime)

    def _list_outputs(self):
        """ Method to list all the interface outputs

        Returns
        -------
        outputs: dict
            all the interface outputs
        """
        # Get the outputs from the nipype method
        outputs = self._list_outputs_core()

        # Modify the path outputs
        corrected_outputs = {}
        for key, value in outputs.iteritems():
            if (not isinstance(value, _Undefined) and
               not isinstance(value, list)):

                corrected_outputs[key] = os.path.join(
                    self.inputs.output_directory,
                    os.path.basename(value))
            else:
                corrected_outputs[key] = value
        return corrected_outputs

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
        metadata = dict(argstr=lambda t: t is not None)
        for name, spec in sorted(self.inputs.traits(**metadata).items()):
            if spec.genfile or spec.name_source:
                setattr(self.inputs, name, _Undefined())
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

    # Monkey patching: '_run_interface'
    nipype_instance._run_interface_core = nipype_instance._run_interface
    nipype_instance._run_interface = types.MethodType(_run_interface,
                                                      nipype_instance)

    # Monkey patching: '_parse_inputs'
    nipype_instance._parse_inputs_core = nipype_instance._parse_inputs
    nipype_instance._parse_inputs = types.MethodType(_parse_inputs,
                                                     nipype_instance)

    # Monkey patching: '_gen_filename'  for fsl interface only
    if "fsl" in nipype_instance.__class__.__module__:
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
        if main_id == 'TraitCompound':
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

                # Synchronize traits: check if file existance
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
        # Get the nipype trait string description
        str_description = trait_ids(trait)

        # Normalize (convert) the description if necessary
        # For the moment do not create Either struct since it is not
        # considered in capuslview
        add_switch = False
        if "MultiPath" in str_description[0]:
            add_switch = False  # set to True to ceate a selector

        # Use the convertion table to normalize the trait description
        for old_str, new_str in trait_cvt_table.iteritems():
            for cnt in range(len(str_description)):
                str_description[cnt] = str_description[
                    cnt].replace(old_str, new_str)

        # If a selector structure is detected, update the string description
        # accordingly
        if add_switch:
            str_description = [
                str_description[0],
                "_".join(str_description[0].split("_")[1:])]

        # Create a new trait from its expression and namespace
        # Frist define the namespace were the expression will be executed
        namespace = {"traits": traits, "_Undefined": _Undefined,
                     "process_trait": None}

        # Build now the trait expressions
        trait_expressions = []

        # Go through all the string description items
        for trait_spec in str_description:

            # Get each atomic trait elements
            trait_spec = trait_spec.split("_")

            # Start building the current trait expression
            expression = ""

            # Go through all atomic trait elements
            for trait_item in trait_spec:

                # Standard case: add atomic trait description in the
                # expression
                expression += "traits.{0}(".format(trait_item)

                # Special case: Enum
                # Need to add enum values at the construction
                if trait_item == "Enum":
                    # Enum()
                    if (isinstance(trait.get_validate(), tuple) and
                       trait.get_validate()[0] == 5):

                        expression += "{0}".format(trait.get_validate()[1])

                    # List(Enum())
                    elif trait.handler.inner_traits():

                        inner_trait = trait.handler.inner_traits()[0]

                        if (isinstance(inner_trait.get_validate(), tuple)
                           and inner_trait.get_validate()[0] == 5):

                            expression += "{0}".format(
                                inner_trait.get_validate()[1])

                    # Either(Enum(),..)
                    else:
                        for inner_trait in trait.handler.handlers:
                            if inner_trait.values:
                                expression += "{0}".format(inner_trait.values)

                # Special case: Range
                # Need to add the lower and upper bounds
                if trait_item == "Range":
                    if isinstance(nipype_trait, traits.CTrait):
                        expression += "low={0},high={1}".format(
                            nipype_trait.handler._low,
                            nipype_trait.handler._high)
                    else:
                        expression += "low={0},high={1}".format(
                            nipype_trait._low,
                            nipype_trait._high)

                # Special case: File
                # Initialize the default file trait value to undefined
                if trait_item == "File":
                    expression += "_Undefined()"

            # Finalize the current expression and store it
            expression += ")" * len(trait_spec)
            trait_expressions.append(expression)

        # If we have multiple expression use a selector structure
        if len(trait_expressions) > 1:
            expression = "process_trait = traits.Either("
            for trait_expression in trait_expressions:
                expression += "{0}, ".format(trait_expression)
            expression += ")"
        # Otherwise
        else:
            expression = "process_trait = {0}".format(trait_expressions[0])

        # Evaluate the expression in the defined namespace
        def f():
            exec expression in namespace

        try:
            f()
        except:
            raise Exception(
                "Can't evaluate expression {0} in namespace {1}."
                "Please investigate: {2}.".format(
                    expression, namespace, sys.exc_info()[1]))

        # Get the evaluated traits
        process_trait = namespace["process_trait"]

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
