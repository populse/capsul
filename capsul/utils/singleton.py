#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Singleton pattern.

- author: Yann Cointepas
- organization: `NeuroSpin <http://www.neurospin.org>`_ and 
  `IFR 49 <http://www.ifr49.org>`_
- license: `CeCILL version 2 <http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>`_
'''
from __future__ import absolute_import
__docformat__ = 'restructuredtext en'


class Singleton( object ):
  '''
  Implements the singleton pattern. A class deriving from ``Singleton`` can
  have only one instance. The first instanciation will create an object and
  other instanciations return the same object. Note that the :py:meth:`__init__`
  method (if any) is still called at each instanciation (on the same object).
  Therefore, :py:class:`Singleton` derived classes should define 
  :py:meth:`__singleton_init__`
  instead of :py:meth:`__init__` because the former is only called once.
  
  Example::

    from singleton import Singleton
    
    class MyClass( Singleton ):
      def __singleton_init__( self ):
        self.attribute = 'value'
    
    o1 = MyClass()
    o2 = MyClass()
    print o1 is o2
  
  '''
  def __new__( cls, *args, **kwargs ):
    if '_singleton_instance' not in cls.__dict__:
      cls._singleton_instance = super(Singleton, cls).__new__( cls )
      singleton_init = getattr( cls._singleton_instance, 
                               '__singleton_init__', None )
      if singleton_init is not None:
        singleton_init( *args, **kwargs )
    return cls._singleton_instance

  def __init__( self, *args, **kwargs ):
    '''
    The __init__ method of :py:class:`Singleton` derived class should do 
    nothing. 
    Derived classes must define :py:meth:`__singleton_init__` instead of __init__.
    '''
