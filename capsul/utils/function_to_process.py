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
import xml.dom.minidom
import inspect
import re
import importlib

# Trait import
import traits.api as traits

# Capsul import
from .description_utils import title_for
from .description_utils import parse_docstring
from capsul.utils.trait_utils import clone_trait
from capsul.process import Process


class AutoProcess(Process):
    """ Process class  generated dynamically.
    """
    xml_tag = "unit"

    def __init__(self):
        """ Initialize the AutoProcess class.
        """
        # Inheritance
        super(AutoProcess, self).__init__()

        # Set the process input and output traits
        for trait_name, trait in self._process_traits.iteritems():
            self.add_trait(trait_name, trait)
            self.trait(trait_name).output = trait.output
            self.trait(trait_name).desc = trait.desc
            self.trait(trait_name).optional = trait.optional

        for trait_name, trait_value in self._defaults.items():
            self.set_parameter(trait_name, trait_value)

        # Redefine process identifier
        if hasattr(self, "_id"):
            self.id = self._id

    def _run_process(self):
        """ Execute the AutoProcess class.
        """
        # Build expression and namespace
        namespace, expression = self._build_expression()

        # Execute it
        def f():
            exec expression in namespace
        f()

        # Update the user trait values
        for parameter in self._parameters:
            if parameter.get("role", "") == "output":
                self.set_parameter(
                    parameter["name"], namespace[parameter["name"]])

    def _build_expression(self):
        """ Build an expression and namespace in order to execute the function
        attached to this box.
        """
        # Load the function from its string description
        importlib.import_module(self._func_module)
        module = sys.modules[self._func_module]
        function = getattr(module, self._func_name)

        # Get the function parameters and retunred values
        inputs = inspect.getargspec(function).args
        code = inspect.getsourcelines(function)
        return_pattern = r"return\s*(.*)\n*$"
        outputs = re.findall(return_pattern, code[0][-1])
        outputs = [item.strip() for item in outputs[0].split(",")]

        # Build the expression namespace
        namespace = {"function": function}

        # Deal with all function input parameters
        kwargs = []
        for control_name in inputs:

            # Check input function parameter has been declared on the box
            if control_name not in self.traits(output=False):
                raise Exception(
                    "Impossible to execute Box '{0}': function input "
                    "parameter '{1}' has not been defined in function '<{2}>' "
                    "description.".format(self.id, control_name, self.xml_tag))
            # Update namespace
            value = self.get_parameter(control_name)
            if value is traits.Undefined:
                value = None
            namespace[control_name] = value
            # Create kwargs
            kwargs.append("{0}={0}".format(control_name))

        # Deal with all function returned parameters
        for control_name in outputs:

            # Check returned function parameter has been declared on the bbox
            if control_name not in self.traits(output=True):
                raise Exception(
                    "Impossible to execute Box '{0}': function returned "
                    "parameter '{1}' has not been defined in function '<{2}>' "
                    "description.".format(self.id, control_name, self.xml_tag))
            # Update namespace
            namespace[control_name] = None

        # Build the function expression
        expression = "function({0})".format(", ".join(kwargs))

        # If we have some returned values, update the expression
        if outputs:
            return_expression = ", ".join(outputs)
            expression = "{0} = {1}".format(return_expression, expression)

        return namespace, expression


def class_factory(func, destination_module_globals):
    """ Dynamically create a process instance from a function

    In order to make the class publicly accessible, we assign the result of
    the function to a variable dynamically using globals().

    Parameters
    ----------
    func: @function (mandatory)
        the function we want encapsulate in a process.
    """
    # Create the process class name
    class_name = title_for(func.__name__)

    # Get the capsul prototype
    capsul_proto = parse_docstring(func.__doc__)

    # Create all the process input and output traits
    process_traits, defaults = create_controls(capsul_proto, func)

    # Clean the docstring
    docstring = func.__doc__
    res = re.search(r"<unit>.*</unit>.*", docstring, flags=re.DOTALL)
    if res:
        docstring = docstring.replace(docstring[res.start():res.end()], "")

    # Define the process class parameters
    class_parameters = {
        "__doc__": docstring,
        "__module__": destination_module_globals["__name__"],
        "_id":  destination_module_globals["__name__"] + "." + class_name,
        "_func_name": func.__name__,
        "_func_module": func.__module__,
        "_parameters": capsul_proto,
        "_process_traits": process_traits,
        "_defaults": defaults,
        "desc": func.__module__ + "." + func.__name__
    }

    # Get the process instance associated to the function
    destination_module_globals[class_name] = (
        type(class_name, (AutoProcess, ), class_parameters))

def create_controls(proto, func):
    """ Define the process input and output parameters. Each parameter is
    a control defined in Trait library.

    Expected control attibutes are: 'type', 'name', 'description', 'from',
    'role'.
    """
    # Get the function default values
    args = inspect.getargspec(func)
    defaults = dict(zip(reversed(args.args or []),
                        reversed(args.defaults or [])))

    # Go through all controls defined in the function prototype
    shared_output_controls = []
    process_traits = {}
    for desc in proto:

        # Detect shared output controls
        if "from" in desc and desc["role"] == "output":
            shared_output_controls.append(desc["from"])
            continue

        # Get the control type and description
        control_type = desc.get("type", None)
        if control_type is None:
            raise Exception("Impossible to warp Box '{0}': control type "
                            "undefined.".format(func.__name__))
        control_desc = desc.get("description", "")
        control_name = desc.get("name", None)
        if control_name is None:
            raise Exception("Impossible to warp Box '{0}': control name "
                            "undefined.".format(func.__name__))
        control_content = desc.get("content", None)

        # Create the trait
        trait_desc = control_type
        if control_content is not None:
            trait_desc += "_{0}".format(control_content)
        try:
            trait_desc = eval(trait_desc)
        except:
            pass
        if not isinstance(trait_desc, list):
            trait_desc = [trait_desc]
        trait = clone_trait(trait_desc)
        trait._metadata = {}

        # Set description
        trait.desc = control_desc

        # Set default values
        if control_name in defaults:
            trait.optional = True
        else:
            trait.optional = False

        # Split output controls
        if desc["role"] == "output":
            trait.output = True
        # And input controls
        else:
            trait.output = False

        # Store the created trait
        process_traits[control_name] = trait

    # Deal with shared output controls
    for control_name in shared_output_controls:
        raise NotImplementedError("Reference control not yet implemented.")

    return process_traits, defaults

def register_processes(functions, destination_module_globals=None):
    """ Register a number of new processes from function.

    Parameters
    ----------
    functions: list of @function (mandatory)
        a list of functions we want to encapsulate in processes.
    """
    # Get the caller module globals parameter
    if destination_module_globals is None:
        destination_module_globals = inspect.stack()[1][0].f_globals

    # Go through all function and create/register the corresponding process
    for func in functions:
        class_factory(func, destination_module_globals)
