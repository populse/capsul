# -*- coding: utf-8 -*-
'''
Extension to sphinx to document Capsul processes

This moduls allows to make sphinx source to automatically document Capsul processes and pipelines. The module can be used as a commandline:

.. code-block:: bash

    python -m capsul.sphinxext.capsul_pipeline_rst -i morphologist.capsul -o processes_docs --schema

It can be automatically run when building sphinx docs (inside the sphinx-build process) by adding at the end of the ``conf.py`` file in sphinx sources:

::

    # generate pipeline and processes docs
    # we must actually write in sources for now.
    import subprocess

    module_to_document = 'morphologist.capsul'  # replace with your modules set
    sphinx_dir = os.path.dirname(__file__)
    proc_rst_dir = os.path.join(sphinx_dir, 'process_docs')
    if not os.path.exists(proc_rst_dir):
        os.makedirs(proc_rst_dir)
    cmd = [sys.executable, '-m', 'capsul.sphinxext.capsul_pipeline_rst',
          '-i', module_to_document, '-o', proc_rst_dir, '--schema']
    print('generating CAPSUL processes docs...')
    print(cmd)
    subprocess.check_output(cmd)


The documentation will include all pipelines and processes in the module to be documented (including Nipype interfaces), and will be built from the processes documentation: docstrings, and parameters descriptions (``desc`` property of processes traits), as in the processes :meth:`~capsul.process.process.Process.get_help` method. An ``index.rst`` file will be created for each sub-module of the main one, and contain links to pipelines and processes docs there.

Then within the sphinx docs sources (``index.rst`` for instance, or any other sphinx source file), you can include them:

# interestingly, sphinx lexers do not support sphinx language ;)

.. code-block:: ReST

    .. toctree::

        process_docs/morphologist/capsul/index.rst

'''
