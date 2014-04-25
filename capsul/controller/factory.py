#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''Base classes for the management of association between Python objects and
factories (i.e. a function that create something for an object) taking into
account classes hierachy but without storing anything in the objects classes.
'''

from __future__ import absolute_import

from weakref import WeakKeyDictionary

class MetaFactories( type ):
  '''This is the metaclass of Factories. 
  It intercepts Factories class creation to make sure that they have
  a _global_factories attibute.'''
  
  def __new__( mcs, name, bases, dictionary ):
    if '_global_factories' not in dictionary:
      dictionary[ '_global_factories' ] = {}
    return type.__new__( mcs, name, bases, dictionary )


class Factories( object ):
  '''
  This is the base class for managing association between any Python object
  and a factory. For instance, WidgetFactories is derived from Factories and
  used to register all factories allowing to create a graphical widget for a
  Python object.
  
  There are two levels of associations between Python objects and factories
  (i.e. two dictionaries). The global factories are associated at the class
  level (for classes derived from Factories) with the register_global_factory
  method. The global factories are shared by all instances. On the other hand,
  if one wants to customize some factories for a specific context, it can
  create one Factories instance per context and use register_factory method
  to create an associtation at the instance level.
  '''
  __metaclass__ = MetaFactories
  _global_factories = {}
  

  def __init__( self ):
    super( Factories, self ).__init__()
    self._factories = WeakKeyDictionary()


  @classmethod
  def register_global_factory( cls, klass, factory ):
    '''
    Create an association between a class and a global factory.
    '''
    cls._global_factories[ klass ] = factory
  
  
  def get_global_factory(self, klass):
    '''
    Retrieve the global factory associated to a class or an instance. Only
    direct association is used. In order to take into account class hierarchy,
    one must use get_factory method.
    '''
    return self._global_factories.get(klass)
  
  
  def register_factory( self, class_or_instance, factory ):
    '''
    Create an association between a class (or an instance) and a factory.
    '''
    self._factories[ class_or_instance ] = factory
  
  
  def get_factory( self, class_or_instance ):
    '''
    Retrieve the factory associated to an object.
    First look into the object instance and then in the object class hierarchy.
    At each step a registered factory in the Factories instance is looked for.
    If there is none, self.get_global_factory is used.
    Returns None if no factory is found.
    '''
    for key in ( class_or_instance, ) + class_or_instance.__class__.__mro__:
      factory = self._factories.get( key )
      if factory is not None:
        break
      factory = self.get_global_factory( key )
      if factory is not None:
        break
    return factory
