# -*- coding: utf-8 -*-
""" Script to auto-generate pipeline rst documentation.
"""

from __future__ import print_function

# System import
from __future__ import absolute_import
import os
from optparse import OptionParser
import logging
import sys
import shutil

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
parser.add_option("-s", "--short", action="append", dest="short_names",
                  default=[],
                  help="use short prefix names for modules names. "
                  "Ex: morphologist.capsul.morphologist=morpho. "
                  "Several -s options may be specified.")
parser.add_option('--schema', action='store_true', dest='schema',
                  help='also build pipelines schemas images.')
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
short_names = dict([x.split("=") for x in options.short_names])
schema = options.schema

# Capsul import
from capsul.qt_apps.utils.find_pipelines import find_pipeline_and_process
from capsul.sphinxext.pipelinedocgen import PipelineHelpWriter

###############################################################################
# Generate shemas first
###############################################################################

if schema and shutil.which('dot'):
    # schemas need the dot tool
    import subprocess
    cmd = [sys.executable, '-m', 'capsul.sphinxext.capsul_pipeline_view',
       '-i', options.module, '-o', base_outdir]
    if options.verbose:
        cmd.append('-v')
    if options.short_names:
        for n in short_names:
            cmd += ['-s', n]
    print('generating schemas:')
    print(*cmd)
    subprocess.check_call(cmd)

# Get all pipelines and processes
descriptions = find_pipeline_and_process(os.path.basename(options.module))
pipelines = descriptions["pipeline_descs"]
processes = descriptions["process_descs"]
logger.info("Found '{0}' pipeline(s) in '{1}'.".format(
    len(pipelines), options.module))
logger.info("Found '{0}' process(es) in '{1}'.".format(
    len(processes), options.module))

###############################################################################
# Sort pipelines and processes by module names
###############################################################################

# Treat pipeline and process:
sorted_pipelines = {}
sorted_processes = {}
for modules, sorted_dict in ([pipelines, sorted_pipelines],
                             [processes, sorted_processes]):

    # From the modules full path 'm1.m2.pipeline/process' get the module
    # name 'm2'
    module_names = set([x.split(".")[1] for x in modules])

    # Sort each item according to its module name.
    # The result is a dict of the form 'd[m2] = [pipeline/process1, ...]'.
    for module_description in modules:
        module_name = module_description.split(".")[1]
        sorted_dict.setdefault(module_name, []).append(module_description)

###############################################################################
# Generate pipelines and processes reST API
###############################################################################

# Treat pipeline and process:
for sorted_modules, dtype in ([sorted_pipelines, "pipeline"],
                              [sorted_processes, "process"]):

    # Go through all modules
    for module_name, modules in sorted_modules.items():

        # Generate the writer object
        docwriter = PipelineHelpWriter(modules, short_names=short_names)

        # Where the documentation will be written: a relative path from the
        # makefile
        short_name = docwriter.get_short_name(module_name)
        outdir = os.path.join(base_outdir, short_name, dtype)
        print('short name:', short_name, ', outdir:', outdir)

        docwriter.write_api_docs(outdir)

        # Create an index that will be inserted in the module main index.
        # The file format doesn't matter since we will make an include but
        # prevent Sphinx to convert such files
        docwriter.write_index(
            outdir, "index",
            relative_to=os.path.join(base_outdir, short_name),
            rst_extension=".rst")

        # Just print a summary
        logger.info("{0}: '{1}' files written for module '{2}' at location "
                    "{3}.".format(dtype, len(docwriter.written_modules),
                                  module_name, os.path.abspath(outdir)))

###############################################################################
# Generate the main module index
###############################################################################

# First get all unique modules
modules = set(list(sorted_processes.keys()) + list(sorted_pipelines.keys()))

# Go through all unique modules
for module_name in modules:

    # Generate an empty writer object
    docwriter = PipelineHelpWriter([], short_names=short_names)

    # Where the index will be written: a relative path from the makefile
    short_name = docwriter.get_short_name(module_name)
    outdir = os.path.join(base_outdir, short_name)
    print('short name:', short_name, ', outdir:', outdir)

    docwriter.write_main_index(outdir, module_name, options.module,
                               have_usecases=False)
    logger.info("Index: an index has been written for module '{0}' at "
                "location {1}.".format(module_name, os.path.abspath(outdir)))
