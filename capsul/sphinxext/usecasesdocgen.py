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
import inspect
import ast
import os
import logging
import six
from six.moves import range

# Define logger
logger = logging.getLogger(__file__)


class UseCasesHelperWriter(object):
    """ A basic class to convert the pilot codes to rst use cases
    """
    def __init__(self, pilots, rst_extension=".rst"):
        """ Initialize the UseCasesHelper class

        Parameters
        ----------
        pilots: list of @function (mandatory)
            list of pilot functions.
        rst_extension : string (optional)
            Extension for reST files, default '.rst'.
        """
        self.pilots = pilots
        self.rst_extension = rst_extension

    def getsource(self, function):
        """ Method that returns the source code of a function

        Parameters
        ----------
        function: @function (mandatory)
            a python function.

        Returns
        -------
        srccode: str
            the function source code.
        """
        return inspect.getsource(function)

    def generate_usecases_doc(self, src_code, module_name):
        """ Make autodoc documentation of pilots

        Parameters
        ----------
        src_code : string
            pilot source code.

        Returns
        -------
        ad : string
            the use case reST formatted documentation.
        """
        # First parse the pilot function code
        code_tree = ast.parse(src_code).body
        pilot_tree = code_tree[0].body

        # Then reST formatting
        lines = src_code.splitlines()
        nb_lines = len(lines)
        ad = ".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n"
        ad += ":orphan:\n\n"
        ad += ".. _example_{0} :\n\n".format(module_name)

        line_start_code = 0
        line_end_code = 0
        is_header = True
        full_code = "# The full use case code: {0}\n".format(module_name)
        for code_item in pilot_tree:
            if (isinstance(code_item, ast.Expr) and
                    isinstance(code_item.value, ast.Str)):
                # Find End code line
                code_value = lines[line_start_code:line_end_code]
                for line_index in range(line_end_code, nb_lines):
                    clean_line = lines[line_index].lstrip()
                    if clean_line[:3] in ["'''", '"""']:
                        break
                    else:
                        code_value.append(lines[line_index])

                # Add code value to reST documentation
                if line_start_code != 0:
                    full_code += "\n".join(code_value)
                    ad += "::\n\n"
                    ad += "\n".join(code_value)
                    ad += "\n\n"

                # Add expand box with full code in header
                if is_header:
                    code = ".. hidden-code-block:: python\n"
                    code += "    :starthidden: True\n\n"
                    code += "    $FULL_CODE"

                # Add comments to reST
                comment = inspect.cleandoc(code_item.value.s)
                # Insert full code after main title
                if is_header:
                    comment = comment.splitlines()
                    comment.insert(3, code)
                    comment.insert(3, "")
                    ad += "\n".join(comment)
                    is_header = False
                else:
                    ad += comment
                ad += "\n\n"
                line_start_code = code_item.lineno

            else:
                line_end_code = code_item.lineno + 1

        # Add the end of the file
        if line_start_code != nb_lines:
            full_code += "\n".join(lines[line_start_code:])
            ad += "::\n\n"
            ad += "\n".join(lines[line_start_code:])
            ad += "\n\n"

        # Insert full use case code
        ad = ad.replace("$FULL_CODE", full_code)

        return ad

    def write_usecases_docs(self, outdir=None, returnrst=False):
        """ Generate Use Cases reST files.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files.
            We create automatic filenames for each Use case.
        returnrst: bool (optional, default False)
            if True return the rst string documentation,
            otherwise write it to disk.
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

        # Write reST use cases documentation
        written_usecases = []
        for pilot in self.pilots:

            # Information message
            logger.info("Processing pilot '{0}' in module '{1}'...".format(
                pilot.__name__, pilot.__module__))

            # Generate reST
            uid = pilot.__module__ + "." + pilot.__name__
            code_str = self.getsource(pilot)
            use_case_str = self.generate_usecases_doc(code_str, uid)
            title_str = code_str.splitlines()[3].strip()
            if not use_case_str:
                continue

            # Write to file
            if returnrst is False:
                outfile = os.path.join(outdir, uid + self.rst_extension)
                fileobj = open(outfile, "wt")
                fileobj.write(use_case_str)
                fileobj.close()
            else:
                rstdoc[uid] = use_case_str

            # Update the list of written use cases
            written_usecases.append((title_str, uid))

        # Update the class attribute containing the list of written use cases
        self.written_usecases = written_usecases

        if returnrst is True:
            return rstdoc

    def write_index(self, outdir, froot="index", relative_to=None,
                    rst_extension=".rst"):
        """ Make a reST API index file from written files

        Parameters
        ----------
        outdir : string (mandatory)
            Directory to which to write generated index file
        froot : string (optional)
            root (filename without extension) of filename to write to
            Defaults to 'index'.  We add ``rst_extension``.
        relative_to : string
            path to which written filenames are relative.  This
            component of the written file path will be removed from
            outdir, in the generated index.  Default is None, meaning,
            leave path as it is.
        rst_extension : string (optional)
            Extension for reST files, default '.rst'
        """
        if self.written_usecases is None:
            raise ValueError('No modules written')
        # Get full filename path
        path = os.path.join(outdir, froot + rst_extension)
        # Path written into index is relative to rootpath
        if relative_to is not None:
            relpath = outdir.replace(relative_to + os.path.sep, "")
        else:
            relpath = outdir
        idx = open(path, "wt")
        w = idx.write
        w(".. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n")
        w(".. raw:: html\n\n")

        table = ["<!-- Block section -->"]
        table.append("<table border='1' class='docutils' style='width:100%'>")
        table.append("<colgroup><col width='25%'/><col width='75%'/>"
                     "</colgroup>")
        table.append("<tbody valign='top'>")

        for title_str, f in self.written_usecases:

            # generate the relative pipeline name
            relative_uid = ".".join(f.split(".")[2:])

            ref = os.path.join(relpath, f + ".html")
            table.append("<tr class='row-odd'>")
            table.append(
                "<td><a class='reference internal' href='{0}'>"
                "<em>{1}</em></a></td>\n".format(ref, relative_uid))
            table.append("<td>{0}</td>".format(title_str))
            table.append("</tr>")

        table.append("</tbody>\n\n")
        table.append("</table>")

        table_with_indent = [" " * 4 + line for line in table]

        w("\n".join(table_with_indent))
        idx.close()
