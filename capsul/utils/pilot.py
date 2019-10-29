'''
Functions
=========
:func:`pilotfunction`
---------------------
'''

# System import
import types
import sys


def pilotfunction(pilot_func):
    """ Function that can be used as a decorator for pilot functions.

    In order to test properly the module, remove the dictionary that holds
    the function's global variables, except the builtins functions.

    Parameters
    ----------
    pilot_func: @func (mandatory)
        a function that will be decorated.

    Returns
    -------
    decorated_func: @func
        the same input function, with the function's global variables removed.
    """
    if sys.version_info[0] >= 3:
        func_code = pilot_func.__code__
    else:
        func_code = pilot_func.func_code
    func = types.FunctionType(func_code, {"__builtins__": __builtins__})
    func.__module__ = pilot_func.__module__
    return func
