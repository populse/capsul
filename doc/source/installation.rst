
.. _install_guid:

====================
Installing `CAPSUL`
====================

This tutorial will walk you through the process of intalling CAPSUL...

  * :ref:`Install an official release <install_release>`. This
    is the best approach for users who want a stable version.

  * :ref:`Install the latest development version
    <install_development>`. This is best for users who want to contribute
    to the project.


.. _install_release:

Installing a stable version
==============================





.. _install_development:

Installing the current version
===============================

Nightly build packages are available at: 
http://nsap.intra.cea.fr/resources/ 

Install the python package with *pip*
-------------------------------------

**First find the package**
  * Choose the desired package, for instance `capsul-0.0.1.dev.tar.gz`.
  * You have now the full url of the nightly build package you want to 
    install: 
    url = http://nsap.intra.cea.fr/resources/capsul-0.0.1.dev.tar.gz 

**Install the package without the root privilege**

>>> pip install --user --verbose $url
>>> export PATH=$PATH:$HOME/.local/bin

**Install the package with the root privilege**

>>> pip install --verbose $url

**When reinstalling locally the package first do**

>>> pip uninstall capsul

Install the debian package with *dpkg*
--------------------------------------

**First find the package**
  * Choose the desired package, for instance `capsul-0.0.1.dev-1_all.tar.gz`.
  * You have now the full url of the nightly build package you want to 
    install:
    url = http://nsap.intra.cea.fr/resources/capsul-0.0.1.dev-1_all.tar.gz

**Install the package with the root privilege**

>>> sudo dpkg -i python-capsul_0.0.1-1_all.deb









