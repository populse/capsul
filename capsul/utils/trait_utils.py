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

# Soma import
from soma.controller import trait_ids

# Trait import
try:
    import traits.api as traits
except ImportError:
    import enthought.traits.api as traits


def clone_trait(trait_description, trait_values=None):
    """ Clone a trait from its string description.

    In the case of Enum trait, we need to initilaize the object with all its
    trait values

    Parameters
    ----------
    trait_description: list of str (mandatory)
        the trait string description from which we want to create a new trait 
        instance of the same type.
    trait_values: object (optional, default None)
        the new trait initiale values.
    """
    # Get the trait string descriptions
    #if isinstance(trait, list):
    #    trait_description = trait
    #else:
    #    trait_description = trait_ids(trait)

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
