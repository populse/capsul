from .configuration import ModuleConfiguration
from soma.controller import Directory, undefined, field


class AntsConfiguration(ModuleConfiguration):
    """ANTs configuration module"""

    version: str
    directory: Directory = field(optional=True)
    name = "ants"

    def is_valid_config(self, requirements):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            return False
        return True

    @staticmethod
    def init_execution_context(execution_context):
        """
        Configure execution (env variables) from a configured execution context
        """
        from capsul.in_context import ants

        ants.set_env_from_config(execution_context)
