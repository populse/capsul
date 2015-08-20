#! /usr/bin/env python
##########################################################################
# CASPER - Copyright (C) AGrigis, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
#
# From http://notionbox.de/detail/6/
##########################################################################

# Xml import
import xml.dom.minidom


def xmltodict(xmlstring):
    doc = xml.dom.minidom.parseString(xmlstring)
    remove_whitespace_nodes(doc.documentElement)
    return elementtodict(doc.documentElement)


def elementtodict(parent, **kwargs):
    child = parent.firstChild
    if (not child):
        return kwargs
    elif (child.nodeType == xml.dom.minidom.Node.TEXT_NODE):
        return child.nodeValue

    d = {}
    while child is not None:
        if (child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE):
            if child.tagName not in d:
                d[child.tagName] = []
            for name, value in kwargs.items():
                if name not in d:
                    d[name] = [value]
            extra_attributes = {}
            if child.attributes is not None:
                for attribute in child.attributes.values():
                    extra_attributes[attribute.name] = attribute.value
            d[child.tagName].append(elementtodict(child, **extra_attributes))
        child = child.nextSibling
    return d


def remove_whitespace_nodes(node, unlink=True):
    remove_list = []
    for child in node.childNodes:
        if child.nodeType == xml.dom.Node.TEXT_NODE and not child.data.strip():
            remove_list.append(child)
        elif child.hasChildNodes():
            remove_whitespace_nodes(child, unlink)
    for node in remove_list:
        node.parentNode.removeChild(node)
        if unlink:
            node.unlink()
