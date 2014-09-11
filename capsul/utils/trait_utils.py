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
import types
from textwrap import wrap
import re
import logging

# Define the logger
logger = logging.getLogger(__name__)

# Trait import
import traits.api as traits

# Soma import
from soma.controller import trait_ids


def get_trait_desc(trait_name, trait, def_val=None):
    """ Generate a trait string description of the form:

    [parameter name: type (default trait value) string help (description)]

    Parameters
    ----------
    name: string (mandatory)
        the trait name
    trait: a trait instance (mandatory)
        a trait instance
    def_val: object (optional)
        the trait default value
        If not in ['', None] add the default trait value to the trait
        string description.

    Returns
    -------
    manhelpstr: str
        the trait description.
    """
    # Get the trait description
    desc = trait.desc

    # Get the trait type
    trait_id = trait_ids(trait)

    # Add the trait name (bold)
    manhelpstr = ["{0}".format(trait_name)]

    # Get the default value string representation
    if def_val not in ["", None]:
        def_val = ", default value: {0}".format(repr(def_val))
    else:
        def_val = ""

    # Get the paramter type (optional or mandatory)
    if trait.optional:
        dtype = "optional"
    else:
        dtype = "mandatory"

    # Get the default parameter representation: trait type of default
    # value if specified
    line = "{0}".format(trait.info())
    if not trait.output:
        line += " ({0} - {1}{2})".format(trait_id, dtype, def_val)

    # Wrap the string properly
    manhelpstr = wrap(line, 70,
                      initial_indent=manhelpstr[0] + ": ",
                      subsequent_indent="    ")

    # Add the trait description if specified
    if desc:
        for line in desc.split("\n"):
            line = re.sub("\s+", " ", line)
            manhelpstr += wrap(line, 70,
                               initial_indent="    ",
                               subsequent_indent="    ")

    return manhelpstr


def is_trait_value_defined(value):
    """ Check if a trait value is valid.

    Parameters
    ----------
    value: type (mandatory)
        a value to test.

    Returns
    -------
    out: bool
        True if the value is valid,
        False otherwise.
    """
    # Initialize the default value
    is_valid = True

    # Check if the trait value is not valid
    if (value is None or value is traits.Undefined or
       (type(value) in types.StringTypes and value == "")):

        is_valid = False

    return is_valid


def is_trait_pathname(trait):
    """ Check if the trait is a file or a directory.

    Parameters
    ----------
    trait: CTrait (mandatory)
        the trait instance we want to test.

    Returns
    -------
    out: bool
        True if trait is a file or a directory,
        False otherwise.
    """
    return (isinstance(trait.trait_type, traits.File) or
            isinstance(trait.trait_type, traits.Directory))


def clone_trait(trait_description, trait_values=None):
    """ Clone a trait from its string description.

    In the case of Enum trait, we need to initilaize the object with all its
    'trait_values'.

    Parameters
    ----------
    trait_description: list of str (mandatory)
        the trait string description from which we want to create a new trait
        instance of the same type.
    trait_values: object (optional, default None)
        the new trait initiale values.
    """
    # Build the new trait expression
    trait_expression = []

    # Go through all its possible types (Either trait structure)
    for trait_spec in trait_description:

        # Split the current trait specification
        trait_spec = trait_spec.split("_")

        # Build the expression we will evaluate to build the new trait item
        expression = ""
        for trait_item in trait_spec:
            expression += "traits.{0}(".format(trait_item)

        # Add initiale values if necessary
        if trait_values is not None:
            expression += str(trait_values)

        # Close and store the current trait expression
        expression += ")" * len(trait_spec)
        trait_expression.append(expression)

    # Build the final expression: use the Either trait if multiple expressions
    if len(trait_expression) > 1:
        expression = "eval_trait = traits.Either("
        for item in trait_expression:
            expression += "{0}, ".format(item)
        expression += ")"
    else:
        expression = "eval_trait = {0}".format(trait_expression[0])

    # Create a new trait from its expression and namespace
    namespace = {"traits": traits, "eval_trait": None}

    # Evaluate expression in namespace
    def f():
        exec expression in namespace

    try:
        f()
    except:
        raise Exception(
            "Can't evaluate expression {0} in namespace {1}."
            "Please investigate: {2}.".format(
                expression, namespace, sys.exc_info()[1]))

    return namespace["eval_trait"]
