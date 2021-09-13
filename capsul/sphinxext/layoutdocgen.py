# -*- coding: utf-8 -*-
##########################################################################
# CAPSUL - CAPS - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from __future__ import absolute_import
import os
import sys
import six
from docutils.core import publish_parts
import logging
import traceback


class LayoutHelperWriter(object):
    """ A basic class to create sphinx layout and associated index.
    """
    def __init__(self, module_names, root_module_name, rst_extension=".rst"):
        """ Initialize the LayoutHelperWriter class

        Parameters
        ----------
        module_names: list of str (mandatory)
            list of modules defined in the project
        root_module_name: str (mandatory)
            the name of the python package
        rst_extension : string (optional)
            Extension for reST files, default '.rst'
        """
        self.module_names = module_names
        self.rst_extension = rst_extension
        self.root_module_name = root_module_name
        self.rst_section_levels = ['*', '=', '-', '~', '^']

    def generate_index_entry(self, module_name, indent=4):
        """ Make autodoc documentation of pilots

        Parameters
        ----------
        module_name: string
            the name of the module we want to index
        ident: int
            the number of blank prefix

        Returns
        -------
        ad : string
            the reST formatted index description.
        """
        # Try to get the module description
        full_module_name = "{0}.{1}".format(self.root_module_name, module_name)
        try:
            __import__(full_module_name)
        except ImportError:
            exc_info = sys.exc_info()
            logging.error("".join(traceback.format_exception(*exc_info)))
            logging.error(
                "Can't load module {0}".format(full_module_name))
        module = sys.modules[full_module_name]
        description = module.__doc__

        # Then reST formatting
        spacer = " " * 4
        ad = spacer + "<div class='span6 box'>\n"
        ad += spacer + "<h2><a href='{0}/index.html'>\n".format(module_name)
        ad += spacer + "{0} module\n".format(module_name)
        ad += spacer + "</a></h2>\n"
        ad += spacer + "<blockquote>\n"
        if description is not None:
            ad += spacer + "{0}\n".format(("\n" + spacer).join(
                self.rst2html(description).splitlines()))
        ad += spacer + "</blockquote>\n"
        ad += spacer + "</div>\n"

        return ad

    def title_for(self, title):
        """ Create a title from a underscore-separated string.

        Parameters
        ----------
        title: str (mandatory)
            the string to format.

        Returns
        -------
        out: str
            the formatted string.
        """
        return title.replace("_", " ").capitalize()

    def rst2html(self, rst):
        """ Convert a rst formatted string to an html string.

        Parameters
        ----------
        rst: str (mandatory)
            the rst formatted string.

        Returns
        -------
        out: str
            the html formatted string.
        """
        parts = publish_parts(rst, writer_name="html")
        return parts["body_pre_docinfo"] + parts["body"]

    def write_layout(self, outdir):
        """Generate the sphinx layout.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files
        """
        # Check if output dir exists
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Get the layout template
        layout_file = os.path.join(
            os.path.dirname(__file__), "resources", "layout.html")

        # Top selection panel
        indices = [
            """<li><a href="{{{{ pathto('generated/{0}/index') }}}}">"""
            """{1}</a></li>""".format(x, self.title_for(x))
            for x in self.module_names]

        # Project description
        try:
            __import__(self.root_module_name)
        except ImportError:
            exc_info = sys.exc_info()
            logging.error("".join(traceback.format_exception(*exc_info)))
            logging.error(
                "Can't load module {0}".format(self.root_module_name))
        module = sys.modules[self.root_module_name]
        release_info = {}
        exec(compile(open(os.path.join(module.__path__[0], "info.py"), "rb").read(), os.path.join(module.__path__[0], "info.py"), 'exec'), release_info)

        # Carousel items
        carousel_items_path = os.path.join(
            module.__path__[0], os.pardir, "doc", "source", "_static",
            "carousel")
        carousel_items = [item for item in os.listdir(carousel_items_path)]
        images = []
        indicators = []
        for cnt, item in enumerate(carousel_items):
            if cnt == 0:
                indicators.append(
                    "<li data-target='#examples_carousel' data-slide-to='0' "
                    "class='active'></li>")
                images.append(
                    "<div class=\"active item\">"
                    "<a href=\"{{pathto('index')}}\">"
                    "<img src=\"{{ pathto('_static/carousel/%s', 1) }}\">"
                    "</div></a>" % item)
            else:
                indicators.append(
                    "<li data-target='#examples_carousel' data-slide-to='{0}' "
                    "</li>".format(cnt))
                images.append(
                    "<div class=\"item\"><a href=\"{{pathto('index')}}\">"
                    "<img src=\"{{ pathto('_static/carousel/%s', 1) }}\">"
                    "</a></div>" % item)

        # Create correspondence mapping
        layout_info = {
            "NAME_LOWER": self.root_module_name,
            "NAME_UPPER": self.root_module_name.upper(),
            "INDEX": "\n".join(indices),
            "CAROUSEL_INDICATORS": "\n".join(indicators),
            "CAROUSEL_IMAGES": "\n".join(images),
            "DESCRIPTION": self.rst2html(release_info["LONG_DESCRIPTION"]),
            "LOGO": self.root_module_name,
        }

        # Get full output filename path
        path = os.path.join(outdir, "layout.html")

        # Start writing the index
        idx = open(path, "wt")
        w = idx.write

        # Edit the template
        with open(layout_file) as open_file:
            s = "".join(open_file.readlines())
            for key, value in six.iteritems(layout_info):
                s = s.replace("%({0})s".format(key), value)
            w(s)

        # Close the open file
        idx.close()

    def write_installation(self, outdir):
        """Generate the installation recommendations.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files
        """
        # Check if output dir exists
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Get the layout template
        layout_file = os.path.join(
            os.path.dirname(__file__), "resources", "installation.rst")

        # Generate title
        title = "Installing `{0}`".format(self.root_module_name.upper())
        title = [self.rst_section_levels[1] * len(title), title,
                 self.rst_section_levels[1] * len(title)]

        # Create correspondence mapping
        layout_info = {
            "NAME_LOWER": self.root_module_name,
            "NAME_UPPER": self.root_module_name.upper(),
            "TITLE": "\n".join(title),
        }

        # Get full output filename path
        path = os.path.join(outdir, "installation.rst")

        # Start writing the index
        idx = open(path, "wt")
        w = idx.write

        # Edit the template
        with open(layout_file) as open_file:
            s = "".join(open_file.readlines())
            for key, value in six.iteritems(layout_info):
                s = s.replace("%({0})s".format(key), value)
            w(s)

        # Close the open file
        idx.close()

    def write_index(self, outdir, froot="index", rst_extension=".rst"):
        """ Make a reST API index file from python modules

        Parameters
        ----------
        outdir : string (mandatory)
            Directory to which to write generated index file
        froot : string (optional)
            root (filename without extension) of filename to write to
            Defaults to 'index'.  We add ``rst_extension``.
        rst_extension : string (optional)
            Extension for reST files, default '.rst'
        """
        # Check output directory
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Get full output filename path
        path = os.path.join(outdir, froot + rst_extension)

        # Start writing the index
        idx = open(path, "wt")
        w = idx.write

        # Header
        w(".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n")
        w(".. raw:: html\n\n")
        w("    <div class='container-index'>\n\n")
        title = "Documentation of the {0} Pipelines\n".format(
            self.root_module_name.upper())
        w(title)
        w(self.rst_section_levels[1] * len(title) + "\n\n")

        # Modules
        w(".. raw:: html\n\n")
        w("    <!-- Block section -->\n\n")
        for cnt, module_name in enumerate(self.module_names):
            if cnt % 2 == 0:
                w("    <div class='row-fluid'>\n\n")
            w(self.generate_index_entry(module_name))
        w("\n    </div>\n")
        w("\n    </div>")

        # Close the open file
        idx.close()
