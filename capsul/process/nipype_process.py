# -*- coding: utf-8 -*-
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Utilities to link Capsul and NiPype interfaces

Functions
---------
:func:`nipype_factory`
++++++++++++++++++++++
'''

# System import
from __future__ import print_function
from __future__ import absolute_import
from soma.controller.trait_utils import relax_exists_constraint
from soma.controller import trait_ids
import sys
import os
import types
import logging
import six

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
from traits.api import Directory, File, List, CTrait, Undefined, TraitError

# Capsul import
from .process import NipypeProcess


def nipype_factory(nipype_instance, base_class=NipypeProcess):
    """ From a nipype class instance generate dynamically a process
    instance that encapsulate the nipype instance.

    This function clones the nipye traits (also convert special traits) and
    connects the process and nipype instances traits.

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
    if (nipype_instance.__class__.__module__.startswith(
            'nipype.interfaces.spm.')
        and nipype_instance.__class__.__name__ == "Level1Design"):
        nipype_instance._make_matlab_command = types.MethodType(
            _make_matlab_command, nipype_instance)

    # Create new instance derived from Process
    if hasattr(base_class, '_nipype_class_type'):
        process_instance = base_class()
    else:
        process_instance = base_class(nipype_instance)

    ####################################################################
    # Define functions to synchronized the process and interface traits
    ####################################################################

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
        trait_map = getattr(process_instance, '_nipype_trait_mapping', {})
        inames = [iname for iname, pname in trait_map.items() if pname == name]
        if inames:
            name = inames[0]

        if name.startswith("nipype_"):
            setattr(process_instance._nipype_interface.inputs,
                    name[7:],
                    value)

        else:
            setattr(process_instance._nipype_interface.inputs,
                    name,
                    value)

    def _replace_dir(value, directory):
        """ Replace directory in filename(s) in value.

        value may be a string, or a list
        """
        if value in (None, Undefined, ""):
            return value
        if isinstance(value, list):
            value = [_replace_dir(x, directory) for x in value]
        else:
            value = os.path.join(directory, os.path.basename(value))
        return value

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
        value: type (mandatory)
            the old trait value
        """
        # Get all the input traits
        input_traits = process_instance.traits(output=False)
        output_directory \
            = getattr(process_instance, 'output_directory', Undefined)

        # get the interface name from the process trait name
        trait_map = getattr(process_instance, '_nipype_trait_mapping', {})

        # Try to update all the output process instance traits values when
        # a process instance input trait is modified or when the dedicated
        # 'synchronize' trait value is modified
        if name in input_traits or name in ("synchronize", 'output_directory'):

            # Try to set all the process instance output traits values from
            # the nipype autocompleted traits values
            try:
                nipype_outputs = (process_instance.
                                  _nipype_interface._list_outputs())
            except Exception as e:
                # don't make it all crash because of a nipype trait assign
                # error
                print('EXCEPTION:', e, file=sys.stderr)
                print('while syncing nipype parameter', name,
                      'on', process_instance.name, file=sys.stderr)
                # when called during exit, the traceback module might have
                # already disappeared
                import traceback
                traceback.print_exc()
                ex_type, ex, tb = sys.exc_info()
                logger.debug(
                    "Something wrong in the nipype output trait "
                    "synchronization:\n\n\tError: {0} - {1}\n"
                    "\tTraceback:\n{2}".format(
                        ex_type, ex, "".join(traceback.format_tb(tb))))
                nipype_outputs = {}

            # Synchronize traits: check file existence
            for out_name, out_value in six.iteritems(nipype_outputs):

                pname = trait_map.get(out_name, '_' + out_name)

                try:
                    # if we have an output directory, replace it
                    if output_directory not in (Undefined, None) \
                            and any([x
                                     for x in trait_ids(process_instance.trait(
                                        pname))
                                     if 'File' in x or 'Directory' in x]):
                        out_value = _replace_dir(out_value, output_directory)
                    # Set the output process trait value
                    process_instance.set_parameter(pname, out_value)

                # If we can't update the output process instance traits values,
                # print a logging debug message.
                except Exception as e:
                    print('EXCEPTION:', e, file=sys.stderr)
                    print('while setting nipype output parameter', pname,
                          'on', process_instance.name, 'with value:',
                          out_value, file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    ex_type, ex, tb = sys.exc_info()
                    logger.debug(
                        "Something wrong in the nipype output trait "
                        "synchronization:\n\n\tError: {0} - {1}\n"
                        "\tTraceback:\n{2}".format(
                            ex_type, ex, "".join(traceback.format_tb(tb))))

        if name in list(input_traits.keys()) + ['synchronize',
                                                'output_directory']:
            names = [name]
            if name == 'output_directory':
                names = list(input_traits.keys())
            for name in names:
                # check if the input trait is duplicated as an output
                trait = process_instance.trait(name)
                if trait.copyfile:
                    out_trait = process_instance.trait('_modified_%s' % name)
                    if out_trait:
                        new_value = getattr(process_instance, name)
                        if output_directory not in (Undefined, None):
                            new_value = _replace_dir(new_value,
                                                     output_directory)
                        try:
                            process_instance.set_parameter(
                                "_modified_%s" % name, new_value)
                        # If we can't update the output process instance
                        # traits values, print a logging debug message.
                        except Exception as e:
                            print('EXCEPTION:', e)
                            import traceback
                            traceback.print_exc()
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
        """ Create a new trait (cloned and converted if necessary)
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

    # beginning of nipype_factory function
    try:
        import nipype.interfaces.base.traits_extension as npe
    except (AttributeError, ImportError):
        # In some situations an AttributeError is raised, with the message:
        # module 'nipype.interfaces' has no attribute 'base'
        # but the module is actually here. Maybe it has not finished loading
        # (how can that happen?)
        if 'nipype.interfaces.base.traits_extension' in sys.modules:
            npe = sys.modules['nipype.interfaces.base.traits_extension']
        else:
            # no nipype, or problem loading it. Give up, use regular traits.
            import traits.api as npe

    # Add nipype traits to the process instance
    # > input traits
    trait_map = getattr(process_instance, '_nipype_trait_mapping', {})

    for trait_name, trait in nipype_instance.input_spec().items():

        # Check if trait name already used in class attributes:
        # For instance nipype.interfaces.fsl.FLIRT has a save_log bool input
        # trait.
        trait_name = trait_map.get(trait_name, trait_name)
        if hasattr(process_instance, trait_name):
            trait_name = "nipype_" + trait_name

        # Relax nipype exists trait constraint
        relax_exists_constraint(trait)

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

            if trait_name.startswith("nipype_"):
                setattr(process_instance,
                        trait_name,
                        getattr(nipype_instance.inputs, trait_name[7:]))

            else:
                setattr(process_instance, trait_name,
                        getattr(nipype_instance.inputs, trait_name))

        except TraitError:
            # the value in the nipype trait is actually invalid...
            pass

        # Add the callback to update nipype traits when a process input
        # trait is modified
        process_instance.on_trait_change(sync_nypipe_traits, name=trait_name)

        ## if copyfile is True, we assume the input will be modified, thus it
        ## also becomes an output
        #if trait.copyfile:
            #process_trait = clone_nipype_trait(process_instance, trait)
            #process_trait.output = True
            #process_trait.input_filename = False
            #process_trait.optional = True
            #private_name = "_" + trait_name + '_out'
            #process_instance.add_trait(private_name, process_trait)

    # Add callback to synchronize output process instance traits with nipype
    # autocompleted output traits
    process_instance.on_trait_change(sync_process_output_traits)

    # > output traits
    for trait_name, trait in nipype_instance.output_spec().items():

        # Relax nipye exists trait constraint
        relax_exists_constraint(trait)

        # Clone the nipype trait
        process_trait = clone_nipype_trait(process_instance, trait)

        # Create the output process trait name: nipype trait name prefixed
        # by '_'
        private_name = trait_map.get(trait_name, '_' + trait_name)

        # Add the cloned trait to the process instance
        process_instance.add_trait(private_name, process_trait)
        process_trait = process_instance.trait(private_name)

        # Need to copy all the nipype trait information
        process_trait.optional = not trait.mandatory
        process_trait.desc = trait.desc
        process_trait.output = True
        process_trait.enabled = False

        # SPM output File traits and lists of File should have the
        # metatata input_filename=False
        if process_instance._nipype_interface_name == 'spm':
            if isinstance(process_trait.trait_type,
                          (File, Directory, npe.File, npe.Directory)):
                process_trait.input_filename = False
            elif isinstance(process_trait.trait_type, List) \
                    and isinstance(process_trait.inner_traits[0].trait_type,
                                   (File, Directory, npe.File, npe.Directory)):
                process_trait.inner_traits[0].output = True
                process_trait.inner_traits[0].input_filename = False
                process_trait.input_filename = False

    # allow to save the SPM .m script
    if nipype_instance.__class__.__module__.startswith(
            'nipype.interfaces.spm.'):
        script_name = trait_map.get('_spm_script_file', '_spm_script_file')

        process_instance.add_trait(script_name,
                                   File(output=True, optional=True))

    return process_instance
