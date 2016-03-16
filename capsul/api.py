##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from capsul.process.process import (Process, NipypeProcess, ProcessResult,
                                    FileCopyProcess)
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import Plug
from capsul.pipeline.pipeline_nodes import Node
from capsul.pipeline.pipeline_nodes import ProcessNode
from capsul.pipeline.pipeline_nodes import PipelineNode
from capsul.pipeline.pipeline_nodes import Switch
from capsul.process.loader import get_process_instance
from capsul.utils.finder import find_processes

