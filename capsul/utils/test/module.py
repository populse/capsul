#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################


def a_function_to_wrap(fname, directory, value, enum, list_of_str, reference):
    """ A dummy fucntion that just print all its parameters.

    <process>
        <return name="string" type="Str" desc="test" />
        <input name="fname" type="File" desc="test" />
        <input name="directory" type="Directory" desc="test" />
        <input name="value" type="Float" desc="test" />
        <input name="enum" type="Str" desc="test" />
        <input name="list_of_str" type="List_Str" desc="test" />
        <output name="reference" type="List_Str" desc="test" />
    </process>
    """
    string = "ALL FUNCTION PARAMETERS::\n\n"
    for input_parameter in (fname, directory, value, enum, list_of_str):
        string += str(input_parameter)
    reference.append("27")
    return string
