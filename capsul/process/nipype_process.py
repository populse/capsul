#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import sys
import os
import types

try:
    import traits.api as traits
    from traits.api import (ListStr, HasTraits, File, Float, Instance,
                            Enum, Str, Directory, CTrait)
    from traits.trait_base import _Undefined
except ImportError:
    import enthought.traits.api as traits
    from enthought.traits.api import (ListStr, HasTraits, File, Float,
                                      Instance, Enum, Str,CTrait)

from capsul.controller import trait_ids
from process import NipypeProcess


def nipype_factory(nipype_instance):
    """ From a nipype class instance generate dynamically the
    corresponding Process instance.

    Parameters
    ----------
    nipype_instance : instance (mandatory)
        a nipype interface instance.

    Returns
    -------
    process_instance : instance
        a process instance.
    """
    trait_cvt_table = {
        "InputMultiPath_TraitCompound": "List",
        "InputMultiPath": "List",
        "MultiPath": "List",
        "Dict_Str_Str": "DictStrStr",
        "OutputMultiPath_TraitCompound": "List",
        "OutputMultiPath": "List",
        "OutputList": "List"
    }

    # modify nipype interface to dynamically update the working dir
    def _run_interface(self, runtime):
        """ Method to execute nipype interface

        Parameters
        ----------
        runtime: Bunch (mandatory)
        the configuration structure
        """
        runtime.cwd = self.inputs.output_directory
        #print runtime
        return self._run_interface_core(runtime)

    def _list_outputs(self):
        """ Method to list all the interface outputs

        Returns
        -------
        outputs: dict
        all the interface outputs
        """
        outputs = self._list_outputs_core()
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

    def _gen_filename(self, name):
        """ Method to generate automatically the output file name.

        Used by: nipype.interfaces.base.CommandLine._parse_inputs

        Returns
        -------
        outputs: str
        the generated output file name
        """
        output = self._gen_filename_core(name)
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
        # reset input traits that has to be generated
        metadata = dict(argstr=lambda t: t is not None)
        for name, spec in sorted(self.inputs.traits(**metadata).items()):
            if spec.genfile or spec.name_source:
                setattr(self.inputs, name, _Undefined())
        return self._parse_inputs_core()  # skip

    nipype_instance.inputs.add_trait("output_directory",
                                     Directory(os.getcwd()))

    nipype_instance._list_outputs_core = nipype_instance._list_outputs
    nipype_instance._list_outputs = types.MethodType(_list_outputs,
                                                     nipype_instance)
    nipype_instance._run_interface_core = nipype_instance._run_interface
    nipype_instance._run_interface = types.MethodType(_run_interface,
                                                      nipype_instance)
    nipype_instance._parse_inputs_core = nipype_instance._parse_inputs
    nipype_instance._parse_inputs = types.MethodType(_parse_inputs,
                                                      nipype_instance)

    if "fsl" in nipype_instance.__class__.__module__:
        nipype_instance._gen_filename_core = nipype_instance._gen_filename
        nipype_instance._gen_filename = types.MethodType(_gen_filename,
                                                         nipype_instance)

