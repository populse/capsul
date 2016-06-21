:orphan:

.. _capsul_guide:

###########
User Guide
###########

The main documentation of all the proposed scripts.

Tutorial
########

Different tutorials are available as `IPython notebooks <http://ipython.org/notebook.html>`_.
Capsul may be used in two ways:

* a descriptive interface allows to develop processing bricks using simple Python functions and pipelines using a XML text description. :download:`See this notebook to demonstrate this approach <../_static/tutorial/capsul_descriptive_tutorial.ipynb>`.
* an object-oriented interface that uses Python classes programming. :download:`See this notebook to demonstrate this approach <../_static/tutorial/capsul_object_oriented_tutorial.ipynb>`. Note that this interface is compatible with the descriptive one, and allows more functionalities and tweak possibilities.

To run it, the following must be done:

* :ref:`install_guid`.
* have IPython installed.
* run the tutorial ipython notebook server, with Qt GUI support:

    ::

        ipython notebook --gui=qt my_tutorial.ipynb


Building processes
##################


Building pipelines
##################

Python API
==========

XML files
=========

Graphical display and edition
=============================


Configuration
#############

StudyConfig object, options, modules
====================================

Data paths

Execution options: Soma-Workflow


Running
#######

Simple, sequential execution
============================

Distributed execution
=====================

Running on-the-fly using StudyConfig
------------------------------------

Generating and saviong workflows
--------------------------------


Parameters completion
#####################

File Organization Model (FOM)
=============================


Iterating processing over multiple data
#######################################

