..  CAPSUL documentation master file, created by
    sphinx-quickstart on Wed Sep  4 12:18:01 2013.
    You can adapt this file completely to your liking, but it should at least
    contain the root `toctree` directive.


CAPSUL
=======

Capsul is a free and open-source `Python <http://python.org>`_ library for encapsulating algorithms and chain them in pipelines. It has unique features for building and dealing with complex pipelines. It is designed to make it easy to execute pipelines in various environments ranging from a local computer to a remote computing center. Capsul is connected to :somaworkflow:`soma-workflow <index.html>` in order to manage all the difficulties of running a lot of pipelines in parallel.

* doc of the current stable release: http://brainvisa.info/capsul/
* sources on gitHub: https://github.com/populse/capsul


Main features
-------------

* Althrough written in Python, Capsul does not force algorithms to be written in Python language: pipeline nodes can run any software program. However Capsul provides facilities for Python: a pipeline node can be a simple Python function.

* A parameters completion system helps to automatically fill parameters from a set of common attributes.

* An iteration system allows to iterate runs, or pipeline nodes, over a set of parameters configurations.

* Capsul provides a GUI (graphical user interface) to display pipelines structure in a boxes and links representation, to enter parameters, to iterate runs... The GUI allows basic pipeline edition and graphical building.

* Pipelines can be saved as XML files. They can thus be written either as Python source files, or as XML files.

* Pipeline execution can optionally make use of :somaworkflow:`soma-workflow <index.html>`, which manages execution dependencies between pipeline nodes and can run in parallel independent ones, can run and monitor pipelines either locally or remotely on a distant computing resource (a cluster for instance).

* Capsul has a compatibility with `Nipype <http://nipype.readthedocs.io/en/latest/>`_ interfaces which can be directly used as pipeline nodes.


Technical features
------------------

* Capsul is compatible with Python 2 (>= 2.7) and Python 3 (>= 3.4).

* The Gui is based on `Qt <https://www.qt.io/developers/>`_ and can use `PyQt4 <https://riverbankcomputing.com>`_, `PyQt5 <https://riverbankcomputing.com>`_, or `PySide <https://wiki.qt.io/PySide>`_.

* Most dependencies are optional: Gui (Qt/PyQt), NiPype, and Soma-Workflow, can be disabled, with the main pipelining features still working. The only mandatory dependency is :somabase:`Soma-Base <index.html>`, which is developed by the same team (at Neurospin) and can be regarded as an independent basis for Capsul.


Documentation contents
----------------------

.. toctree::
    :maxdepth: 1

    installation
    documentation
    status


License
-------

CAPSUL is released under the `CeCILL-B <http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html>`_ software license, which is much similar to the BSD license.
