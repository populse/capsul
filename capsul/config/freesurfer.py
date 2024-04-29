from soma.controller import Directory, File, field, undefined

from .configuration import ModuleConfiguration


class FreesurferConfiguration(ModuleConfiguration):
    """Freesurfer configuration module"""

    version: str
    setup_script: File = field(optional=True)
    subjects_dir: Directory = field(optional=True)
    name = "freesurfer"

    def is_valid_config(self, requirements, explain=False):
        required_version = requirements.get("version")
        if required_version and getattr(self, "version", undefined) != required_version:
            if explain:
                return f"{self.name} configuration does not match required version {required_version} not found."
            return False
        return True

    @staticmethod
    def init_execution_context(execution_context):
        """
        Configure execution (env variables) from a configured execution context
        """
        from capsul.in_context import freesurfer

        freesurfer.set_env_from_config(execution_context)
