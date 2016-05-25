
.. _install_guid:

=====================
`CAPSUL` installation
=====================

.. This tutorial will walk you through the process of intalling CAPSUL.
.. 
..   * :ref:`Install an official release <install_release>`. This
..     is the best approach for users who want a stable version.
.. 
..   * :ref:`Install the latest development version
..     <install_development>`. This is best for users who want to contribute
..     to the project.
.. 
.. 
.. .. _install_release:

Installing with BrainVISA
==========================

CAPSUL is the new pipelining system of the `BrainVISA suite <http://brainvisa.info>`_. It can therefore be installed with `BrainVISA installer <http://brainvisa.info/web/download>`_.


Installing without BrainVISA
==============================

The latest stable Capsul version can be installed `with pip <https://en.wikipedia.org/wiki/Pip_%28package_manager%29>`_. Please refer to the `pip documentation <http://www.pip-installer.org/>`_ to get full installation possibilities. Here are some examples for most frequent situation.


Install in a directory
----------------------
To install Capsul in a self-content directory, we recommend to use `virtualenv <https://virtualenv.pypa.io/>`_.

>>> virtualenv my_python_modules
>>> my_python_modules/bin/pip install --upgrade capsul

Install on Linux for a single user (without administrator privilege)
--------------------------------------------------------------------

>>> pip install --user --upgrade capsul


Get source code
===============

The source code is located on GitHub: http://github.com/neurospin/capsul.









