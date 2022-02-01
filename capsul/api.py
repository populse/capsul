# -*- coding: utf-8 -*-
'''
The high-level capsul.api module pre-imports the main objects from several sub-modules:

Classes
-------

* :class:`~capsul.process.process.Process`
* :class:`~capsul.process.process.NipypeProcess`
* :class:`~capsul.process.process.FileCopyProcess`
* :class:`~capsul.pipeline.pipeline.Pipeline`
* :class:`~capsul.pipeline.pipeline_nodes.Plug`
* :class:`~capsul.pipeline.pipeline_nodes.Node`
* :class:`~capsul.pipeline.pipeline_nodes.ProcessNode`
* :class:`~capsul.pipeline.pipeline_nodes.PipelineNode`
* :class:`~capsul.pipeline.pipeline_nodes.Switch`
* :class:`~capsul.pipeline.pipeline_nodes.OptionalOutputSwitch`

Functions
---------

* :func:`~capsul.engine.capsul_engine`
* :func:`~capsul.engine.get_process_instance`
* :func:`~capsul.utils.finder.find_processes`

'''

from __future__ import absolute_import
from .application import Capsul
from .pipeline.pipeline import Pipeline
from .pipeline.pipeline_nodes import Plug
from .pipeline.pipeline_nodes import Node
from .pipeline.pipeline_nodes import ProcessNode
from .pipeline.pipeline_nodes import PipelineNode
from .pipeline.pipeline_nodes import Switch
from .pipeline.pipeline_nodes import OptionalOutputSwitch
from .process.process import (Process, NipypeProcess,
                              FileCopyProcess,)
from .execution_context import ExecutionContext
