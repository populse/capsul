from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined


class SPMConfiguration(ModuleConfiguration):
    """SPM configuration module"""

    directory: Directory
    version: str
    standalone: bool = False
    name = "spm"

    module_dependencies = ["matlab"]

    def is_valid_config(self, requirements):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        if self.standalone:
            return {"matlab": {"mcr": True}}
        else:
            return {"matlab": {"mcr": False}}

    @staticmethod
    def init_execution_context(execution_context):
        """
        Configure execution (env variables) from a configured execution context
        """
        from capsul.in_context import spm

        spm.set_env_from_config(execution_context)
