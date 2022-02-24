# -*- coding: utf-8 -*-
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
import sys
import os
import types
import inspect
import logging

# Capsul import
from .process import NipypeProcess
import soma.controller as sc
import traits.api as traits


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
    """

    def replace_undef(value):
        ''' traits -> fields values replacement
        '''
        if value is traits.Undefined:
            return sc.undefined
        if isinstance(value, list):
            return [replace_undef(v) for v in value]
        if isinstance(value, tuple):
            return tuple(replace_undef(v) for v in value)
        if isinstance(value, dict):
            return {k: replace_undef(v) for k, v in value.items()}
        return value

    def replace_Undef(value):
        ''' fields -> traits values replacement
        '''
        if value is sc.undefined:
            return traits.Undefined
        if isinstance(value, list):
            return [replace_Undef(v) for v in value]
        if isinstance(value, tuple):
            return tuple(replace_Undef(v) for v in value)
        if isinstance(value, dict):
            return {k: replace_Undef(v) for k, v in value.items()}
        return value

    ###################################################################
    # Define functions to synchronize the process and interface traits
    ###################################################################

    def sync_nypipe_traits(value, old, name, process_instance):
        """ Event handler function to update the nipype interface traits

        Parameters
        ----------
        value: type (manndatory)
            the new trait value
        old: type (manndatory)
            the old trait value
        name: str (mandatory)
            the name of the trait we want to update.
        process_instance: process instance (mandatory)
            the process instance that contain the nipype interface we want
            to update.
        """
        # Set the new nypipe interface value
        trait_map = getattr(process_instance, '_nipype_trait_mapping', {})
        inames = [iname for iname, pname in trait_map.items() if pname == name]
        if inames:
            name = inames[0]

        value = replace_Undef(value)

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
        value = replace_undef(value)
        if value in (None, sc.undefined, ""):
            return value
        if isinstance(value, list):
            value = [_replace_dir(x, directory) for x in value]
        else:
            value = os.path.join(directory, os.path.basename(value))
        return value

    def sync_process_output_traits(value, old, name, process_instance):
        """ Event handler function to update the process instance outputs

        This callback is only called when an input process instance field is
        modified.

        Parameters
        ----------
        value: type (mandatory)
            the new trait value
        old: type (mandatory)
            the old trait value
        name: str (mandatory)
            the name of the trait we want to update.
        process_instance: process instance (mandatory)
            the process instance that contain the nipype interface we want
            to update.
        """
        # Get all the input fields
        input_fields = {f.name for f in process_instance.fields()
                        if f.is_input()}
        output_directory \
            = getattr(process_instance, 'output_directory', sc.undefined)

        # get the interface name from the process trait name
        trait_map = getattr(process_instance, '_nipype_trait_mapping', {})

        # Try to update all the output process instance traits values when
        # a process instance input trait is modified or when the dedicated
        # 'synchronize' trait value is modified
        if name in input_fields or name in ("synchronize", 'output_directory'):

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
                logging.debug(
                    "Something wrong in the nipype output trait "
                    "synchronization:\n\n\tError: {0} - {1}\n"
                    "\tTraceback:\n{2}".format(
                        ex_type, ex, "".join(traceback.format_tb(tb))))
                nipype_outputs = {}

            # Synchronize traits: check file existence
            for out_name, out_value in nipype_outputs.items():

                pname = trait_map.get(out_name, '_' + out_name)

                try:
                    # if we have an output directory, replace it
                    if output_directory not in (sc.undefined, None) \
                            and process_instance.field(pname).has_path():
                        out_value = _replace_dir(out_value, output_directory)
                        # Set the output process trait value
                        setattr(process_instance, pname, out_value)

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
                    logging.debug(
                        "Something wrong in the nipype output trait "
                        "synchronization:\n\n\tError: {0} - {1}\n"
                        "\tTraceback:\n{2}".format(
                            ex_type, ex, "".join(traceback.format_tb(tb))))

        if name in input_fields.union(['synchronize', 'output_directory']):
            names = [name]
            if name == 'output_directory':
                names = input_fields
            for name in names:
                # check if the input trait is duplicated as an output
                field = process_instance.field(name)
                if process_instance.metadata(field, 'copyfile', False):
                    out_field = process_instance.field('_modified_%s' % name)
                    if out_field:
                        new_value = getattr(process_instance, name,
                                            sc.undefined)
                        if output_directory not in (sc.undefined, None):
                            new_value = _replace_dir(new_value,
                                                     output_directory)
                        try:
                            setattr(process_instance,
                                    "_modified_%s" % name, new_value)
                        # If we can't update the output process instance
                        # traits values, print a logging debug message.
                        except Exception as e:
                            print('EXCEPTION:', e)
                            import traceback
                            traceback.print_exc()
                            ex_type, ex, tb = sys.exc_info()
                            logging.debug(
                                "Something wrong in the nipype output trait "
                                "synchronization:\n\n\tError: {0} - {1}\n"
                                "\tTraceback:\n{2}".format(
                                    ex_type, ex, "".join(traceback.format_tb(tb))))


    # Change first level masking explicit in postscript
    def _make_matlab_command(self, content):
        from nipype.interfaces.spm import Level1Design
        return super(Level1Design, self)._make_matlab_command(
            content, postscript=None)

    # beginning of nipype_factory function

    ####################################################################
    # Monkey patching for Nipype version '0.9.2'.
    ####################################################################

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
        field_name = trait_map.get(trait_name, trait_name)
        if process_instance.field(field_name) is not None:
            field_name = "nipype_" + field_name

        # Relax nipype exists trait constraint
        relax_exists_constraint(trait)

        # Convert the nipype trait to a field
        process_field = trait_to_field(trait)

        # Add the cloned trait to the process instance,
        # Need to copy all the nipype trait information
        process_instance.add_field(field_name, process_field,
                                   optional=not trait.mandatory,
                                   output=False,
                                   doc=trait.desc)

        # initialize value with nipype interface initial value, (if we can...)
        try:

            if trait_name.startswith("nipype_"):
                setattr(process_instance,
                        trait_name,
                        getattr(nipype_instance.inputs, trait_name[7:]))

            else:
                value = getattr(nipype_instance.inputs, trait_name)
                value = replace_undef(value)
                setattr(process_instance, field_name, value)

        except sc.ValidationError:
            # the value in the nipype trait is actually invalid...
            pass

        # Add the callback to update nipype traits when a process input
        # trait is modified
        process_instance.on_attribute_change.add(sync_nypipe_traits,
                                                 attribute_name=trait_name)

        ## if copyfile is True, we assume the input will be modified, thus it
        ## also becomes an output
        #if trait.copyfile:
            #process_trait = trait_to_field(trait)
            #process_trait.output = True
            #process_trait.input_filename = False
            #process_trait.optional = True
            #private_name = "_" + trait_name + '_out'
            #process_instance.add_trait(private_name, process_trait)

    # Add callback to synchronize output process instance traits with nipype
    # autocompleted output traits
    process_instance.synchronize.add(sync_process_output_traits)

    # > output traits
    for trait_name, trait in nipype_instance.output_spec().items():

        # Relax nipye exists trait contrain
        relax_exists_constraint(trait)

        # Clone the nipype trait
        process_field = trait_to_field(trait)

        # Create the output process field name: nipype trait name prefixed
        # by '_'
        private_name = trait_map.get(trait_name, '_' + trait_name)

        # Add the cloned trait to the process instance
        # Need to copy all the nipype trait information
        kwargs = {
            'optional': not trait.mandatory,
            'enabled': False,
            'doc': trait.desc,
        }
        if process_field.has_path():
            kwargs['write'] = True
        else:
            kwargs['output'] = True

        # SPM output File traits and lists of File should have the
        # metatata output=True
        if process_instance._nipype_interface_name == 'spm':
            kwargs['output'] = True

        process_instance.add_field(private_name, process_field,
                                   metadata=kwargs)

    # allow to save the SPM .m script
    if nipype_instance.__class__.__module__.startswith(
            'nipype.interfaces.spm.'):
        script_name = trait_map.get('_spm_script_file', '_spm_script_file')

        process_instance.add_field(script_name,
                                   sc.file(write=True, optional=True))

    return process_instance


t_f = {
    'Int': (int, None),
    'Float': (float, None),
    'Str': (str, None),
    'String': (str, None),
    'Bool': (bool, None),
    'File': (sc.file, None),
    'List': (list, None),
    'Directory': (sc.directory, None),
    'TraitCompound': (sc.Union, None),
    'InputMultiPath_TraitCompound': (sc.List, None),
    'InputMultiPath': (sc.List, None),
    'InputMultiObject': (sc.List, None),
    'OutputMultiObject': (sc.List, {'write': True}),
    'MultiPath': (sc.List, None),
    'Dict_Str_Str': (dict, None),
    'OutputMultiPath_TraitCompound': (sc.List, {'write': True}),
    'OutputMultiPath': (sc.List, {'write': True}),
    'OutputList': (sc.List, {'write': True}),
    'ImageFileSPM': (sc.file,
                      {'allowed_extensions': ['.nii', '.img', '.hdr',
                                              '.mnc']}),
}


def parse_trait(trait):
    tree = {}

    handler = trait
    if trait.handler is not None:
        handler = trait.handler

    ttype = handler.__class__.__name__
    ftype = t_f.get(ttype)
    if ftype is None:
        print('trait type', ttype, 'not found')
        return tree

    ftype, args = ftype
    tree['trait'] = handler
    tree['field'] = ftype
    tree['args'] = args

    if handler.has_items:
        if handler.handlers:
            sub_traits = handler.handlers
        else:
            sub_traits = handler.inner_traits()
        tree['children'] = [parse_trait(t) for t in sub_traits]

    return tree


def parsed_trait_to_field(ptrait):
    ftype = ptrait['field']
    children = ptrait.get('children', [])
    chtypes = []
    args = ptrait.get('args')
    if args is None:
        args = {}
    for child in children:
        stype, sargs = parsed_trait_to_field(child)
        chtypes.append(stype)
        # FIXME: what about sargs ?

    if inspect.isfunction(ftype):
        #f = ftype
        f = ftype(*chtypes, **args)
        args = {}
    elif children:
        if len(chtypes) == 1:
            f = ftype[chtypes[0]]
        else:
            # this syntax doas not work for List
            f = ftype[tuple(chtypes)]
    else:
        f = ftype

    return f, args


def trait_to_field(trait):
    ptrait = parse_trait(trait)
    ftype, args = parsed_trait_to_field(ptrait)
    return sc.field(type_=ftype, **args)


def relax_exists_constraint(trait):
    """ Relax the exist constraint of a trait

    Parameters
    ----------
    trait: trait
        a trait that will be relaxed from the exist constraint
    """
    # If we have a single trait, just modify the 'exists' contrain
    # if specified
    if hasattr(trait.handler, "exists"):
        trait.handler.exists = False

    # If we have a selector, call the 'relax_exists_constraint' on each
    # selector inner components.
    main_id = trait.handler.__class__.__name__
    if main_id == "TraitCompound":
        for sub_trait in trait.handler.handlers:
            sub_c_trait = traits.CTrait(0)
            sub_c_trait.handler = sub_trait
            relax_exists_constraint(sub_c_trait)
    elif len(trait.inner_traits) > 0:
        for sub_c_trait in trait.inner_traits:
            relax_exists_constraint(sub_c_trait)
