##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import os

# CAPSUL import
from capsul.utils.xml_to_pipeline import register_pipelines
from capsul.utils.test.module import a_function_to_wrap


# Locate the files containing the pipeline descriptions
xmlpipelines = [
    os.path.join(os.path.dirname(__file__), "xml_pipeline.xml"),
    os.path.join(os.path.dirname(__file__), "xml_iterative_pipeline.xml"),
]

# Register new pipelines
register_pipelines(xmlpipelines)

