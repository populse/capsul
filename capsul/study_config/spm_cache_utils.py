#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# system modules
import os
import shutil


def local_map(inputs, root, copy=False):
    """ `This function search for files that may be modified by a call
    to the SPM interface.`
    File concerned : .mat .nii .txt (.hdr,.img)?
    Note that when using analyse images a .mat file is created.

    Parameters
    ----------
    inputs : dict
        the inputs of the SPM interface.
    root : str
        the destination folder.
    copy : bool
        if False create symbolic link if file does
        not exists (required Traits)
        else copy the file.

    Returns
    -------
    outputs : dict
        the local inputs of the SPM interface.
    """
    # init the modified parameters to the original values
    outputs = inputs.copy()

    # check all ressources
    for key, value in inputs.items():
        if key not in ["tissue_prob_maps", ]:
            if isinstance(value, str) and os.path.isfile(value):
                outputs[key] = copy_resources(root, value, copy)
            elif isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, str) and os.path.isfile(item):
                        new_list.append(copy_resources(root, item, copy))
                outputs[key] = new_list

    return outputs


def copy_resources(root, file, copy):
    """ Function to 'copy' the files on disk
    """
    # get file name and extension
    _, filename = os.path.split(file)
    _, extension = os.path.splitext(file)
    new_file = file

    # copy if the extension is in [".mat",".nii",".txt"]
    if extension in [".mat", ".nii", ".txt"]:
        new_file = os.path.join(root, filename)
        _copy(file, new_file, copy)
    elif extension in [".img"]:
        new_file = os.path.join(root, filename)
        _copy(file, new_file, copy)
        _copy(file.replace(".img", ".hdr"), new_file.replace(".img", ".hdr"),
              copy)
    elif extension in [".hdr"]:
        new_file = os.path.join(root, filename)
        _copy(file, new_file, copy)
        _copy(file.replace(".hdr", ".img"), new_file.replace(".hdr", ".img"),
              copy)

    return new_file


def _copy(source, destination, copy):
    """ `Copy function`
    If copy is False create a symbolic link if the file does not exists.
    Else copy the file and unlink if necessary.
    """
    if copy:
        if os.path.islink(destination):
            os.unlink(destination)
        shutil.copy(source, destination)
    else:
        if not os.path.isfile(destination):
            os.symlink(source, destination)


def last_timestamp(inputs):
    """ `Find the latest created file on disk.`
    If no file is found in inputs dictionnary, -1 is returned
    """
    last_modified = -1
    for key, value in inputs.items():
        if isinstance(value, str) and os.path.isfile(value):
            mtime = os.path.getmtime(value)
            if mtime > last_modified:
                last_modified = mtime
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and os.path.isfile(item):
                    mtime = os.path.getmtime(item)
                    if mtime > last_modified:
                        last_modified = mtime
    return last_modified
