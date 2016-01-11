##########################################################################
# NSAp - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os

# Docutils import
from docutils import nodes
from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from docutils.statemachine import ViewList


# Add node
class link_to_block(nodes.Admonition, nodes.Element):
    """ Node for inserting a link to button."""
    pass


# Add directive
class LinkToBlock(BaseAdmonition):
    """ Hidden technical block"""
    node_class = link_to_block
    has_content = False
    required_arguments = 1
    optional_arguments = 2
    final_argument_whitespace = True
    option_spec = {
        "right-side": bool,
        "label": str
    }

    def run(self):
        # Construct an empty node
        new_content = ViewList()
        ref = u":ref:`{0} <{1}>`".format(
            self.options.get("label", "Link To"),
            "".join(self.arguments))
        new_content.append(ref, source=self.content)
        self.content = new_content
        return super(LinkToBlock, self).run()


# Add html writer
def visit_ltb_html(self, node):
    """ Visit link to block"""   
    # Generate the html div
    position = node.get("right-side", True)
    self.body.append("<div class='{0}'>".format(
        "buttonNext" if position else "buttonPrevious"))


def depart_ltb_html(self, node):
    """ Depart link to block"""
    # Add close div
    self.depart_admonition(node)


# Register new directive
def setup(app):
    app.add_directive("link-to-block", LinkToBlock)
    app.add_node(link_to_block, html=(visit_ltb_html, depart_ltb_html))
