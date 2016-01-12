##########################################################################
# NSAp - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging

# Docutils import
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from docutils.statemachine import ViewList

# Global counter
HTB_COUNTER = 0

# Javascript hidde code
js_showhide = """
<script type="text/javascript">
    function showhide(element){
        if (!document.getElementById)
            return

        if (element.style.display == "block")
            element.style.display = "none"
        else
            element.style.display = "block"
    };
</script>
"""


def nice_bool(arg):
    tvalues = ('true',  't', 'yes', 'y')
    fvalues = ('false', 'f', 'no',  'n')
    arg = directives.choice(arg, tvalues + fvalues)
    return arg in tvalues


# Add node
class hidden_technical_block(nodes.Admonition, nodes.Element):
    """Node for inserting hidden technical block."""
    pass


class MyError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


# Add directive
class HiddenTechnicalBlock(BaseAdmonition):
    """Hidden technical block"""
    node_class = hidden_technical_block
    has_content = True
    required_arguments = 0
    optional_arguments = 2
    final_argument_whitespace = False
    option_spec = {
        "starthidden": nice_bool,
        "label": str
    }

    def run(self):
        # Include raw item
        new_content = ViewList()
        for item in self.content:
            # Check if the item is a link to a file to be included
            if item.startswith(".. include:: "):
                # Get the path to file
                resource_path = item.replace(".. include:: ", "")
                # Try to open the file
                try:
                    fo = open(resource_path, "r")
                    # Item content is a string or buffer
                    item_content = [x.replace("\n", "")
                                    for x in fo.readlines()]
                    for string_content in item_content:
                        new_content.append(unicode(string_content),
                                           source=self.content)
                    fo.close()
                except MyError as e:
                    item_content = ("Can't open the resource file "
                                    "'{0}'".format(resource_path))
                    logging.error(item_content + e.value)
                    # Add an error item
                    new_content.append(item_content, source=self.content)
            else:
                # Just copy the source item
                new_content.append(item, source=self.content)
        # Replace old content item
        self.content = new_content
        # Call the parent class method
        return super(HiddenTechnicalBlock, self).run()


# Add html writer
def visit_htb_html(self, node):
    """Visit hidden code block"""
    # Increment the global counter in order generate a unique element id
    global HTB_COUNTER
    HTB_COUNTER += 1

    # Vist the node
    self.visit_admonition(node)

    # Get the last element of the html body
    # The one we want to edit
    technical_block = self.body[-1]

    # Get the node options
    fill_header = {
        "divname": "hiddencodeblock{0}".format(HTB_COUNTER),
        "startdisplay": "none" if node["starthidden"] else "block",
        "label": node.get("label", "[+ show/hide technical details]")
    }

    # Generate the html div
    divheader = (
        """<a href="javascript:showhide(document.getElementById"""
        """('{divname}'))">"""
        """\n{label}</a><br />"""
        """\n<div id="{divname}" style="display: {startdisplay}">"""
    ).format(**fill_header)

    # Edit the body item
    technical_block = js_showhide + divheader + technical_block

    # Reassign the last body item
    self.body[-1] = technical_block


def depart_htb_html(self, node):
    """Depart hidden technical block"""
    # Need to close two divs
    self.depart_admonition(node)
    self.depart_admonition(node)


# Register new directive
def setup(app):
    app.add_directive("hidden-technical-block", HiddenTechnicalBlock)
    app.add_node(hidden_technical_block,
                 html=(visit_htb_html, depart_htb_html))
