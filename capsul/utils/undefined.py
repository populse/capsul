#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
L{Undefined} is a constant that can be used as a special value different from any other Python value including C{None}.

@author: Yann Cointepas
@organization: U{NeuroSpin<http://www.neurospin.org>} and U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''
__docformat__ = "epytext en"

from capsul.utils.singleton import Singleton


#-------------------------------------------------------------------------------
class UndefinedClass( Singleton ):
  '''
  C{UndefinedClass} instance is used to represent an undefined attribute value
  when C{None} cannot be used because it can be a valid value. Should only be
  used for value checking.
  
  @see: L{Undefined}
  '''
  def __repr__( self ):
    '''
    @return: C{'<undefined>'}
    '''
    return '<undefined>'

#: C{Undefined} contains the instance of UndefinedClass and can be used to check
#: wether a value is undefined or not.
#: 
#: Example::
#:    from soma.undefined import Undefined
#:    
#:    if object.value is Undefined:
#:      # do something
Undefined = UndefinedClass()
