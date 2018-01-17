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

      * `See the notebook contents <../_static/tutorial/capsul_tutorial.html>`_
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

or, especially if run with Python 2.6 which does not accept the former (it does the same otherwise):

.. code-block:: bash

    python -m capsul.run <parameters>

It can accept a variety of options to control configuration settings, processing modes, iterations, and process parameters either through file names or via attributes and paramters completion system.

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

Advanced usage
##############

:doc:`More advanced features can be found on this page. <advanced_usage>`
