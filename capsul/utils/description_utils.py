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

# Xml import
import xml.dom.minidom
from .xmltodict import xmltodict


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
    """ Parse the given docstring to get the <unit> xml-like structure.

    Parameters
    ----------
    docstring: str (mandatory)
        a string where we will try to found the <process> xml-like structure.

    Returns
    -------
    parameters: dict
        the process trait descriptions.
    """
    # Find the <process> xml-like structure in the docstring
    capsul_start = docstring.rfind("<unit>")
    capsul_end = docstring.rfind("</unit>")
    capsul_description = docstring[
        capsul_start: capsul_end + len("</unit>")]

    # Parse the xml structure and put each xml dictionnary formated item in a
    # list
    parameters = []

    # If no description has been found in the doctring, return an empty
    # parameter list
    if not capsul_description:
        return parameters

    # Find all the xml 'input', 'output' and 'return' tag elements
    document = xml.dom.minidom.parseString(capsul_description)
    for node in document.childNodes[0].childNodes:

        # Assert we have an 'item' node
        if (node.nodeType != node.ELEMENT_NODE or
                node.tagName not in ["input", "output"]):
            continue

        # Set each xml 'item' tag element in the parameter list
        parameters.append(
            dict(node.attributes.items() + [("role", node.tagName)]))

    return parameters


def load_xml_description(xmlfile):
    """ Load the given xml description.

    Parameters
    ----------
    xmlfile: string (mandatory)
        a file containing a xml formated description.

    Returns
    -------
    desc: dict
        the loaded xml structure description.
    """
    # Check that a valid description file has been specified
    if not os.path.isfile(xmlfile):
        raise IOError("The input xml description '{0}' is not a valid "
                      "file.".format(xmlfile))

    # Parse the xml file
    with open(xmlfile) as open_description:
        desc = xmltodict(open_description.read())

    return desc


def is_io_control(controldesc):
    """ Check if the control description is attached to the pipeline
    inputs/outputs.

    A box input/output control is specified as '<box_control>' while a
    pbox inner box control is specified as '<box_name>.<box_control_name>'.

    Parameters
    ----------
    controldesc: string (mandatory)
        a control description.

    Returns
    -------
    is_pbox_control: bool
        True if a pbox input/output control is detected.
    """
    if "." not in controldesc:
        return True
    else:
        return False


def parse_link(linkrep):
    """ Parse a box link.

    Parameters
    ----------
    linkrep: str (mandatory)
        a link representation of the form
        'box_from.control_name->box_to.input_control_name' or
        'input_control_name->box_to.input_control_name' or
        'box_from.output_control_name->output_control_name'

    Returns
    -------
    output: 4-uplet
        tuple containing the source/destination box name and control.
        A pbox name is virtually represented by ''.


    """
    # Split source and destination descriptions
    src, dest = linkrep.split("->")

    # Parse the source and destination control descriptions
    src_box_name, src_control_name = parse_controldesc(src)
    dest_box_name, dest_control_name = parse_controldesc(dest)

    return src_box_name, src_control_name, dest_box_name, dest_control_name


def parse_controldesc(controldesc):
    """ Parse a control description.

    Parameters
    ----------
    controldesc: str (mandatory)
        the description plug we want to load 'node.plug'

    Returns
    -------
    box_name: string
        the box name.
    control_name: string
        the associated control name.
    """
    # Parse the plug description
    dot = controldesc.find(".")

    # Check if its a pbox input/output control
    if dot < 0:
        box_name = ""
        control_name = controldesc
    else:
        box_name = controldesc[:dot]
        control_name = controldesc[dot + 1:]

    return box_name, control_name
