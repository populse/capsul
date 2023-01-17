
.. _install_guid:

===================
CAPSUL installation
===================

.. This tutorial will walk you through the process of installing CAPSUL.
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

Prerequisite
------------

Installing Capsul on a brain new system requires that Python is installed (either Python 2 or Python 3) but also that some Python packages are installed. These dependencies are managed by `pip <https://en.wikipedia.org/wiki/Pip_%28package_manager%29>`_ or by `setup.py <https://stackoverflow.com/questions/1471994/what-is-setup-py>`_. But one of the dependency (the `traits Python module <http://code.enthought.com/projects/traits/>`_) requires some compilation during installation. Therefore, before installing Capsul is it necessary to install compilation packages as well as Python development package. In this document, we give the procedure for installation on a bare Debian based Linux distribution (it has been tested on Ubuntu 16.04).


**Python 3 :**

.. code-block:: shell

   sudo apt-get install python3-dev build-essential

**Python 2 :**

.. code-block:: shell

   sudo apt-get install python-dev build-essential

On the following commands, we use ``python`` command name indiferently for Python 2 and Python 3. For systems where Python 3 is not the default version, it may be necessary to use another command such as ``python3``.

Install system-wide
-------------------

**From PyPI**

.. code-block:: shell

   sudo apt-get install python-pip # On Ubuntu 16.04, use python3-pip for Python 3 
   sudo pip install capsul # On Ubuntu 16.04, use pip3 for Python 3
    
**From source**

.. code-block:: shell

   sudo apt-get install git
   git clone https://github.com/populse/capsul.git /tmp/capsul
   cd /tmp/capsul
   python setup.py install # On Ubuntu 16.04, use python3 for Python 3
   cd /tmp
   rm -r /tmp/capsul

Install user-wide
-------------------

**From PyPI**

.. code-block:: shell

   sudo apt-get install python-pip # On Ubuntu 16.04, use python3-pip for Python 3 
   pip install --user capsul # On Ubuntu 16.04, use pip3 for Python 3
    
**From source**

.. code-block:: shell

   sudo apt-get install git
   git clone https://github.com/populse/capsul.git /tmp/capsul
   cd /tmp/capsul
   python setup.py install --user
   cd /tmp
   rm -r /tmp/capsul

Install with virtualenv
-----------------------

**For Python 3**

.. code-block:: shell

   sudo apt-get install python3-venv
   python3 -m venv /tmp/venv # Choose your installation directory instead of /tmp/venv
   /tmp/venv/bin/pip install capsul
    
**For Python 2**

.. code-block:: shell

   sudo apt-get install python-virtualenv
   virtualenv /tmp/venv # Choose your installation directory instead of /tmp/venv
   /tmp/venv/bin/pip install capsul