#    # add method in order to enable the cache pickling the instance.
#    # add the virtual mathod
#    attributes["_run_process"] = _call_nipype
#    # store the nipype interface instance
#    attributes["_nipype_interface"] = nipype_instance
#    attributes["_nipype_module"] = nipype_instance.__class__.__module__
#    attributes["_nipype_class"] = nipype_instance.__class__.__name__
#    attributes["_nipype_interface_name"] = attributes["_nipype_module"].split(
#                                                      ".")[2]
#
#    # create new instance derived from Process
#    process_class = type(attributes["_nipype_class"],
#                         (NipypeProcess, ),
#                         attributes)
#    process_instance = process_class()

    # create new instance derived from Process
    process_instance = NipypeProcess(nipype_instance)

    # relax exists constrain
    def relax_exists_constrain(trait):

        if "exists" in dir(trait.handler):
            trait.handler.exists = False

        main_id = trait.handler.__class__.__name__
        if main_id == 'TraitCompound':
            for sub_trait in trait.handler.handlers:
                sub_c_trait = CTrait(0)
                sub_c_trait.handler = sub_trait
                relax_exists_constrain(sub_c_trait)
        elif len(trait.inner_traits) > 0:
            for sub_c_trait in trait.inner_traits:
                relax_exists_constrain(sub_c_trait)

    # add traits to the process instance
    def sync_nypipe_traits(process_instance, name, old, value):
        """ Event handler function to update
        the nipype interface traits
        """
        if old != value:
            # relax exists constrain
            trait = process_instance._nipype_interface.inputs.trait(name)
            relax_exists_constrain(trait)
            # sync value
            setattr(process_instance._nipype_interface.inputs, name,
                    value)

    def sync_process_output_traits(process_instance, name, value):
        """ Event handler function to update
        the process instance outputs """
        try:
            nipype_outputs = (process_instance.
                             _nipype_interface._list_outputs())
            for out_name, out_value in nipype_outputs.iteritems():
                process_instance.set_parameter("_" + out_name, out_value)
        except:
            pass

    # clone a nipype trait
    def clone_nipype_trait(nipype_trait):
        """ Create a new trait (clone) from a trait string description
        """
        # get the string description
        str_description = trait_ids(trait)

        # normlize the description
        add_switch = False
        if "MultiPath" in str_description[0]:
            add_switch = True
        for old_str, new_str in trait_cvt_table.iteritems():
            for cnt in range(len(str_description)):
                str_description[cnt] = str_description[cnt].replace(old_str,
                                                                    new_str)
        if add_switch:
            str_description = [str_description[0],
                               "_".join(str_description[0].split("_")[1:])]

        # create a new trait from its expression and namespace
        namespace = {"traits": traits, "process_trait": None}
        trait_expressions = []
        for trait_spec in str_description:
            trait_spec = trait_spec.split("_")
            expression = ""
            for trait_item in trait_spec:
                expression += "traits.{0}(".format(trait_item)
                if trait_item == "Enum":
                    expression += "{0}".format(trait.get_validate()[1])

                #  Range Extra args
                if trait_item == "Range":
                    if isinstance(nipype_trait, traits.CTrait):
                        expression += "low={0},high={1}".format(
                            nipype_trait.handler._low,
                            nipype_trait.handler._high)
                    else:
                        expression += "low={0},high={1}".format(
                            nipype_trait._low,
                            nipype_trait._high)
            expression += ")" * len(trait_spec)
            trait_expressions.append(expression)

        if len(trait_expressions) > 1:
            expression = "process_trait = traits.Either("
            for trait_expression in trait_expressions:
                expression += "{0}, ".format(trait_expression)
            expression += ")"
        else:
            expression = "process_trait = {0}".format(trait_expressions[0])

        # evaluate expression in namespace
        def f():
            exec expression in namespace

        try:
            f()
        except:
            raise Exception("Can't evaluate expression {0} in namespace"
                            "{1}."
                            "Please investigate: {2}.".format(expression,
                            namespace, sys.exc_info()[1]))
        process_trait = namespace["process_trait"]

        # copy description*
        process_trait.desc = nipype_trait.desc
        process_trait.optional = not nipype_trait.mandatory

        return process_trait

    # input
    for name, trait in nipype_instance.input_spec().items():
        process_trait = clone_nipype_trait(trait)
        process_instance.add_trait(name, process_trait)
        #print name, trait_ids(trait)
        # TODO: fix this hack in Controller
        process_instance.trait(name).optional = not trait.mandatory
        process_instance.trait(name).desc = trait.desc
        process_instance.trait(name).output = False
        process_instance.get(name)
        process_instance.on_trait_change(sync_nypipe_traits, name=name)
        process_instance.on_trait_change(sync_process_output_traits)

    # output
    for name, trait in nipype_instance.output_spec().items():
        process_trait = clone_nipype_trait(trait)
        process_trait.output = True
        private_name = "_" + name
        #print private_name, trait_ids(trait)
        process_instance.add_trait(private_name, process_trait)
        # TODO: fix this hack in Controller
        process_instance.trait(private_name).optional = not trait.mandatory
        process_instance.trait(private_name).desc = trait.desc
        process_instance.trait(private_name).output = True
        process_instance.trait(private_name).enabled = False

    return process_instance
