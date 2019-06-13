##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
The high-level capsul.api module pre-imports the main objects from several sub-modules:

Classes
-------

* :class:`~capsul.process.process.Process`
* :class:`~capsul.process.process.NipypeProcess`
* :class:`~capsul.process.process.ProcessResult`
* :class:`~capsul.process.process.FileCopyProcess`
* :class:`~capsul.process.process.InteractiveProcess`
* :class:`~capsul.pipeline.pipeline.Pipeline`
* :class:`~capsul.pipeline.pipeline_nodes.Plug`
* :class:`~capsul.pipeline.pipeline_nodes.Node`
* :class:`~capsul.pipeline.pipeline_nodes.ProcessNode`
* :class:`~capsul.pipeline.pipeline_nodes.PipelineNode`
* :class:`~capsul.pipeline.pipeline_nodes.Switch`
* :class:`~capsul.pipeline.pipeline_nodes.OptionalOutputSwitch`
* :class:`~capsul.study_config.study_config.StudyConfig`

Functions
---------

* :func:`capsul_engine`
* :func:`get_process_instance`
* :func:`find_processes`

'''

from capsul.process.process import (Process, NipypeProcess, ProcessResult,
                                    FileCopyProcess, InteractiveProcess)
from capsul.pipeline.pipeline import Pipeline
from capsul.pipeline.pipeline_nodes import Plug
from capsul.pipeline.pipeline_nodes import Node
from capsul.pipeline.pipeline_nodes import ProcessNode
from capsul.pipeline.pipeline_nodes import PipelineNode
from capsul.pipeline.pipeline_nodes import Switch
from capsul.pipeline.pipeline_nodes import OptionalOutputSwitch
from capsul.engine import capsul_engine
from capsul.study_config.process_instance import get_process_instance
from capsul.study_config.study_config import StudyConfig
from capsul.utils.finder import find_processes


