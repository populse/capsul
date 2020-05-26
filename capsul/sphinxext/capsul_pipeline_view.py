# -*- coding: utf-8 -*-
""" Script to auto-generate pipeline png representation.
"""

# System import
from __future__ import absolute_import
import os
from optparse import OptionParser
import sys
import logging
import tempfile
import soma.subprocess

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

# Capsul import
from capsul.qt_apps.utils.find_pipelines import find_pipeline_and_process
from capsul.api import StudyConfig
from capsul.pipeline import pipeline_tools
from capsul.sphinxext.pipelinedocgen import PipelineHelpWriter


# Get all caps pipelines
pipelines = find_pipeline_and_process(
    os.path.basename(options.module))["pipeline_descs"]
logger.info("Found '{0}' pipeline(s) in '{1}'.".format(
    len(pipelines), options.module))

# Sort pipelines processes
# From the pipelines full path 'm1.m2.pipeline' get there module names 'm2'
module_names = set([x.split(".")[1] for x in pipelines])
# Sort each pipeline according to its module name.
# The result is a dict of the form 'd[m2] = [pipeline1, pipeline2, ...]'.
sorted_pipelines = dict((x, []) for x in module_names)
for pipeline in pipelines:
    module_name = pipeline.split(".")[1]
    sorted_pipelines[module_name].append(pipeline)

study_config = StudyConfig(modules=StudyConfig.default_modules + ['FomConfig'])

# Generate a png representation of each pipeline.
for module_name, module_pipelines in sorted_pipelines.items():

    # this docwriter is juste used to manage short names
    docwriter = PipelineHelpWriter([], short_names=short_names)

    # Where the documentation will be written: a relative path from the
    # makefile
    short_name = docwriter.get_short_name(module_name)
    outdir = os.path.join(base_outdir, short_name,  "schema")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    # Go through all pipeline
    for module_pipeline in module_pipelines:

        # Get pipeline instance
        pipeline_instance = study_config.get_process_instance(module_pipeline)

        # Get output files
        short_pipeline = docwriter.get_short_name(module_pipeline)
        image_name = os.path.join(outdir, short_pipeline + ".png")
        pipeline_tools.save_dot_image(
            pipeline_instance, image_name, nodesep=0.1, include_io=False,
            rankdir='TB')
        logger.info("Pipeline '{0}' representation has been written at "
                    "location '{1}'.".format(module_pipeline,
                                             os.path.abspath(image_name)))

    # Just print a summary
    logger.info("Summary: '{0}' files written for module '{1}'.".format(
        len(module_pipelines), module_name))
