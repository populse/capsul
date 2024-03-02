"""
The ``in_context`` module provides functions to call some external software from Capsul processes (SPM, FSL, etc.). The main functions perform calls to the software in a similar way as ``subprocess`` functions (:class:`~subprocess.Popen`, :func:`~subprocess.call`, :func:`~subprocess.check_call` and :func:`subprocess.check_output`).
The notable difference is that they use an :class:`~capsul.execution_context.ExecutionContext` object instance to get configuration from.
These functions are only run from within the :meth:`~capsul.process.Process.execute` method of a Process, which gets the context as a parameter::

    from capsul.api import Process
    from capsul.in_context.fsl import fsl_check_call

    ce = Capsul()
    # .. configure it ...
    Class MyProcess(Process):

        # [declare fields etc] ...

        def execute(self, execution_context):
            fsl_check_call(['bet', '-h'], execution_context=execution_context)

"""
