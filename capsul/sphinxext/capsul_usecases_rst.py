# -*- coding: utf-8 -*-
##########################################################################
# CAPSUL - CAPS - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

"""Script to auto-generate use cases rst documentation.
"""
from __future__ import print_function

# System import
from __future__ import absolute_import
import os
import sys
from optparse import OptionParser
import logging

# Get the module name passed in argument
default_output_dir = os.path.join("source", "generated")
parser = OptionParser(usage="usage: %prog -i <inputmodule>'")
parser.add_option("-i", "--imodule",
                  action="store",
                  dest="module",
                  default=None,
                  help="the name of the module we want to document.")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="set the logging level to DEBUG.")
parser.add_option("-o", "--outdir",
                  action="store",
                  dest="outdir",
                  default=default_output_dir,
                  help="output base directory. Docs will be generated in "
                  "sub-directories there, named by their module names. "
                  "default: {0}".format(
                      default_output_dir))
(options, args) = parser.parse_args()
if options.module is None:
    parser.error("Wrong number of arguments.")

# Define logger
logger = logging.getLogger(__file__)
if options.verbose:
    logging.basicConfig(
        level=logging.DEBUG,
        format="{0}::%(asctime)s::%(levelname)s::%(message)s".format(
            logger.name))
else:
    logging.basicConfig(
        level=logging.INFO,
        format="{0}::%(asctime)s::%(levelname)s::%(message)s".format(
            logger.name))

base_outdir = options.outdir

# Capsul import
from capsul.sphinxext.usecasesdocgen import UseCasesHelperWriter
from capsul.sphinxext.load_pilots import load_pilots


# Get all the pilots
# > first find the package location
try:
    __import__(options.module)
except ImportError:
    logging.error("Can't load module {0}".format(options.module))
    exit(2)
module = sys.modules[options.module]
module_path = module.__path__[0]
# > then load the pilots
pilots = load_pilots(module_path, module_path, options.module)

# Sort all the pilots
# > from the pilots full path 'm1.m2.pipeline' get the module name 'm2'
module_names = set([x.split(".")[1] for x in pilots])
# > sort each pilot according to its module name.
# > the result is a dict of the form 'd[m2] = [pilot1, ...]'
sorted_pilots = {}
for module_name, pilots in pilots.items():
    name = module_name.split(".")[1]
    sorted_pilots.setdefault(name, []).extend(pilots)

# Generate use cases reST
for module_name, pilots in sorted_pilots.items():

    # Where the documentation will be written: a relative path from the
    # makefile
    outdir = os.path.join(base_outdir, module_name, "use_cases")

    # Generate the writer object
    docwriter = UseCasesHelperWriter(pilots)
    docwriter.write_usecases_docs(outdir)

    # Create an index that will be inserted in the module main index.
    # The file format doesn't matter since we will make an include but prevent
    # Sphinx to convert such files
    docwriter.write_index(
        outdir, "index",
        relative_to=os.path.join(base_outdir, module_name),
        rst_extension=".txt")

    # Just print a summary
    logger.info("'{0}' files written for module '{1}'.".format(
        len(docwriter.written_usecases), module_name))
