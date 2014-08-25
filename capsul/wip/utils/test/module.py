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

    <capsul>
        <item name="fname" type="File" desc="test" />
        <item name="directory" type="Directory" desc="test" />
        <item name="value" type="Float" desc="test" />
        <item name="enum" type="Enum" initializer="('choice1','choice2')" desc="test" />
        <item name="list_of_str" type="List" content="Str" desc="test" />
        <item name="reference" type="List" content="Str" role="output" desc="test" />
        <item name="string" type="Str" role="return" desc="test" />
    </capsul>
    """
    string = "ALL FUNCTION PARAMETERS::\n\n"
    for input_parameter in (fname, directory, value, enum, list_of_str):
        string += str(input_parameter)
    reference.append("27")
    return string
