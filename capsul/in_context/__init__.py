# -*- coding: utf-8 -*-
'''
The ``in_context`` module provides functions to call some external software from Capsul processes (SPM, FSL, etc.). The main functions perform calls to the software in a similar way as ``subprocess`` functions (:class:`~subprocess.Popen`, :func:`~subprocess.call`, :func:`~subprocess.check_call` and :func:`subprocess.check_output`). These functions are only valid when the software environment *context* is activated.
Activating the context is normally done using the ``with`` statement on a :class:`~capsul.engine.CapsulEngine` object::

    from capsul.engine import capsul_engine
    from capsul.in_context.fsl import fsl_check_call

    ce = capsul_engine()
    # .. configure it ...

    with ce:
        fsl_check_call(['bet', '-h'])

'''
