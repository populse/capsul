:orphan:

.. _capsul_guide:

###########
User Guide
###########

The main documentation of all the proposed scripts.

Tutorial
########

Tutorial is available as a `Jupyter notebook <https://jupyter.org/>`_ (Jupyter is the new name for `IPython notebook <http://ipython.org/notebook.html>`_).

  .. ifconfig:: 'nbsphinx' in extensions

      * `See the notebook contents <../tutorial/capsul_tutorial.html>`_
      * `Download notebook <../_static/tutorial/capsul_tutorial.ipynb>`_ (for use with Jupyter)

      .. toctree::
          :hidden:

          ../tutorial/capsul_tutorial

  .. ifconfig:: 'nbsphinx' not in extensions

      * `Download notebook <../_static/tutorial/capsul_tutorial.ipynb>`_ (for use with Jupyter)

To run it, the following must be done:

* :ref:`install_guid`.
* have IPython installed.
* run the tutorial ipython notebook server, with Qt GUI support:

    .. code-block:: bash

        jupyter notebook --gui=qt my_tutorial.ipynb


.. Building processes
.. ##################
.. 
.. 
.. Building pipelines
.. ##################
.. 
.. Python API
.. ==========
.. .. 
.. Graphical display and edition
.. =============================
.. 
.. 
.. Configuration
.. #############
.. 
.. StudyConfig object, options, modules
.. ====================================
.. 
.. Data paths
.. 
.. Execution options: Soma-Workflow


Running Capsul
##############

Running as commandline
======================

CAPSUL has a commandline program to run any process, pipeline, or process iteration. It can be used from a shell, or a script. It allows to run locally, either sequentially or in parallel, or on a remote processing server using Soma-Workflow.

The program is a python module/script:

.. code-block:: bash

    python -m capsul <parameters>

It can accept a variety of options to control configuration settings, processing modes, iterations, and process parameters either through file names or via attributes and parameters completion system.

To get help, you may run it with the ``-h`` or ``--help`` option:

.. code-block:: bash

    python -m capsul -h

**Ex:**

.. code-block:: bash

    python -m capsul --swf -i /home/data/study_data --studyconfig /home/data/study_data/study_config.json -a subject=subjet01 -a center=subjects morphologist.capsul.morphologist.Morphologist

will run the Morphologist pipeline on data located in the directory ``/home/data/study_data`` using Soma-Workflow on the local computer, for subject ``subject01``

**Ex with iteration:**

.. code-block:: bash

    python -m capsul --swf -i /home/data/study_data --studyconfig /home/data/study_data/study_config.json -a subject='["subjet01", "subject02", "subject03"]' -a center=subjects -I t1mri morphologist.capsul.morphologist.Morphologist

will iterate the same process 3 times, for 3 different subjects.

To work correctly, StudyConfig settings have to be correctly defined in ``study_config.json`` including FOM completion parameters, external software, formats, etc.

Alternatively, or in addition to attributes, it is possible to pass process parameters as additional options after the process name. They can be passed either as positional arguments (given in the order the process expects), or as "keyword" arguments:

.. code-block:: bash

  python -m capsul --swf -i /home/data/study_data --studyconfig /home/data/study_data/study_config.json -a subject=subjet01 -a center=subjects morphologist.capsul.morphologist.Morphologist /home/data/raw_data/subject01.nii.gz pipeline_steps='{"importation": True, "orientation": True}'

To get help about a process, its parameters, and available attributes to control its completion:

.. code-block:: bash

  python -m capsul --process-help morphologist.capsul.morphologist.Morphologist

**Configuration:**

Capsul configuration may be specified via the ``--config`` option, or the older ``--studyconfig`` option:

.. code-block:: bash

    python -m capsul --config engine.json -a subject=subjet01 -a center=subjects morphologist.capsul.morphologist.Morphologist

The config may be imported from BrainVisa/Axon config using the process ``capsul.engine.write_engine_config``:

.. code-block:: bash

    axon-runprocess capsul://capsul.engine.write_engine_config engine.json

.. Simple, sequential execution
.. ============================
.. 
.. Distributed execution
.. =====================
.. 
.. Running on-the-fly using StudyConfig
.. ------------------------------------
.. 
.. Generating and saving workflows
.. -------------------------------


XML Specifications
##################

Processes may be functions with XML specifications for their parameters.

Pipelines can be saved and loaded as XML files.

:doc:`The specs of XML definitions can be found on this page. <xml_spec>`


Documenting CAPSUL processes and pipelines with Sphinx
######################################################

Sphinx documentation can be built automatically for all Capsul processes. See :mod:`capsul.sphinxext`.

Hints may be stored in process classes to point to the documentation. This doc may be accessed through the :class:`~capsul.qt_gui.widgets.pipeline_developper_view.PipelineDevelopperView` pipeline viewer (at least). Several mechanisms can be used to find the HTML documentation of a process or node:

* a :class:`~capsul.process.process.Process` or :class:`~capsul.pipeline.pipeline_nodes.Node` class (or instance) may contain a ``_doc_path`` attribute. It points to the HTML document corresponding to the process documentation. The path may be absolute (``/path/to/file.html``), or an URL (``https://populse.github.io/capsul/api/pipeline.html#leaveoneoutnode``), or a relative URL. In the latter case the link is relative to to root of the project documentation, found via the process or node modules hierarchy. See below.

* a module containing processes or nodes docs may contain a ``_doc_path`` attribute. It can be in any module / package level above the process / node to be documented (it will be searched upwards, starting form the process module). If found it should point to the root directory of the documentation of the project. It may be an absolute path (``/path/to/project``), or an URL (``https://populse.github.io/capsul``). Individual process / node docs will be appended to this prefix.

* If a process or node class does not provide a ``_doc_path`` attribute, but one is found in one of its parent modules, then the documentation can be looked for, following the organization of the docs auto-generated by :mod:`capsul.sphinxext`.

If a process HTML documentation is not found, then it may be replaced in documentation browsers with the process help (from its docstring).


Advanced usage
##############

:doc:`More advanced features can be found on this page. <advanced_usage>`


.. toctree::
    :hidden:

    advanced_usage
    xml_spec
