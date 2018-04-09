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
import six

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import Directory, CTrait, Undefined, TraitError

# Soma import
from soma.controller.trait_utils import trait_ids

# Capsul import
from .process import NipypeProcess


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
    the monkey patching has been written for Nipype version '0.10.0'.

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

    # Change first level masking explicit in postscript
    def _make_matlab_command(self, content):
        from nipype.interfaces.spm import Level1Design
        return super(Level1Design, self)._make_matlab_command(
            content, postscript=None)
    if (nipype_instance.__class__.__module__.startswith('nipype.interfaces.spm.')
        and nipype_instance.__class__.__name__ == "Level1Design"):
        nipype_instance._make_matlab_command = types.MethodType(
            _make_matlab_command, nipype_instance)

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
        # a process instance input trait is modified or when the dedicated
        # 'synchronize' trait value is modified
        if name in input_traits or name == "synchronize":

            # Try to set all the process instance output traits values from
            # the nipype autocompleted traits values
            try:
                nipype_outputs = (process_instance.
                                  _nipype_interface._list_outputs())

                # Synchronize traits: check file existance
                for out_name, out_value in six.iteritems(nipype_outputs):

                    # Get trait type
                    trait_type = trait_ids(
                        process_instance._nipype_interface.output_spec().
                        trait(out_name))

                    # Set the output process trait value
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
    def clone_nipype_trait(process_instance, nipype_trait):
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
        process_trait = process_instance._clone_trait(nipype_trait)

        # Copy some information from the nipype trait
        process_trait.desc = nipype_trait.desc
        process_trait.optional = not nipype_trait.mandatory
        process_trait._metadata = {}
        
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
        process_trait = clone_nipype_trait(process_instance, trait)

        # Add the cloned trait to the process instance
        process_instance.add_trait(trait_name, process_trait)

        # Need to copy all the nipype trait information
        process_instance.trait(trait_name).optional = not trait.mandatory
        process_instance.trait(trait_name).desc = trait.desc
        process_instance.trait(trait_name).output = False

        # initialize value with nipype interface initial value, (if we can...)
        try:
            setattr(process_instance, trait_name,
                    getattr(nipype_instance.inputs, trait_name))
        except TraitError:
            # the value in the nipype trait is actually invalid...
            pass

        # Add the callback to update nipype traits when a process input
        # trait is modified
        process_instance.on_trait_change(sync_nypipe_traits, name=trait_name)

    # Add callback to synchronize output process instance traits with nipype
    # autocompleted output traits
    process_instance.on_trait_change(sync_process_output_traits)

    # > output traits
    for trait_name, trait in nipype_instance.output_spec().items():

        # Clone the nipype trait
        process_trait = clone_nipype_trait(process_instance,trait)

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
