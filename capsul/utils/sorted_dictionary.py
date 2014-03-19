#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Sorted dictionary behave like a dictionary but keep the item insertion
order.

@author: Yann Cointepas
@organization: U{NeuroSpin<http://www.neurospin.org>} and U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''
__docformat__ = "epytext en"

from UserDict import UserDict
from capsul.utils.undefined import Undefined


class SortedDictionary( UserDict, object ):
  '''
  Sorted dictionary behave like a dictionary but keep the item insertion
  order.
    
  Example::
    from SortedDictionary import SortedDictionary
    sd = SortedDictionary( ( 'fisrt', 1 ), ( 'second', 2 ) )
    sd[ 'third' ] = 3
    sd.insert( 0, 'zero', 0 )
    sd.items() == [('zero', 0), ('fisrt', 1), ('second', 2), ('third', 3)]
  '''
  def __init__( self, *args ):
    '''
    Initialize the dictionary with a list of ( key, value ) pairs.
    '''
    super(SortedDictionary, self).__init__()
    #UserDict.__init__(self)
    self.sortedKeys = []
    self.data = {}
    for key, value in args:
      self[ key ] = value
      
  def keys( self ):
    '''
    @rtype: list
    @return: sorted list of keys
    '''
    return self.sortedKeys
  
  def items( self ):
    '''
    @rtype: list
    @return: sorted list of C{( key, value)} pairs
    '''
    return [x for x in self.iteritems()]

  def values( self ):
    '''
    @rtype: list
    @return: sorted list of values
    '''
    return [x for x in self.itervalues()]

  def __setitem__( self, key, value ):
    if not self.data.has_key( key ):
      self.sortedKeys.append( key )
    self.data[ key ] = value

  def __delitem__( self, key ):
    del self.data[ key ]
    self.sortedKeys.remove( key )

  def __getstate__( self ):
    return self.items()
    
  def __setstate__( self, state ):
    SortedDictionary.__init__( self, *state )

  def __iter__( self ):
    '''
    returns an iterator over the sorted keys
    '''
    return iter( self.sortedKeys )

  def iterkeys( self ):
    '''
    returns an iterator over the sorted keys
    '''
    return iter( self.sortedKeys )
  
  def itervalues( self ):
    '''
    returns an iterator over the sorted values
    '''
    for k in self:
      yield self[ k ]

  def iteritems( self ):
    '''
    returns an iterator over the sorted (key, value) pairs
    '''
    for k in self:
      try:
        yield ( k, self[ k ] )
      except KeyError:
        print '!SortedDictionary error!', self.data.keys(), self.sortedKeys
        raise

        
  def insert( self, index, key, value ):
    '''
    insert a ( C{key}, C{value} ) pair in sorted dictionary before position 
    C{index}. If C{key} is already in the dictionary, a C{KeyError} is raised.
    @type  index: integer
    @param index: index of C{key} in the sorted keys
    @param key: key to insert
    @param value: value associated to C{key}
    '''
    if self.data.has_key( key ):
      raise KeyError( key )
    self.sortedKeys.insert( index, key )
    self.data[ key ] = value

  def index(self, key):
   """
   Returns the index of the key in the sorted dictionary, or -1 if this key isn't in the dictionary.
   """ 
   try:
    i=self.sortedKeys.index(key)
   except:
    i=-1
   return i

  def clear( self ):
    '''
    Remove all items from dictionary
    '''
    del self.sortedKeys[:]
    self.data.clear()


  def sort(self, func=None):
    """Sorts the dictionary using function func to compare keys.

    @type func: function key*key->int
    @param func: comparison function, return -1 if e1<e2, 1 if e1>e2, 0 if e1==e2
    """
    self.sortedKeys.sort(func)


  def compValues(self, key1, key2):
    """
    Use this comparaison function in sort method parameter in order to sort the dictionary by values.
    if data[key1]<data[key2] return -1
    if data[key1]>data[key2] return 1
    if data[key1]==data[key2] return 0
    """
    e1=self.data[key1]
    e2=self.data[key2]
    print "comp", e1, e2
    if e1 < e2:
      return -1
    elif e1 > e2:
      return 1
    return 0
  
  
  def setdefault( self, key, value=None ):
    result = self.get( key, Undefined )
    if result is Undefined:
      self[ key ] = value
      result = value
    return result


  def pop( self, key, default=Undefined ):
    if default is Undefined:
      result = self.data.pop(key)
    else:
      result = self.data.pop(key,Undefined)
      if result is Undefined:
        return default
    self.sortedKeys.remove( key )
    return result


  def popitem( self ):
    result = self.data.popitem()
    try:
      self.sortedKeys.remove( result[0] )
    except ValueError:
      pass
    return result

  
  def __repr__( self ):
    return '{' + ', '.join( repr(k)+': '+repr(v) for k, v in self.iteritems() ) + '}'
