#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

'''
Importing this module defines a L{translate} function that translate
messages of an application. The current implementation does nothing but
defines a minimum API.

Example::
  from soma.translation import translate as _
  try:
    f = open( configurationFileName )
  except OSError:
    raise RuntimeError( _( 'Cannot open configuration file "%s"' ) % ( configurationFileName, ) )

@author: Yann Cointepas
@organization: U{NeuroSpin<http://www.neurospin.org>} and U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''
__docformat__ = "epytext en"


#------------------------------------------------------------------------------
def translate( message ):
  '''
  Translate C{message} into the current application language.
  Current implementation does nothing, C{message} is returned untouched.
  
  @param message: message to translate
  @type  message: unicode
  '''
  return message
