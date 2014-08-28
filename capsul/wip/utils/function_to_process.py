#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os
import sys
import xml.dom.minidom
import inspect
import re

# Capsul import
from capsul.utils.trait_utils import clone_trait
from capsul.process import Process


def title_for(title):
    """ Create a title from an underscore-separated string.

    Parameters
    ----------
    title: str (mandatory)
        the string to format.

    Returns
    -------
    out: str
        the formated string.
    """
    return title.replace("_", " ").title().replace(" ", "")


def parse_docstring(docstring):
    """ Parse the given docstring to get the <capsul> xml-like structure.

    Parameters
    ----------
    docstring: str (mandatory)
        a string where we will try to found the <capsul> xml-like structure.

    Returns
    -------

    """
    # Find the <capsul> xml-like structure in the docstring
    capsul_start = docstring.rfind("<capsul>")
    capsul_end = docstring.rfind("</capsul>")
    capsul_description = docstring[capsul_start: capsul_end + len("</capsul>")]

    # Parse the xml structure and put each xml dictionnary formated item in a
    # list
    parameters = []

    # If no description has been found in the doctring, return an empty
    # parameter list
    if not capsul_description:
        return parameters

    # Find all the xml 'item' tag elements
    document = xml.dom.minidom.parseString(capsul_description)
    for node in document.childNodes[0].childNodes:

        # Assert we have an 'item' node
        if node.nodeType != node.ELEMENT_NODE or node.tagName != "item":
            continue
        
        # Set each xml 'item' tag element in the paramter list
        parameters.append(dict(node.attributes.items()))

    return parameters


class AutoProcess(Process):
    """ Dummy process class genereated dynamically.
    """
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

        # Redifine process identifier
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
            if parameter.get("role", "") in ["return", "output"]:
                self.set_parameter(
                    parameter["name"], namespace[parameter["name"]])

    def _build_expression(self) :
        """ Build the expression and corresponding namespace to execute
        properly the function attached to this process.
        """
        # Load the function from its string description
        __import__(self._func_module)
        module = sys.modules[self._func_module]
        function = getattr(module, self._func_name)

        # Build the expression namespace
        namespace = {"function": function}
        for parameter in self._parameters :
            if parameter.get("role", "") == "return":
                namespace[parameter["name"]] = None
            else :
                namespace[parameter["name"]] = self.get_parameter(
                    parameter["name"])
       
        # Build the expression
        # Start spliting input and output function parameters
        args = []
        return_values = []
        for parameter in self._parameters :
            if parameter.get("role", "") == "return":
                return_values.append(parameter["name"])
            else :
                args.append("{0}={0}".format(parameter["name"]))

        # Build the expression to evaluate
        expression = "function({0})".format(", ".join(args))

        # If we have some return values, update the expression accordingly
        if return_values: 
            return_expression = ", ".join(return_values)
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
    process_traits = {}
    for trait_item in capsul_proto:

        # Create the trait
        trait_desc = trait_item["type"]
        if "content" in trait_item:
             trait_desc += "_" + trait_item["content"]
        trait_values = trait_item.get("initializer", None)
        trait = clone_trait([trait_desc], trait_values)

        # Specify the trait
        trait.desc = trait_item.get("desc", "")
        if trait_item.get("role", "") in ["return", "output"]:
            trait.output = True
        else:
            trait.output = False
        trait.optional = False        

        # Store the created trait
        process_traits[trait_item["name"]] = trait

    # Clean the docstring
    docstring = func.__doc__
    # python 2.7 only (not working on Centos 6.4)
    # docstring = re.sub(r"<capsul>.*</capsul>", "", docstring, flags=re.DOTALL)
    res = re.search(r"<capsul>.*</capsul>.*", docstring, flags=re.DOTALL)
    if res:
        docstring = docstring.replace(docstring[res.start():res.end()],"")

    # Define the process class parameters
    class_parameters = {
        "__doc__": docstring,
        "__module__": destination_module_globals["__name__"],
        "_id":  destination_module_globals["__name__"] + "." + class_name,
        "_func_name": func.__name__,
        "_func_module": func.__module__,
        "_parameters": capsul_proto,
        "_process_traits": process_traits
    }

    # Get the process instance associated to the function
    destination_module_globals[class_name] = (
        type(class_name, (AutoProcess, ), class_parameters))


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

