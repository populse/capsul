##########################################################################
# SOMA - Copyright (C) CEA, 2015
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


# Global parameters
_type_to_trait_id = {
    int: "Int",
    unicode: "Unicode",
    str: "Str",
    float: "Float"
}
# In order to convert nipype special traits, we define a dict of
# correspondances
_trait_cvt_table = {
    "InputMultiPath_TraitCompound": "List",
    "InputMultiPath": "List",
    "MultiPath": "List",
    "Dict_Str_Str": "DictStrStr",
    "OutputMultiPath_TraitCompound": "List",
    "OutputMultiPath": "List",
    "OutputList": "List"
}


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
    else:
        manhelpstr += wrap("No description.", 70,
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


def clone_trait(trait_description):
    """ Clone a trait from its string description.

    In the case of Enum trait, we need to initilaize the object with all its
    'trait_values'.

    Parameters
    ----------
    trait_description: list of str (mandatory)
        the trait string description from which we want to create a new trait
        instance of the same type.
    """
    # Build the new trait expression
    trait_expression = []

    # Go through all its possible types (Either trait structure)
    for trait_spec in trait_description:

        # Split the current trait specification
        trait_spec = trait_spec.split("_")
        trait_expression.append(build_expression_from_spec(trait_spec))

    # Build the final expression: use the Either trait if multiple expressions
    if len(trait_expression) > 1:
        expression = "eval_trait = traits.Either("
        for item in trait_expression:
            expression += "{0}, ".format(item)
        expression += ")"
    else:
        expression = "eval_trait = {0}".format(trait_expression[0])

    return eval_trait(expression)


def build_expression_from_spec(trait_spec):
    """ Build the expression to instanciate the trait.

    Parameters
    ----------
    trait_spec: list of string (mandatory)
        a trait string description structure.

    Returns
    -------
    expression: str
        the corresponding string expression.
    """
    # Only deal for now with those traits
    allowed_traits = ["List", "Tuple", "Int", "Float", "Str", "String", "File",
                      "Directory", "Any", "Bool"]

    # Build the expression we will evaluate to build the new trait item
    expression = ""
    expression_size = 0
    for trait_item in trait_spec:

        # Check item type
        if trait_item not in allowed_traits:
            raise ValueError("'{0}' trait not yet supported.".format(
                trait_item))

        # Update the expression with the new item
        expression += "traits.{0}(".format(trait_item)
        expression_size += 1

        # Tuple special case
        if trait_item == "Tuple":

            # Go through all tuple items
            for cnt, tuple_item in enumerate(trait_spec[expression_size:]):

                # Check item type
                if tuple_item not in allowed_traits:
                    raise ValueError("'{0}' trait not yet supported.".format(
                        trait_item))

                # List and Tuple special cases
                if tuple_item in ["List", "Tuple"]:
                    expression += build_expression_from_spec(
                        trait_spec[expression_size + cnt:])
                    break

                # Update expression with the new item
                else:
                    expression += "traits.{0}(), ".format(tuple_item)
            break

    # Close and store the current trait expression
    expression += ")" * expression_size

    return expression


def eval_trait(expression):
    """ Evaluate an expression to create a new trait.

    Parameters
    ----------
    expression: str (mandatory)
        a string expression to evaluate in order to create a new trait.

    Returns
    -------
    eval_trait: trait instance
        a trait instance.
    """
    # Create a new trait from its expression and namespace
    # Frist define the namespace were the expression will be executed
    namespace = {"traits": traits, "Undefined": traits.Undefined,
                 "eval_trait": None}

    # Complete the expression
    expression = "eval_trait = {0}".format(expression)

    # Debug message
    logger.debug("Evaluate expression '%s' in namespace '%s'", expression,
                 repr(namespace))

    # Evaluate the expression in the defined namespace
    def f():
        exec expression in namespace
    try:
        f()
    except:
        raise Exception(
            "Can't evaluate expression '{0}' in namespace '{1}'."
            "Please investigate: '{2}'.".format(
                expression, namespace, sys.exc_info()[1]))

    return namespace["eval_trait"]


def trait_ids(trait):
    """Return the type of the trait: File, Enum etc...

    Parameters
    ----------
    trait: trait instance (mandatory)
        a trait instance

    Returns
    -------
    main_id: list
        the string description (type) of the input trait.
    """
    # Get the trait class name
    handler = trait.handler or trait
    main_id = handler.__class__.__name__
    if main_id == "TraitCoerceType":
        real_id = _type_to_trait_id.get(handler.aType)
        if real_id:
            main_id = real_id

    # Use the convertion table to normalize the trait id
    if main_id in _trait_cvt_table:
        main_id = _trait_cvt_table[main_id]

    # Debug message
    logger.debug("Trait with main id %s", main_id)

    # Search for inner traits
    inner_ids = []

    # Either case
    if main_id in ["Either", "TraitCompound"]:

        # Debug message
        logger.debug("A coumpound trait has been found %s", repr(
            handler.handlers))

        # Build each trait compound description
        trait_description = []
        for sub_trait in handler.handlers:
            trait_description.extend(trait_ids(sub_trait()))
        return trait_description

    # Default case
    else:
        # FIXME may recurse indefinitely if the trait is recursive
        inner_id = '_'.join((trait_ids(i)[0]
                             for i in handler.inner_traits()))
        if not inner_id:
            klass = getattr(handler, 'klass', None)
            if klass is not None:
                inner_ids = [i.__name__ for i in klass.__mro__]
            else:
                inner_ids = []
        else:
            inner_ids = [inner_id]

        # Format the output string result
        if inner_ids:
            return [main_id + "_" + inner_desc for inner_desc in inner_ids]
        else:
            return [main_id]


def build_expression(trait):
    """ Build the expression to instanciate the trait.

    Parameters
    ----------
    trait: trait instance (mandatory)
        a trait instance.

    Returns
    -------
    expression: str
        the corresponding string expression.
    """
    # Get the trait desciption
    # If the desciption list return more than one element, we have to deal with
    # an Either trait
    trait_description = trait_ids(trait)

    # Error case
    if len(trait_description) == 0:
        raise ValueError("Can't deal with empty structure.")

    # Either case
    elif len(trait_description) > 1:

        # Debug message
        logger.debug("Either compounds are %s", repr(trait.handler.handlers))

        # Update expression
        either_expression = [build_expression(inner_trait())
                             for inner_trait in trait.handler.handlers]
        return "traits.Either({0})".format(", ".join(either_expression))

    # Default case
    else:
        trait_spec = trait_description[0].split("_")

    # Debug message
    logger.debug("Build expression from %s (%s)", repr(trait_spec),
                 repr(trait))

    # Standard case: add atomic trait description in the
    # expression
    trait_item = trait_spec[0]
    expression = "traits.{0}".format(trait_item)

    # Debug message
    logger.debug("Current item is a %s", trait_item)

    # Special case: Tuple
    # Need to set the value types
    if trait_item == "Tuple":

        # Debug message
        logger.debug("Inner traits are %s", repr(trait.get_validate()[1]))

        # Update expression
        tuple_expression = [build_expression(inner_trait())
                            for inner_trait in trait.get_validate()[1]]
        expression += "({0})".format(", ".join(tuple_expression))

    # Special case: List
    # Need to set the value type
    elif trait_item == "List":

        # Debug message
        logger.debug("Inner traits are %s", repr(trait.inner_traits))

        # Update expression
        expression += "({0})".format(build_expression(trait.inner_traits[0]))

    # Special case: Dict
    # Need to set the key and value types
    elif trait_item == "Dict":

        # Debug message
        logger.debug("Inner traits are %s", repr(trait.inner_traits))

        # Update expression
        expression += "({0}, {1})".format(
            build_expression(trait.inner_traits[0]),
            build_expression(trait.inner_traits[1]))

    # Special case: Enum
    # Need to add enum values at the construction
    elif trait_item == "Enum":

        # Debug message
        logger.debug("Default values are %s", repr(trait.get_validate()[1]))

        # Update expression
        expression += "({0})".format(trait.get_validate()[1])

    # Special case: Range
    # Need to add the lower and upper bounds
    elif trait_item == "Range":

        if isinstance(trait, traits.CTrait):
            # Debug message
            logger.debug("Range is %f - %f", trait.handler._low,
                         trait.handler._high)

            # Update expression
            expression += "(low={0},high={1})".format(
                trait.handler._low, trait.handler._high)
        else:
            # Debug message
            logger.debug("Range is %f - %f", trait._low, trait._high)

            # Update expression
            expression += "(low={0},high={1})".format(
                trait._low, trait._high)

    # Special case: File
    # Initialize the default file trait value to undefined
    elif trait_item == "File":
        expression += "(Undefined)"

    # Default
    else:
        expression += "()"

    return expression
