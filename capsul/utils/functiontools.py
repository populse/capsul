#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Utility classes and functions for Python callable.

- author: Yann Cointepas
- organization: `NeuroSpin <http://www.neurospin.org>`_ and 
  `IFR 49 <http://www.ifr49.org>`_
- license: `CeCILL version 2 <http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>`_
'''
__docformat__ = 'restructuredtext en'

import inspect
from itertools import izip


#-------------------------------------------------------------------------------
from capsul.utils.translation import translate as _


#-------------------------------------------------------------------------------
class Empty( object ):
  pass

#-------------------------------------------------------------------------------
class SomaPartial( object ):
  '''
  Python 2.5 introduced a very useful function: :py:func:`functools.partial`,
  this is an implementation that is compatible with Python 2.3 (if
  functools.partial exists, it is used directly).
  
  functools.partial allow to create a new function from an existing
  function by setting values to some arguments. The new function
  will be callable with less parameters. See Python 2.5 documentation
  for more information.
  
  Example::

    from soma.functiontools import partial
    
    def f( a, b, c ):
      return ( a, b, c )
    
    g = partial( f, 'a', c='c' )
    g( 'b' ) # calls f( 'a', 'b', c='c' )
  '''
  def __init__( self, function, *args, **kwargs ):
    self.func = function
    self.args = args
    self.keywords = kwargs
  
  
  def __call__( self, *args, **kwargs ):
    merged_kwargs = self.keywords.copy()
    merged_kwargs.update( kwargs )
    return self.func( *(self.args + args), **merged_kwargs )
  
  @property
  def func_code( self ):
    '''
    This property make SomaPartial useable with traits module. The method
    on_trait_change is requiring that the function has a func_code.co_argcount
    attribute.
    '''
    result = Empty()
    result.co_argcount = numberOfParameterRange( self )[ 0 ]
    return result
    
try:
  from functools import partial
except ImportError:
  partial = SomaPartial

#-------------------------------------------------------------------------------
def getArgumentsSpecification( callable ):
  '''
  This is an extension of Python module :py:mod:`inspect.getargspec` that 
  accepts classes and returns only information about the parameters that can 
  be used in a call to *callable* (*e.g.* the first *self* parameter of bound 
  methods is ignored). If *callable* has not an appropriate type, a 
  :py:class:`TypeError` exception is raised.

  - callable: *function*, *method*, *class* or *instance*

    callable to inspect

  - returns: *tuple* of four elements
  
    As :py:func:`inspect.getargspec`, returns 
    *(args, varargs, varkw, defaults)* where *args* is a list of the argument
    names (it may contain nested lists). *varargs* and *varkw* are the names 
    of the ``*`` and ``**`` arguments or *None*. *defaults* is an n-tuple of 
    the default values of the last *n* arguments.
  '''
  if inspect.isfunction( callable ):
    return inspect.getargspec( callable )
  elif inspect.ismethod( callable ):
    args, varargs, varkw, defaults = inspect.getargspec( callable )
    args = args[ 1: ] # ignore the first "self" parameter
    return args, varargs, varkw, defaults
  elif inspect.isclass( callable ):
    try:
      init = callable.__init__
    except AttributeError:
      return [], None, None, None
    return getArgumentsSpecification( init )
  elif isinstance( callable, partial ):
    args, varargs, varkw, defaults = inspect.getargspec( callable.func )
    if defaults:
      d = dict( izip( reversed( args ), reversed( defaults ) ) )
    else:
      d = {}
    d.update( izip( reversed( args ), reversed( callable.args ) ) )
    if callable.keywords:
      d.update( callable.keywords )

    if len(d) :
      defaults = tuple( (d[i] for i in args[ -len(d): ] ) )
    else :
      defaults = d
      
    return ( args, varargs, varkw, defaults )
  else:
    try:
      call = callable.__call__
    except AttributeError:
      raise TypeError( _( '%s is not callable' ) % \
                          repr( callable ) )
    return getArgumentsSpecification( call )

#-------------------------------------------------------------------------------
def getCallableString( callable ):
  '''
  Returns a translated human readable string representing a callable.
  
  - callable: *function*, *method*, *class* or *instance*
  
    callable to inspect
  
  - returns: *string*
  
    type and name of the callable
  '''
  if inspect.isfunction( callable ):
    name = _( 'function %s' ) % ( callable.__name__, )
  elif inspect.ismethod( callable ):
    name = _( 'method %s' ) % ( callable.im_class.__name__ + '.' + \
                                callable.__name__, )
  elif inspect.isclass( callable ):
    name = _( 'class %s' ) % ( callable.__name__, )
  else:
    name = str( callable )
  return name

#-------------------------------------------------------------------------------
def hasParameter( callable, parameterName ):
  '''
  Return True if *callable* can be called with a parameter named
  *parameterName*. Otherwise, returns *False*.
  
  - callable: *function*, *method*, *class* or *instance*
  
    callable to inspect
  
  - parameterName: *string*
  
    name of the parameter
  
  - returns: *bool*
  
  see: :py:func:`getArgumentsSpecification`
  '''
  args, varargs, varkw, defaults = getArgumentsSpecification( callable )
  return varkw is not None or parameterName in args

#-------------------------------------------------------------------------------
def numberOfParameterRange( callable ):
  '''
  Return the minimum and maximum number of parameter that can be used to call a
  function. If the maximum number of argument is not defined, it is set to 
  None.
  
  - callable: *function*, *method*, *class* or *instance*
  
    callable to inspect
  
  - returns: *tuple* of two elements
  
    (minimum, maximum)
  
  see: :py:func:`getArgumentsSpecification`
  '''
  args, varargs, varkw, defaults = getArgumentsSpecification( callable )
  if defaults is None or len( defaults ) > len( args ):
    lenDefault = 0
  else:
    lenDefault = len( defaults )
  minimum = len( args ) - lenDefault
  if varargs is None:
    maximum = len( args )
  else:
    maximum = None
  return minimum, maximum


#-------------------------------------------------------------------------------
def checkParameterCount( callable, paramCount ):
  '''
  Check that a callable can be called with *paramCount* arguments. If not, a
  RuntimeError is raised.
  
  - callable: *function*, *method*, *class* or *instance*
  
    callable to inspect
  
  - paramCount: *integer*
  
    number of parameters
  
  see: :py:func:`getArgumentsSpecification`
  '''
  minimum, maximum = numberOfParameterRange( callable )
  if ( maximum is not None and paramCount > maximum ) or \
     paramCount < minimum:
    raise RuntimeError( \
      _( '%(callable)s cannot be called with %(paramCount)d arguments' ) % \
      { 'callable': getCallableString( callable ), 
        'paramCount': paramCount }  )

#-------------------------------------------------------------------------------
def drange(start, stop, step = 1):
    '''
    Creates lists containing arithmetic progressions of any number type (integer, float, ...)
    '''
    r = start
    while r < stop:
        yield r
        r += step
