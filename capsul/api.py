'''
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

'''

from .debug import debug
from .process.process import (Process, NipypeProcess,
                                    FileCopyProcess,)
from .pipeline.pipeline import Pipeline
from .pipeline.pipeline_nodes import Plug
from .pipeline.pipeline_nodes import Node
from .pipeline.pipeline_nodes import Switch
from .application import Capsul, executable
from .execution_context import CapsulWorkflow
