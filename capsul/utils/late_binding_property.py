#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

def update_meta(self, other):
    self.__name__ = other.__name__
    self.__doc__ = other.__doc__
    self.__dict__.update(other.__dict__)
    return self

class LateBindingProperty(property):
    """ Late-binding property, allow easier usage of properties with derived
        classes.
        
        Regular properties require to redefine the property in derived classes,
        while LateBindingProperty does not :
        
        >>> class C(object):
        ... 
        ...     def getx(self):
        ...         print 'C.getx'
        ...         return self._x
        ... 
        ...     def setx(self, x):
        ...         print 'C.setx'
        ...         self._x = x
        ... 
        ...     x = LateBindingProperty(getx, setx)
        >>> class D(C):
        ... 
        ...     def setx(self, x):
        ...         print 'D.setx'
        ...         super(D, self).setx(x)
        >>> c = C()
        >>> c.x = 1
        C.setx
        >>> c.x
        C.getx
        1
        >>> d = D()
        >>> d.x = 1
        D.setx
        C.setx
        >>> d.x
        C.getx
        1
        
        Source : http://code.activestate.com/recipes/408713/#c1
    """

    def __new__(cls, fget=None, fset=None, fdel=None, doc=None):

        if fget is not None:
            def __get__(obj, objtype=None, name=fget.__name__):
                fget = getattr(obj, name)
                return fget()

            fget = update_meta(__get__, fget)

        if fset is not None:
            def __set__(obj, value, name=fset.__name__):
                fset = getattr(obj, name)
                return fset(value)

            fset = update_meta(__set__, fset)

        if fdel is not None:
            def __delete__(obj, name=fdel.__name__):
                fdel = getattr(obj, name)
                return fdel()

            fdel = update_meta(__delete__, fdel)

        return property(fget, fset, fdel, doc)
