#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

""" This module is used to call a Process or a Pipeline from the command line 
with: "python -m soma.pipeline <process_id> [<parameter>...]" where 
<parameter> can be a value or <parameter name>=<value>. """

import sys
from capsul.process import get_process_instance

process = get_process_instance(sys.argv[1])
process.set_string_list(sys.argv[2:])
process()


