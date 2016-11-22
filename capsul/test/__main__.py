
import sys
from . import test_capsul
is_valid = test_capsul.is_valid_module()
if not is_valid:
    sys.exit(1)

