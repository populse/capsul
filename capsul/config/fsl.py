from soma.controller import Directory, File, field, undefined

from .configuration import ModuleConfiguration


class FSLConfiguration(ModuleConfiguration):
    """FSL configuration module"""

    directory: Directory = field(optional=True)
    version: str
    setup_script: File = field(optional=True)
    prefix: str = field(optional=True)
    name = "fsl"

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
        from capsul.in_context import fsl

        fsl.set_env_from_config(execution_context)
