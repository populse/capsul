##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# CAPSUL import
from capsul.utils.function_to_process import register_processes
from capsul.utils.test.module import a_function_to_wrap

# Register new processes
register_processes([a_function_to_wrap]) # globals())

