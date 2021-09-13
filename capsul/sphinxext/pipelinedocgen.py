# -*- coding: utf-8 -*-
from __future__ import print_function

# System import
from __future__ import absolute_import
import os
import logging
import six
from six.moves import range

# Define logger
logger = logging.getLogger(__file__)

# Capsul import
from capsul.api import get_process_instance


class PipelineHelpWriter(object):
    """ Class for automatic generation of pipeline API documentations
    in Sphinx-parsable reST format.
    """

    # Only separating first two levels
    rst_section_levels = ['*', '=', '-', '~', '^']

    def __init__(self, pipelines, rst_extension=".rst", short_names={}):
        """ Initialize package for parsing

        Parameters
        ----------
        pipelines : list (mandatory)
            list of pipeline class
        rst_extension : string (optional)
            extension for reST files, default '.rst'
        short_names : dict (optional)
            translation dict for module/pipeline file names
        """
        self.pipelines = sorted(pipelines)
        self.rst_extension = rst_extension
        self.short_names = short_names

    def generate_api_doc(self, pipeline, schema):
        """ Make autodoc documentation for a pipeline python module

        Parameters
        ----------
        pipeline : string
            python location of pipeline - e.g 'caps.fmri.PIPELINE'
        schema : string
            path to the pipeline representation image

        Returns
        -------
        ad : string
            contents of API doc
        title : string
            the fist line of the docstring
        """
        # Fiest get the pipeline instance from its string description
        pipeline_instance = get_process_instance(pipeline)

        # Get the header, ie. the first line of the docstring
        # Default title is ''
        header = pipeline_instance.__doc__
        title = ""
        if header:
            title = pipeline_instance.__doc__.splitlines()[0]

        # Add header to tell us that this documentation must not be edited
        ad = ".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n"

        # Generate the page title: name of the pipeline
        ad += ":orphan:\n\n"

        # Set the current module
        currentmodule = ".".join(pipeline_instance.id.split(".")[:-1])
        ad += ".. currentmodule:: {0}\n\n".format(currentmodule)

        # Generate a bookmark (for cross references)
        pipeline_name = pipeline_instance.__class__.__name__
        label = pipeline + ":"
        ad += "\n.. _{0}\n\n".format(label)

        chap_title = pipeline
        ad += (chap_title + "\n" +
               self.rst_section_levels[1] * len(chap_title) + "\n\n")

        # Add a subtitle
        ad += (pipeline_name + "\n" +
               self.rst_section_levels[2] * len(pipeline_name) + "\n\n")

        # Then add the trait description
        # It will generate two sections: input and output
        ad += pipeline_instance.get_help(returnhelp=True, use_labels=True)

        # Add schema if generated
        if schema:
            schama_title = "Pipeline schema"
            ad += ("\n" + schama_title + "\n" +
                   "~" * len(schama_title) + "\n\n")
            ad += ".. image:: {0}\n".format(schema)
            ad += "    :height: 400px\n"
            ad += "    :align: center\n\n"

        return ad, title

    def write_api_docs(self, outdir=None, returnrst=False):
        """ Generate API reST files.

        Parameters
        ----------
        outdir : string (optional, default None)
            directory name in which to store files.
            Automatic filenames are created for each module.
        returnrst: bool (optional, default False)
            if True return the rst string documentation,
            otherwise write it to disk.

        Notes
        -----
        Sets self.written_modules to list of written modules
        """
        # Check output directory
        if returnrst is False:
            if not isinstance(outdir, six.string_types):
                raise Exception("If 'returnrst' is False, need a valid output "
                                "directory.")
            if not os.path.exists(outdir):
                os.makedirs(outdir)
        else:
            rstdoc = {}

        # Generate reST API
        written_modules = []
        for pipeline in self.pipelines:

            # Information message
            logger.info("Processing pipeline '{0}'...".format(pipeline))

            pipeline_short = self.get_short_name(pipeline)
            # Check if an image representation of the pipeline exists
            if returnrst is False:
                schema = os.path.join(os.pardir, "schema",
                                      pipeline_short + ".png")
                if not os.path.isfile(os.path.join(outdir, schema)):
                    schema = None
            else:
                schema = None

            # Generate the rst string description
            api_str, title_str = self.generate_api_doc(pipeline, schema)
            if not api_str:
                continue

            # Write to file
            if returnrst is False:
                outfile = os.path.join(outdir,
                                       pipeline_short + self.rst_extension)
                fileobj = open(outfile, "wt")
                fileobj.write(api_str)
                fileobj.close()
            else:
                rstdoc[pipeline] = api_str

            # Update the list of written modules
            written_modules.append((title_str, pipeline))

        # Update the class attribute containing the list of written modules
        self.written_modules = written_modules

        if returnrst is True:
            return rstdoc

    def get_short_name(self, name):
        """
        Get a short file name prefix for module/process in the
        short_names dict. Used to build "reasonably short" path/file names.
        """
        short_name = self.short_names.get(name)
        if short_name:
            return short_name
        # look for a shorter name for the longest module prefix
        modules = name.split(".")
        for i in range(len(modules)-1, 0, -1):
            path = '.'.join(modules[:i])
            short_path = self.short_names.get(path)
            if short_path:
                return '.'.join([short_path] + modules[i+1:])
        # not found
        return name

    def write_index(self, outdir, froot="index", relative_to=None,
                    rst_extension=".rst"):
        """ Make a reST API index file from the list of written files

        Parameters
        ----------
        outdir : string (mandatory)
            directory to which to write generated index file
        froot : string (optional)
            root (filename without extension) of filename to write to
            Defaults to 'index'.  We add ``rst_extension``.
        relative_to : string
            path to which written filenames are relative.  This
            component of the written file path will be removed from
            outdir, in the generated index.  Default is None, meaning,
            leave path as it is.
        rst_extension : string (optional)
            extension for reST files, default '.rst'
        """
        # Check if some modules have been written
        if self.written_modules is None:
            raise ValueError('No modules written')

        # Get full index filename path
        path = os.path.join(outdir, froot + rst_extension)

        # Path written into index is relative to rootpath
        if relative_to is not None:
            relpath = outdir.replace(relative_to + os.path.sep, "")
        else:
            relpath = outdir
        print('relpath:', relpath)

        # Information message
        logger.info("Writing index at location '{0}'...".format(
            os.path.abspath(path)))

        # Edit the index file
        idx = open(path, "wt")
        w = idx.write

        # Add header to tell us that this documentation must not be edited
        w(".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n")

        # Generate a table with all the generated modules
        # module_name (link) + first docstring line
        w(".. raw:: html\n\n")

        # Table definition
        table = ["<!-- Block section -->"]
        table.append("<table border='1' class='docutils' style='width:100%'>")
        table.append("<colgroup><col width='25%'/><col width='75%'/>"
                     "</colgroup>")
        table.append("<tbody valign='top'>")

        # Add all modules
        for title_str, f in self.written_modules:
            pipeline_short = self.get_short_name(f)
            print('title_str:', title_str, ', f:', f)
            relative_pipeline = ".".join(f.split(".")[2:])
            print('relative_pipeline:', relative_pipeline)
            ref = os.path.join(relpath, pipeline_short + ".html")
            print('ref:', ref)
            table.append("<tr class='row-odd'>")
            table.append(
                "<td><a class='reference internal' href='{0}'>"
                "<em>{1}</em></a></td>\n".format(ref, relative_pipeline))
            table.append("<td>{0}</td>".format(title_str))
            table.append("</tr>")

        # Close divs
        table.append("</tbody>\n\n")
        table.append("</table>")

        # Format the table
        table_with_indent = [" " * 4 + line for line in table]
        w("\n".join(table_with_indent))

        # Close the file
        idx.close()

    def write_main_index(self, outdir, module_name, root_module_name,
                         froot="index", rst_extension=".rst",
                         have_usecases=True):
        """ Make a reST API index file for the module

        Parameters
        ----------
        outdir : string (mandatory)
            Directory to which to write generated index file
        module_name: str (mandatory)
            The name of module from which we want to generate an index.
        root_module_name: str (mandatory)
            The python package name
        froot : string (optional)
            root (filename without extension) of filename to write to
            Defaults to 'index'.  We add ``rst_extension``.
        rst_extension : string (optional)
            Extension for reST files, default '.rst'
        """
        # Get full index filename path
        path = os.path.join(outdir, froot + rst_extension)

        # Information message
        logger.info("Writing module '{0}' index at location '{1}'...".format(
            module_name, os.path.abspath(path)))

        # Open the result index file
        idx = open(path, "wt")

        # Stat writing
        w = idx.write

        # Add header to tell us that this documentation must not be edited
        w(".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n")
        w(":orphan:\n\n")

        # Generate a title
        chap_title = " ".join([x.capitalize() for x in module_name.split("_")])
        w(chap_title + "\n" +
          self.rst_section_levels[0] * len(chap_title) + "\n\n")

        # Generate a markup
        label = module_name
        w(".. _{0}:\n\n".format(label))

        # Page use cases
        # # Generate a title
        chap_title = ":mod:`{0}.{1}`: User Guide".format(
            root_module_name, module_name)
        w(chap_title + "\n" +
          self.rst_section_levels[1] * len(chap_title) + "\n\n")

        if have_usecases:
            # # Generate a markup
            label = module_name + "_ug"
            w(".. _{0}:\n\n".format(label))
            # # Some text description
            w("Some live examples containing snippets of codes.\n\n")
            # # Include user guide index
            w(".. include:: use_cases/index%s\n\n" % rst_extension)

        # API page
        # # Generate a title
        chap_title = ":mod:`{0}.{1}`: API".format(
            root_module_name, module_name)
        w(chap_title + "\n" +
          self.rst_section_levels[1] * len(chap_title) + "\n\n")
        # # Generate a markup
        label = module_name + "_api"
        w(".. _{0}:\n\n".format(label))
        # # Some text description
        w("The API of functions and classes, as given by the "
          "docstrings.")
        if have_usecases:
            w(" For the *user guide* see the {0}_ug_ "
              "section for further details.\n\n".format(module_name))
        else:
            w("\n\n")
        # # Include pipeline and buildingblock indexes
        # ## Pipeline
        chap_title = "Pipelines"
        w(chap_title + "\n" +
          self.rst_section_levels[2] * len(chap_title) + "\n\n")
        w(".. include:: pipeline/index%s\n\n" % rst_extension)
        # ## Buildingblocks
        chap_title = "Buildingblocks"
        w(chap_title + "\n" +
          self.rst_section_levels[2] * len(chap_title) + "\n\n")
        w(".. include:: process/index%s\n\n" % rst_extension)

        # Close file
        idx.close()
