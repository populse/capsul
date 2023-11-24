from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, File, field
import sys


class PythonConfiguration(ModuleConfiguration):
    """Python configuration module"""

    version: str = field(optional=True, default="%d.%d" % sys.version_info[:2])
    executable: File = field(default=sys.executable)
    path: list[Directory] = field(default_factory=list)
    name = "python"

    def is_valid_config(self, requirements):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        return True
