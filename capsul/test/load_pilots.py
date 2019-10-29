from __future__ import print_function
import os, sys
import logging


def load_pilots(root, path):
    """ Load all the modules in the use_cases module: path is
    recursively scanned for __init__.py files.
    Any function declared inside will be loaded.
    Test functions should be named 'test' in order to be selected.

    Parameters
    ----------
    root : str (mandatory)
        path to the use_cases module.
    path : str
        path to the module

    Returns
    -------
    pilots : dict
        a dict with module name as keys referencing to function module used
        for unitest.
    """

    pilots = {}
    files = os.listdir(path)


    for fname in files:
        if os.path.isdir(os.path.join(path, fname)):
            sub_pilots = load_pilots(root, os.path.join(path, fname))
            pilots.update(sub_pilots)

    if not any([x in files for x in ["__init__.py", ]]):
        # No __init__ file
        return pilots

    for fname in files:
        if fname.endswith(".py") and fname.startswith("test_"):

            module_name = (["capsul"] +
                path[len(os.path.normpath(root)) + 1:].split(os.path.sep) +
                [os.path.splitext(fname)[0]])
            module_name = ".".join([x for x in module_name if x])

            try:
                __import__(module_name)
            except Warning as e:
                # A test specific warning is raised.
                # For instance, it happens when non mandatory
                # modules (such as Qt or Nipype) cannot be imported 
                # for a test.
                pilots[module_name] = e
                continue
            except ImportError as e:
                # An api exists, but it cannot be imported
                pilots[module_name] = e
                continue

            module = sys.modules[module_name]

            for function in dir(module):
                if function in ["test", ]:
                    if module_name in  pilots.keys():
                        pilots[module_name].append(getattr(module, function))
                    else:
                        pilots[module_name] = [getattr(module, function), ]

    return pilots


if __name__ == "__main__":

    import soma
    module_path = soma.__path__[0]
    print(load_pilots(module_path, module_path))
