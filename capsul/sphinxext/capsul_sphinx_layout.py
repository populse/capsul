# -*- coding: utf-8 -*-
##########################################################################
# CAPSUL - CAPS - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

""" Script to auto-generate sphinx layout, ie layout, documentation index and
installation index.
"""

# System import
from __future__ import absolute_import
import os
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

# Capsul import
from capsul.qt_apps.utils.find_pipelines import find_pipeline_and_process
from capsul.sphinxext.layoutdocgen import LayoutHelperWriter


# Get all pipelines and processes
descriptions = find_pipeline_and_process(os.path.basename(options.module))
pipelines = descriptions["pipeline_descs"]
processes = descriptions["process_descs"]
logger.info("Found '{0}' pipeline(s) in '{1}'.".format(
    len(pipelines), options.module))
logger.info("Found '{0}' process(es) in '{1}'.".format(
    len(processes), options.module))

# Get all the modules involved
module_names = [x.split(".")[1] for x in pipelines]
module_names.extend([x.split(".")[1] for x in processes])
module_names = set(module_names)
logger.info("Module names for layout generation '{0}'.".format(module_names))

# Create object to write the sphinx template elements
docwriter = LayoutHelperWriter(module_names, options.module)
outdir = options.outdir

###############################################################################
# Generate the sphinx main index
###############################################################################

logger.info("Generating documentation index in '{0}'.".format(
    os.path.abspath(outdir)))
docwriter.write_index(outdir, froot="documentation")

###############################################################################
# Generate installation recommendation
###############################################################################

logger.info("Generating installation index in '{0}'.".format(
    os.path.abspath(outdir)))
docwriter.write_installation(outdir)

###############################################################################
# Generate the layout
###############################################################################

logger.info("Generating layout index in '{0}'.".format(
    os.path.abspath(outdir)))
docwriter.write_layout(os.path.join(outdir, "_templates"))
