"""
The high-level capsul.api module pre-imports the main objects from several sub-modules:

Classes
-------

* :class:`~capsul.application.Capsul`
* :class:`~capsul.process.process.Process`
* :class:`~capsul.process.process.NipypeProcess`
* :class:`~capsul.process.process.FileCopyProcess`
* :class:`~capsul.pipeline.pipeline.Pipeline`
* :class:`~capsul.pipeline.pipeline_nodes.Plug`
* :class:`~capsul.pipeline.pipeline_nodes.Node`
* :class:`~capsul.pipeline.pipeline_nodes.Switch`

Functions
---------

* :func:`~capsul.debug.debug`
* :func:`~capsul.application.executable`

"""

from .application import Capsul, executable
from .debug import debug
from .execution_context import CapsulWorkflow
from .pipeline.pipeline import Pipeline
from .pipeline.pipeline_nodes import Node, Plug, Switch
from .process.process import (
    FileCopyProcess,
    NipypeProcess,
    Process,
)
